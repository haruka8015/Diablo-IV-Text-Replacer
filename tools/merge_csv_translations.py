#!/usr/bin/env python3
"""
Diablo IV の英語・日本語 CSV から Web 用 translations.json を更新する。

CSV の行は SNO / FileName / Index / KeyHash / Key の複合キーで対応付ける。
既存翻訳は既定で優先し、文字化け・曖昧な重複・Web で使えない文字列は
自動的に除外する。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


CSV_ID_COLUMNS = ("SNO", "FileName", "Index", "KeyHash", "Key")
CSV_FALLBACK_ID_COLUMNS = ("SNO", "FileName", "KeyHash", "Key")
CSV_REQUIRED_COLUMNS = (*CSV_ID_COLUMNS, "Translation")
NAME_FIELDS = {"Name", "name", "AffixName"}
AFFIX_FIELDS = {"Name", "name", "Name_Prefix", "Name_Suffix", "AffixName"}
PARAGON_FIELDS = {"Name", "name"}
POWER_NAME_RE = re.compile(r"^(?:Buff|Mod)\d+_Name$")
COLOR_TAG_RE = re.compile(
    r"\{/?c(?:_\w+|:[0-9A-Fa-f]{6,8})?\}",
    flags=re.IGNORECASE,
)
TEMPLATE_TOKEN_RE = re.compile(
    r"\[[^\[\]]*\{(?:VALUE[^}]*)\}[^\[\]]*\]"
    r"|\{(?:VALUE[^}]*|s\d+)\}",
    flags=re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\{(?:VALUE[^}]*|s\d+)\}", flags=re.IGNORECASE)
REGEX_META_RE = re.compile(r"([\\^$.*+?()[\]{}|/])")
REGEX_SPECIAL_RE = re.compile(r"[\\()|[\]{}+*?^$.]")
NUMBER_CAPTURE = r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|\.\d+%?)"


@dataclass(frozen=True)
class CsvRow:
    identity: tuple[str, ...]
    file_name: str
    key: str
    translation: str
    line_number: int


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    matches: Callable[[CsvRow], bool]


def _is_legacy_item_file(file_name: str) -> bool:
    if file_name.startswith("ItemType_"):
        return True
    if file_name.startswith(
        ("Item_Talisman_Charm_Set_", "Item_Talisman_Seal_")
    ):
        return True
    if not file_name.startswith("Item_"):
        return False
    return (
        "_Unique" in file_name
        or "_Legendary" in file_name
        or file_name.startswith("Item_Rune_")
    )


def _is_legendary_affix_file(file_name: str) -> bool:
    return file_name.startswith(
        (
            "Affix_legendary_",
            "Affix_x1_legendary_",
            "Affix_S05_BSK_",
        )
    )


def _is_paragon_name_row(row: CsvRow) -> bool:
    if row.file_name.startswith(
        ("ParagonBoard_", "ParagonNode_", "ParagonGlyph_")
    ):
        return row.key in PARAGON_FIELDS
    if row.file_name == "ParagonBoardUI":
        return row.key in {
            "NodeTypeMagic",
            "NodeTypeRare",
            "NodeTypeLegendary",
            "GlyphRarity_Magic",
            "GlyphRarity_Rare",
            "GlyphRarity_Legendary",
        }
    if row.file_name == "ItemLabels":
        return row.key == "Glyph" and clean_color_tags(row.translation) == "Glyph"
    return (
        row.file_name == "UITestStrings"
        and row.key == "Common"
        and clean_color_tags(row.translation) == "Common Node"
    )


RULES: OrderedDict[str, Rule] = OrderedDict(
    (
        (
            "attributes",
            Rule(
                "attributes",
                "AttributeDescriptions の装備・能力値表記",
                lambda row: row.file_name == "AttributeDescriptions",
            ),
        ),
        (
            "items",
            Rule(
                "items",
                "アイテム種別、ユニーク、レジェンダリー、ルーンの名前",
                lambda row: _is_legacy_item_file(row.file_name)
                and row.key in NAME_FIELDS,
            ),
        ),
        (
            "affixes",
            Rule(
                "affixes",
                "Affix の名前、プレフィックス、サフィックス",
                lambda row: row.file_name.startswith("Affix_")
                and row.key in AFFIX_FIELDS,
            ),
        ),
        (
            "rare-names",
            Rule(
                "rare-names",
                "RareNameStrings のランダムアイテム名断片",
                lambda row: (
                    row.file_name == "RareNameStrings"
                    or row.file_name.startswith("RareNameStrings_")
                )
                and clean_color_tags(row.translation) != "Glyph",
            ),
        ),
        (
            "powers",
            Rule(
                "powers",
                "Power と CollectiblePower の名前・強化名",
                lambda row: row.file_name.startswith(("Power_", "CollectiblePower_"))
                and (row.key in NAME_FIELDS or bool(POWER_NAME_RE.match(row.key))),
            ),
        ),
        (
            "paragon",
            Rule(
                "paragon",
                "パラゴンボード、ノード種別、ノード、グリフの名前",
                _is_paragon_name_row,
            ),
        ),
        (
            "skills",
            Rule(
                "skills",
                "スキル名とスキルタグ名",
                lambda row: (
                    row.file_name.startswith("Skill_")
                    or row.file_name in {"SkillTags", "SkillTagNames"}
                ),
            ),
        ),
        (
            "recipes",
            Rule(
                "recipes",
                "レシピ名",
                lambda row: row.file_name.startswith("Recipe_")
                and row.key in NAME_FIELDS,
            ),
        ),
    )
)
DEFAULT_CATEGORIES = tuple(name for name in RULES if name != "recipes")


def load_csv(path: Path) -> tuple[dict[tuple[str, ...], CsvRow], int]:
    rows: dict[tuple[str, ...], CsvRow] = {}
    duplicate_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in CSV_REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: 必須列がありません: {', '.join(missing)}")

        for line_number, raw in enumerate(reader, start=2):
            identity = tuple(raw[column] for column in CSV_ID_COLUMNS)
            row = CsvRow(
                identity=identity,
                file_name=raw["FileName"],
                key=raw["Key"],
                translation=raw["Translation"],
                line_number=line_number,
            )
            if identity in rows:
                duplicate_count += 1
                if rows[identity].translation != row.translation:
                    raise ValueError(
                        f"{path}:{line_number}: 同じ複合キーに異なる Translation があります"
                    )
                continue
            rows[identity] = row
    return rows, duplicate_count


def fallback_identity(row: CsvRow) -> tuple[str, ...]:
    values = dict(zip(CSV_ID_COLUMNS, row.identity))
    return tuple(values[column] for column in CSV_FALLBACK_ID_COLUMNS)


def unique_fallback_rows(
    rows: Iterable[CsvRow],
) -> dict[tuple[str, ...], CsvRow | None]:
    fallback_rows: dict[tuple[str, ...], CsvRow | None] = {}
    for row in rows:
        identity = fallback_identity(row)
        if identity in fallback_rows:
            fallback_rows[identity] = None
        else:
            fallback_rows[identity] = row
    return fallback_rows


def clean_color_tags(value: str) -> str:
    return COLOR_TAG_RE.sub("", value).strip()


def _escape_regex_literal(value: str) -> str:
    return REGEX_META_RE.sub(r"\\\1", value)


def _token_id(token: str) -> str | None:
    match = PLACEHOLDER_RE.search(token)
    return match.group(0).upper() if match else None


def create_template_pair(english: str, japanese: str) -> tuple[str, str] | None:
    """Blizzard の VALUE/s プレースホルダーを JavaScript 正規表現へ変換する。"""
    english_tokens = list(TEMPLATE_TOKEN_RE.finditer(english))
    if not english_tokens:
        return None

    capture_by_token: dict[str, int] = {}
    pattern_parts: list[str] = []
    position = 0
    capture_number = 0

    for match in english_tokens:
        pattern_parts.append(_escape_regex_literal(english[position : match.start()]))
        token = match.group(0)
        token_id = _token_id(token)
        if token_id is None:
            return None
        capture_number += 1
        capture_by_token.setdefault(token_id, capture_number)
        if token.startswith("[") or token_id.endswith("%}"):
            pattern_parts.append(NUMBER_CAPTURE)
        else:
            pattern_parts.append(r"(.*?)")
        position = match.end()

    pattern_parts.append(_escape_regex_literal(english[position:]))
    pattern = "".join(pattern_parts)

    replacement_parts: list[str] = []
    position = 0
    for match in TEMPLATE_TOKEN_RE.finditer(japanese):
        replacement_parts.append(japanese[position : match.start()])
        token_id = _token_id(match.group(0))
        capture = capture_by_token.get(token_id or "")
        if capture is None:
            return None
        replacement_parts.append(f"${capture}")
        position = match.end()
    replacement_parts.append(japanese[position:])
    replacement = "".join(replacement_parts)

    english_without_tokens = TEMPLATE_TOKEN_RE.sub("", english)
    if (
        "{" in english_without_tokens
        or "}" in english_without_tokens
        or "{" in replacement
        or "}" in replacement
    ):
        return None
    return pattern, replacement


def make_translation_pair(english: str, japanese: str) -> tuple[str, str, str | None]:
    """戻り値は (英語キー, 日本語値, 除外理由)。"""
    english = clean_color_tags(english)
    japanese = clean_color_tags(japanese)

    if not english or not japanese:
        return "", "", "empty"
    if "\ufffd" in english or "\ufffd" in japanese:
        return "", "", "corrupt"
    if "\n" in english or "\r" in english or "\n" in japanese or "\r" in japanese:
        return "", "", "multiline"
    if english == japanese:
        return "", "", "same-language"

    template_pair = create_template_pair(english, japanese)
    if template_pair:
        english, japanese = template_pair
    elif "{" in english or "}" in english or "{" in japanese or "}" in japanese:
        return "", "", "unsupported-tag"

    if len(english) >= 200:
        return "", "", "too-long"
    if len(REGEX_SPECIAL_RE.findall(english)) > 14:
        return "", "", "complex-regex"
    try:
        re.compile(english)
    except re.error:
        return "", "", "invalid-regex"
    return english, japanese, None


def make_affix_alias_pairs(key: str, value: str) -> list[tuple[str, str]]:
    """`of X` 形式からMaxroll向け短縮名と `Aspect of X` を生成する。"""
    if not key.startswith("of ") or len(key) <= 3:
        return []

    short_value = value[:-1] if value.endswith("の") else value
    return [
        (key[3:], short_value),
        (f"Aspect {key}", f"{value}化身"),
    ]


def selected_category(row: CsvRow, categories: Iterable[str]) -> str | None:
    for category in categories:
        if RULES[category].matches(row):
            return category
    return None


def load_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        raise ValueError(f"{path}: 文字列から文字列への JSON オブジェクトではありません")
    return data


def sorted_translations(data: dict[str, str]) -> OrderedDict[str, str]:
    return OrderedDict(sorted(data.items(), key=lambda item: (-len(item[0]), item[0])))


def save_json_atomic(data: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(sorted_translations(data), handle, ensure_ascii=False, indent=4)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def merge_csv_files(
    en_path: Path,
    ja_path: Path,
    existing: dict[str, str],
    categories: Iterable[str] = DEFAULT_CATEGORIES,
    overwrite_existing: bool = False,
) -> tuple[dict[str, str], dict[str, object]]:
    categories = tuple(categories)
    en_rows, en_duplicates = load_csv(en_path)
    ja_rows, ja_duplicates = load_csv(ja_path)
    ja_fallback_rows = unique_fallback_rows(ja_rows.values())

    stats: Counter[str] = Counter()
    category_selected: Counter[str] = Counter()
    category_added: Counter[str] = Counter()
    candidates: dict[str, tuple[str, str]] = {}
    conflicts: set[str] = set()

    for identity, en_row in en_rows.items():
        category = selected_category(en_row, categories)
        if category is None:
            continue
        stats["selected"] += 1
        category_selected[category] += 1

        ja_row = ja_rows.get(identity)
        if ja_row is None:
            ja_row = (
                ja_fallback_rows.get(fallback_identity(en_row))
                if category == "paragon"
                else None
            )
            if ja_row is None:
                stats["missing-ja"] += 1
                continue
            stats["matched-ja-fallback"] += 1

        key, value, rejection = make_translation_pair(
            en_row.translation, ja_row.translation
        )
        if rejection:
            stats[f"rejected:{rejection}"] += 1
            continue

        pairs = [(key, value)]
        if category == "affixes" and _is_legendary_affix_file(en_row.file_name):
            pairs.extend(make_affix_alias_pairs(key, value))

        for candidate_key, candidate_value in pairs:
            if candidate_key in conflicts:
                stats["conflict-row"] += 1
                continue
            previous = candidates.get(candidate_key)
            if previous and previous[0] != candidate_value:
                del candidates[candidate_key]
                conflicts.add(candidate_key)
                stats["conflict-key"] += 1
                continue
            if previous:
                stats["duplicate-pair"] += 1
                continue
            candidates[candidate_key] = (candidate_value, category)

    merged = dict(existing)
    for key, (value, category) in candidates.items():
        if key in conflicts:
            continue
        if key in existing and not overwrite_existing:
            stats["kept-existing"] += 1
            continue
        if key in existing and existing[key] == value:
            stats["unchanged"] += 1
            continue
        if key in existing:
            stats["overwritten"] += 1
        else:
            stats["added"] += 1
        merged[key] = value
        category_added[category] += 1

    stats["unmatched-en"] = len(set(en_rows) - set(ja_rows))
    stats["unmatched-ja"] = len(set(ja_rows) - set(en_rows))
    report: dict[str, object] = {
        "english_rows": len(en_rows),
        "japanese_rows": len(ja_rows),
        "english_duplicate_rows": en_duplicates,
        "japanese_duplicate_rows": ja_duplicates,
        "existing": len(existing),
        "result": len(merged),
        "categories": list(categories),
        "selected_by_category": dict(category_selected),
        "added_by_category": dict(category_added),
        "counts": dict(stats),
        "conflict_keys": sorted(conflicts),
    }
    return merged, report


def parse_categories(raw: str) -> tuple[str, ...]:
    if raw.strip().lower() == "all":
        return tuple(RULES)
    categories = tuple(part.strip() for part in raw.split(",") if part.strip())
    unknown = [category for category in categories if category not in RULES]
    if unknown:
        raise argparse.ArgumentTypeError(
            "不明なカテゴリ: "
            + ", ".join(unknown)
            + "（選択肢: "
            + ", ".join(RULES)
            + "）"
        )
    if not categories:
        raise argparse.ArgumentTypeError("カテゴリを1つ以上指定してください")
    return categories


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diablo IV の英日 CSV を対応付けて translations.json にマージします。"
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("sources/translations.json"),
        help="出力 JSON（既定: sources/translations.json）",
    )
    parser.add_argument("--en", type=Path, help="英語 CSV")
    parser.add_argument(
        "--ja", "--jp", dest="ja", type=Path, help="日本語 CSV"
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="マージ元 JSON（省略時は既存の output、存在しなければ空）",
    )
    parser.add_argument(
        "--categories",
        type=parse_categories,
        default=DEFAULT_CATEGORIES,
        metavar="LIST",
        help="カンマ区切り。既定: " + ",".join(DEFAULT_CATEGORIES),
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="既存キーも CSV の訳で上書きする（既定では既存訳を優先）",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="JSON を書き込まず集計だけ表示する"
    )
    parser.add_argument("--report", type=Path, help="詳細な集計を JSON で保存する")
    parser.add_argument(
        "--list-categories", action="store_true", help="カテゴリ一覧を表示して終了する"
    )
    return parser


def print_report(report: dict[str, object], output: Path, dry_run: bool) -> None:
    counts = report["counts"]
    assert isinstance(counts, dict)
    print(f"English rows : {report['english_rows']}")
    print(f"Japanese rows: {report['japanese_rows']}")
    print(f"Selected     : {counts.get('selected', 0)}")
    print(f"Added        : {counts.get('added', 0)}")
    print(f"Kept existing: {counts.get('kept-existing', 0)}")
    print(f"Conflicts    : {counts.get('conflict-key', 0)}")
    print(f"Corrupt skip : {counts.get('rejected:corrupt', 0)}")
    print(f"Result       : {report['result']}")
    print("Added by category:")
    added = report["added_by_category"]
    assert isinstance(added, dict)
    for category in report["categories"]:
        print(f"  {category:12}: {added.get(category, 0)}")
    print("Dry run: no file was written." if dry_run else f"Saved: {output}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_categories:
        for name, rule in RULES.items():
            print(f"{name:12} {rule.description}")
        return 0
    if args.en is None or args.ja is None:
        parser.error("--en と --ja の両方を指定してください")

    try:
        base_path = args.base or args.output
        existing = load_json(base_path)
        merged, report = merge_csv_files(
            args.en,
            args.ja,
            existing,
            categories=args.categories,
            overwrite_existing=args.overwrite_existing,
        )
        if not args.dry_run:
            save_json_atomic(merged, args.output)
        if args.report:
            save_json_atomic(report, args.report)
        print_report(report, args.output, args.dry_run)
        return 0
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
