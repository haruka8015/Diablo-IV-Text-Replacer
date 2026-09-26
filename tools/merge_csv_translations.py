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
PLAYER_SKILL_POWER_PREFIXES = tuple(
    f"Power_{class_name}_"
    for class_name in (
        "Barbarian",
        "Druid",
        "Necromancer",
        "Paladin",
        "Rogue",
        "Sorcerer",
        "Spiritborn",
        "Warlock",
        "pal",
        "sorc",
        "spiritborn",
    )
)
TOOLTIP_TEXT_CATEGORIES = {
    "prism-descriptions",
    "drop-sources",
    "effects",
    "flavors",
    "runes",
    "skill-tags",
    "skills",
    "weapon-tooltip",
}
DROP_SOURCE_KEY_PREFIX = "__D4T_DROP_SOURCE__:"
COLOR_TAG_RE = re.compile(
    r"\{/?c(?:_\w+|:[0-9A-Fa-f]{6,8})?\}",
    flags=re.IGNORECASE,
)
ICON_TAG_RE = re.compile(r"\{icon:[^{}\r\n]+\}", flags=re.IGNORECASE)
TEMPLATE_TOKEN_RE = re.compile(
    r"\[[^\[\]]*\{(?:VALUE[^}]*)\}[^\[\]]*\]"
    r"|\{(?:VALUE[^}]*|s\d+)\}",
    flags=re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\{(?:VALUE[^}]*|s\d+)\}", flags=re.IGNORECASE)
D4_VALUE_TOKEN_RE = re.compile(
    r"\[[^\[\]\r\n]+\]"
    r"|\{(?:"
    r"SF_[^{}\r\n]+"
    r"|payload:[^{}\r\n]+"
    r"|dot:[^{}\r\n]+"
    r"|buffduration:[^{}\r\n]+"
    r"|Resource\s+Cost"
    r"|Combat\s+Effect\s+Chance"
    r"|Cooldown\s+Time"
    r"|Recharge\s+Time"
    r")\}",
    flags=re.IGNORECASE,
)
D4_FORMAT_TAG_RE = re.compile(
    r"\{(?!SF_)[^{}\r\n]*\}",
    flags=re.IGNORECASE,
)
D4_PLURAL_TOKEN_RE = re.compile(r"\|4([^:;\r\n]+)(?::([^;\r\n]+))?;")
D4_CONDITIONAL_RE = re.compile(
    r"\{if:[^{}\r\n]+\}"
    r"(?:(?P<true_else>[\s\S]*?)\{else\}(?P<false>[\s\S]*?)"
    r"|(?P<true_only>[\s\S]*?))"
    r"\{/if\}",
    flags=re.IGNORECASE,
)
FLAVOR_ATTRIBUTION_RE = re.compile(
    r"^(?P<body>.+[.!?])(?P<spacing>\s+)(?P<attribution>-\s*.+)$",
    flags=re.DOTALL,
)
REGEX_META_RE = re.compile(r"([\\^$.*+?()[\]{}|/])")
REGEX_SPECIAL_RE = re.compile(r"[\\()|[\]{}+*?^$.]")
NUMBER_CAPTURE = r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|\.\d+%?)"
PERCENT_CAPTURE = (
    r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%|\.\d+%)"
)
PARAGON_REQUIREMENT_VALUE_CAPTURE = (
    r"(\[?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?"
    r"\]?(?:%|x|\+)?)"
)
# ゲーム辞書の「|%x|」はMaxrollで「%[x]」と描画される場合がある。
# 乗算種別マーカーまで数値アンカーに含め、全文置換後も装飾位置を維持する。
D4_VALUE_CAPTURE = (
    r"(\[?[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?"
    r"(?:\s*[-–]\s*[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?)?"
    r"\]?(?:%\[x\]|%x|x%|%|x|\+)?"
    r"(?:\s+(?:x\s+)?\[[^\]\r\n]+\])?)"
)


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


def _is_soul_splinter_file(file_name: str) -> bool:
    return bool(re.match(r"^Item_S\d+_SoulSplinter_", file_name))


def _is_legacy_item_file(file_name: str) -> bool:
    if _is_soul_splinter_file(file_name):
        return True
    if file_name.startswith("ItemType_"):
        return True
    if file_name.startswith(
        ("Item_Talisman_Charm_Set_", "Item_Talisman_Charm_Uniq_",
         "Item_Talisman_Seal_", "Item_Runeword_")
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


PARAGON_TOOLTIP_UI_FIELDS = {
    "GlyphRadius_Prompt",
    "NodeTypeMagic",
    "NodeTypeRare",
    "NodeTypeLegendary",
    "GlyphLevel",
    "AffectedNodes",
    "GlyphSocket",
    "GlyphRarity_Magic",
    "GlyphRarity_Rare",
    "GlyphRarity_Legendary",
    "GlyphSizeName",
    "GlyphRewardName",
    "GlyphSocketed",
    "ThresholdBonusAttribute",
    "ThresholdBonusAttributeGlyphModified",
    "RequirementsNotMet",
    "RequirementListThresholdMetWithPlus",
    "RequirementListThresholdNotMetWithPlus",
    "ThresholdGlyphBonus",
    "ThresholdRequirementsHeader",
    "ThresholdRequirementsInRangeHeader",
    "RequirementListThresholdMet",
    "RequirementListThresholdNotMet",
    "GlyphRadiusUpgrade",
    "GlyphRadiusMax",
    "RarityRequirement",
    "LegendaryGlyphBonus",
    "RequirementListThresholdNotMetInRange",
    "RequirementListThresholdMetInRange",
}


def _is_paragon_row(row: CsvRow) -> bool:
    if row.file_name == "SkillsUI" and row.key == "Paragon":
        return True
    if row.file_name.startswith(
        ("Power_Paragon_", "Power_ParagonGlyph_")
    ):
        return (
            row.key.lower() in {"name", "desc"}
            or row.key.endswith(("_Name", "_Description"))
        )
    if row.file_name.startswith("ParagonGlyphAffix_"):
        return row.key in {"Name", "name", "Desc", "desc"}
    if row.file_name.startswith(
        ("ParagonBoard_", "ParagonNode_", "ParagonGlyph_")
    ):
        return row.key in PARAGON_FIELDS
    if row.file_name == "ParagonBoardUI":
        return row.key in PARAGON_TOOLTIP_UI_FIELDS
    if row.file_name == "ItemLabels":
        return row.key == "Glyph" and clean_color_tags(row.translation) == "Glyph"
    return (
        row.file_name == "UITestStrings"
        and row.key == "Common"
        and clean_color_tags(row.translation) == "Common Node"
    )


def _is_paragon_description_row(row: CsvRow) -> bool:
    return (
        row.file_name.startswith(
            (
                "Power_Paragon_",
                "Power_ParagonGlyph_",
                "ParagonGlyphAffix_",
            )
        )
        and (
            row.key.lower() == "desc"
            or row.key.endswith("_Description")
        )
    )


RULES: OrderedDict[str, Rule] = OrderedDict(
    (
        (
            "attributes",
            Rule(
                "attributes",
                "AttributeDescriptions の装備・能力値表記",
                lambda row: (
                    row.file_name == "AttributeDescriptions"
                    or (_is_soul_splinter_file(row.file_name)
                        and row.key in {"Description", "RequirementText"})
                    or (row.file_name == "UIToolTips" and row.key == "Socketable")
                ),
            ),
        ),
        (
            "drop-sources",
            Rule(
                "drop-sources",
                "MaxrollのTooltipに表示されるドロップ元ボス名",
                lambda row: row.file_name == "ModifiedLootDescriptions",
            ),
        ),
        (
            "weapon-tooltip",
            Rule(
                "weapon-tooltip",
                "武器Tooltipの秒間ダメージ、命中ダメージ、秒間攻撃回数",
                lambda row: (
                    row.file_name == "H2OLayout"
                    and row.key
                    in {
                        "TooltipRatingLabelDPS",
                        "TooltipRatingLabelAttackSpeed",
                        "TooltipRatingLabelDamagePerHit",
                        "TooltipRatingLabelDamagePerHitHeader",
                    }
                )
                or (
                    row.file_name == "UIToolTips"
                    and row.key.startswith("WeaponSpeed_")
                ),
            ),
        ),
        (
            "tooltip-labels",
            Rule(
                "tooltip-labels",
                "装備Tooltipのアイテムパワー、品質、アイテム品質ラベル",
                lambda row: (
                    (row.file_name, row.key)
                    in {
                        ("Hero", "ItemPower"),
                        ("GameOptions", "HeaderQuality"),
                        ("UIToolTips", "SealSlotToolTip"),
                    }
                    or row.file_name == "ItemQuality"
                ),
            ),
        ),
        (
            "runes",
            Rule(
                "runes",
                "ルーン名、ルーンワード名、条件・効果・オーバーフロー説明",
                lambda row: (
                    bool(re.match(r"^Item_(?:S\d+_)?Rune_", row.file_name))
                    or (
                        row.file_name == "UIToolTips"
                        and row.key in {"RunewordCompleteWithFrequency", "RuneUnsocketedCondition",
                                        "RuneUnsocketedEffect", "SocketableConditionRune",
                                        "SocketableEffectRune", "RuneInternalCooldown"}
                    )
                ),
            ),
        ),
        (
            "items",
            Rule(
                "items",
                "アイテム種別、ユニーク、レジェンダリー、宝石、ルーンの名前",
                lambda row: (_is_legacy_item_file(row.file_name)
                             or row.file_name.startswith("Item_Gem_")
                             or row.file_name.startswith(("Item_X2_HoradricCube_CraftingMaterial_",
                                                          "Item_X2_Talisman_CraftingMaterial_"))
                             or row.file_name.startswith("Item_X2_HoradricCube_TuningStone_")
                             or row.file_name.startswith("SetItemBonus_Talisman_"))
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
            "effects",
            Rule(
                "effects",
                "レジェンダリー、ユニーク、ミシック効果の説明文",
                lambda row: row.key == "Desc"
                and row.file_name.startswith("Affix_")
                and (
                    "_unique_" in row.file_name.lower()
                    or "legendary" in row.file_name.lower()
                    or "mythic" in row.file_name.lower()
                    or row.file_name.startswith((
                        "Affix_Runeword_", "Affix_Talisman_SetPower_",
                        "Affix_Talisman_Charm_", "Affix_HellfireTorch_",
                        "Affix_Talisman_SealAffix_",
                    ))
                ),
            ),
        ),
        (
            "prism-descriptions",
            Rule(
                "prism-descriptions",
                "同調プリズムの用途・使用条件・入手元",
                lambda row: row.file_name.startswith("Item_X2_HoradricCube_TuningStone_")
                and row.key == "Description",
            ),
        ),
        (
            "flavors",
            Rule(
                "flavors",
                "攻略用アイテムのフレーバーテキスト（セット・ルーンワードを含む）",
                lambda row: row.key == "Flavor"
                and row.file_name.startswith("Item_")
                and (
                    _is_legacy_item_file(row.file_name)
                    or row.file_name.startswith("Item_X2_HoradricCube_TuningStone_")
                    or "_Mythic" in row.file_name
                ),
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
                "パラゴンの名前、ノード・グリフ効果文、Tooltip共通文",
                _is_paragon_row,
            ),
        ),
        (
            "skill-tags",
            Rule(
                "skill-tags",
                "SkillTags のタグ名と注釈本文",
                lambda row: row.file_name == "SkillTags",
            ),
        ),
        (
            "skills",
            Rule(
                "skills",
                "スキル名、スキルタグ名、Power の説明文",
                lambda row: (
                    row.file_name.startswith(("Skill_", "SkillTree_"))
                    or row.file_name == "SkillTagNames"
                    or (
                        (row.file_name.startswith(PLAYER_SKILL_POWER_PREFIXES)
                         or bool(re.match(r"^Power_S\d+_Triad[A-C]_Player_", row.file_name)))
                        and (
                            row.key.lower() in {"desc", "rankup_desc"}
                            or row.key.endswith("_Description")
                        )
                    )
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
    previous_identity: tuple[str, ...] | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in CSV_REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: 必須列がありません: {', '.join(missing)}")

        for line_number, raw in enumerate(reader, start=2):
            if not any(raw.get(column) for column in CSV_REQUIRED_COLUMNS):
                continue

            # Blizzard CSVでは複数段落のDescが、次行の第1列だけへ格納される。
            # 直前の正規行へ連結しないと、Loyalty's Mantle等の箇条書きが失われる。
            if (
                previous_identity is not None
                and raw["SNO"]
                and all(not raw[column] for column in CSV_ID_COLUMNS[1:])
                and not raw["Translation"]
            ):
                previous = rows[previous_identity]
                rows[previous_identity] = CsvRow(
                    identity=previous.identity,
                    file_name=previous.file_name,
                    key=previous.key,
                    translation=f"{previous.translation}\n{raw['SNO']}",
                    line_number=previous.line_number,
                )
                continue

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
            previous_identity = identity
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


def _escape_regex_text(value: str) -> str:
    """DOM 側の改行・空白差を許容するリテラル正規表現を作る。"""
    return "".join(
        r"\s+" if part.isspace() else _escape_regex_literal(part)
        for part in re.split(r"(\s+)", value)
        if part
    )


def _escape_d4_rendered_text(value: str) -> str:
    """ゲームの単複数トークンをMaxrollの描画結果に合う正規表現へ変換する。"""
    parts: list[str] = []
    position = 0
    for match in D4_PLURAL_TOKEN_RE.finditer(value):
        parts.append(_escape_regex_text(value[position : match.start()]))
        variants = [match.group(1)]
        if match.group(2):
            variants.append(match.group(2))
        escaped_variants = [
            _escape_regex_text(variant)
            for variant in dict.fromkeys(variants)
        ]
        parts.append(f"(?:{'|'.join(escaped_variants)})")
        position = match.end()
    parts.append(_escape_regex_text(value[position:]))
    return "".join(parts)


def _render_japanese_plural_tokens(value: str) -> str:
    return D4_PLURAL_TOKEN_RE.sub(
        lambda match: match.group(2) or match.group(1),
        value,
    )


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
        literal_before = english[position : match.start()]
        literal_pattern = _escape_regex_text(literal_before)
        # Maxrollはplaceholderをspanにし、直後の空白をDOMから落とすことがある。
        # "Damageif requirements" のような連結表示も同じテンプレートで拾う。
        if pattern_parts and literal_before[:1].isspace():
            literal_pattern = re.sub(r"^\\s\+", r"\\s*", literal_pattern)
        pattern_parts.append(literal_pattern)
        token = match.group(0)
        token_id = _token_id(token)
        if token_id is None:
            return None
        capture_number += 1
        capture_by_token.setdefault(token_id, capture_number)
        if (
            token.startswith("[")
            or token_id.endswith("%}")
            or literal_before.rstrip().endswith(("+", "-"))
        ):
            pattern_parts.append(NUMBER_CAPTURE)
        else:
            text_capture = r"(.*?)"
            if match.end() == len(english):
                text_capture += r"(?=\s*(?:\(|\[|$))"
            pattern_parts.append(text_capture)
        position = match.end()

    trailing_literal = english[position:]
    trailing_pattern = _escape_regex_text(trailing_literal)
    if english_tokens and trailing_literal[:1].isspace():
        trailing_pattern = re.sub(r"^\\s\+", r"\\s*", trailing_pattern)
    pattern_parts.append(trailing_pattern)
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


def _d4_value_token_id(token: str) -> str:
    normalized = re.sub(r"\s+", "", token.replace('""', '"')).lower()
    # 表示上の加算/乗算マーカーは言語CSV間で省略されることがある。
    # 値の参照元が同じなら、置換位置を対応付けられるよう同一視する。
    return re.sub(r"\|(%)(?:\+|x)?\|", r"|\1|", normalized)


def strip_d4_format_tags_preserving_values(value: str) -> str:
    """色・制御タグだけを除き、Maxrollで実数化されるトークンは残す。"""
    return D4_FORMAT_TAG_RE.sub(
        lambda match: (
            match.group(0)
            if D4_VALUE_TOKEN_RE.fullmatch(match.group(0))
            else ""
        ),
        value,
    ).strip()


def create_d4_description_pair(
    english: str, japanese: str
) -> tuple[str, str] | None:
    """Maxroll が描画する装備効果文向けの全文正規表現を生成する。

    Blizzard の色・条件タグは DOM には現れないため除去し、角括弧内の
    Affix 式は Maxroll 上の実数値（範囲表記を含む）を受けるキャプチャにする。
    """
    english = strip_d4_format_tags_preserving_values(english)
    japanese = strip_d4_format_tags_preserving_values(japanese)
    japanese = _render_japanese_plural_tokens(japanese)
    text_without_value_tokens = D4_VALUE_TOKEN_RE.sub(
        "",
        english + japanese,
    )
    if (
        not english
        or not japanese
        or "{" in text_without_value_tokens
        or "}" in text_without_value_tokens
    ):
        return None

    english_tokens = list(D4_VALUE_TOKEN_RE.finditer(english))
    english_literal = D4_VALUE_TOKEN_RE.sub("", english)
    if english_tokens and not re.search(r"[A-Za-z]{2,}", english_literal):
        return None
    if not english_tokens:
        if english == japanese:
            return None
        pattern = _escape_d4_rendered_text(english)
        try:
            re.compile(pattern)
        except re.error:
            return None
        return pattern, japanese

    capture_by_token: dict[str, int] = {}
    pattern_parts: list[str] = []
    position = 0
    for capture_number, match in enumerate(english_tokens, start=1):
        pattern_parts.append(
            _escape_d4_rendered_text(english[position : match.start()])
        )
        capture_by_token.setdefault(_d4_value_token_id(match.group(0)), capture_number)
        pattern_parts.append(D4_VALUE_CAPTURE)
        position = match.end()
    pattern_parts.append(_escape_d4_rendered_text(english[position:]))

    replacement_parts: list[str] = []
    position = 0
    for match in D4_VALUE_TOKEN_RE.finditer(japanese):
        replacement_parts.append(japanese[position : match.start()])
        capture = capture_by_token.get(_d4_value_token_id(match.group(0)))
        if capture is None:
            return None
        replacement_parts.append(f"${capture}")
        position = match.end()
    replacement_parts.append(japanese[position:])

    pattern = "".join(pattern_parts)
    replacement = "".join(replacement_parts)
    if "{" in replacement or "}" in replacement:
        return None
    try:
        re.compile(pattern)
    except re.error:
        return None
    return pattern, replacement


def create_d4_description_pairs(
    english: str, japanese: str
) -> list[tuple[str, str]]:
    """全文に加え、Maxrollが別ブロックへ描画する改行単位の規則も作る。"""
    pairs: list[tuple[str, str]] = []

    def expand_conditionals(value: str) -> list[str]:
        match = D4_CONDITIONAL_RE.search(value)
        if not match:
            return [value]
        prefix = value[: match.start()]
        suffix = value[match.end() :]
        true_branch = (
            match.group("true_else")
            if match.group("true_else") is not None
            else match.group("true_only")
        )
        branches = [true_branch or "", match.group("false") or ""]
        expanded: list[str] = []
        for branch in branches:
            expanded.extend(
                prefix + branch + remainder
                for remainder in expand_conditionals(suffix)
            )
        return expanded

    # RuneDescriptionの{s1}などは実際の数値に置き換わるため、
    # 色タグだけを除去したテンプレート規則を通常の説明文規則より先に作る。
    def strip_format_tags_preserving_placeholders(value: str) -> str:
        return D4_FORMAT_TAG_RE.sub(
            lambda match: (
                match.group(0)
                if PLACEHOLDER_RE.fullmatch(match.group(0))
                else ""
            ),
            value,
        ).strip()

    def append_description_and_line_pairs(
        english_value: str,
        japanese_value: str,
    ) -> None:
        description_pair = create_d4_description_pair(
            english_value,
            japanese_value,
        )
        if description_pair and description_pair not in pairs:
            pairs.append(description_pair)

        english_lines = [
            line.strip()
            for line in english_value.splitlines()
            if line.strip()
        ]
        japanese_lines = [
            line.strip()
            for line in japanese_value.splitlines()
            if line.strip()
        ]
        if len(english_lines) > 1 and len(english_lines) == len(japanese_lines):
            for english_line, japanese_line in zip(
                english_lines,
                japanese_lines,
            ):
                line_pair = create_d4_description_pair(
                    english_line,
                    japanese_line,
                )
                if line_pair and line_pair not in pairs:
                    pairs.append(line_pair)

    template_pair = create_template_pair(
        strip_format_tags_preserving_placeholders(english),
        strip_format_tags_preserving_placeholders(japanese),
    )
    if template_pair:
        pairs.append(template_pair)

    append_description_and_line_pairs(english, japanese)

    english_variants = expand_conditionals(english)
    japanese_variants = expand_conditionals(japanese)
    if (
        len(english_variants) > 1
        and len(english_variants) == len(japanese_variants)
    ):
        for english_variant, japanese_variant in zip(
            english_variants,
            japanese_variants,
        ):
            append_description_and_line_pairs(
                english_variant,
                japanese_variant,
            )
    return pairs


def create_paragon_tooltip_ui_pairs(
    en_row: CsvRow, ja_row: CsvRow
) -> list[tuple[str, str]]:
    """公式UI辞書からMaxrollのグリフツールチップ表示用ルールを作る。"""
    english = ICON_TAG_RE.sub("", clean_color_tags(en_row.translation)).strip()
    japanese = ICON_TAG_RE.sub("", clean_color_tags(ja_row.translation)).strip()
    pairs: list[tuple[str, str]] = []

    # Maxrollはこの見出しと注記を別DOMへ分ける。全文規則にすると、同じ
    # コンテナ内の要件値spanまで長文再配置の対象になるため、行単位だけにする。
    if en_row.key == "ThresholdRequirementsInRangeHeader":
        english_lines = [
            line.strip() for line in english.splitlines() if line.strip()
        ]
        japanese_lines = [
            line.strip() for line in japanese.splitlines() if line.strip()
        ]
        if len(english_lines) == len(japanese_lines):
            for english_line, japanese_line in zip(
                english_lines,
                japanese_lines,
            ):
                line_pair = create_d4_description_pair(
                    english_line,
                    japanese_line,
                )
                if line_pair and line_pair not in pairs:
                    pairs.append(line_pair)
    else:
        key, value, rejection = make_translation_pair(english, japanese)
        if rejection is None:
            pairs.append((key, value))

    # Maxrollは公式の「Level {s1}」を「Level: 25」と表示する。
    if en_row.key == "GlyphLevel" and "{s1}" in japanese.lower():
        label = re.sub(r"\{s1\}", "", japanese, flags=re.IGNORECASE).strip()
        if label:
            pairs.append(
                (
                    rf"Level:\s*{D4_VALUE_CAPTURE}",
                    f"{label}: $1",
                )
            )

    # グリフソケットでは公式のボーナス文から条件だけを括弧内の別行にする。
    if en_row.key in {
        "ThresholdBonusAttribute",
        "ThresholdBonusAttributeGlyphModified",
    }:
        english_condition = re.search(
            r"\bif\s+requirements\s+met\b",
            english,
            flags=re.IGNORECASE,
        )
        japanese_prefix = re.split(
            r"\{s1\}",
            japanese,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        japanese_condition = re.sub(
            r"^[^:：]+[:：]\s*",
            "",
            japanese_prefix,
        ).strip(" \t、,")
        if english_condition and japanese_condition:
            template_pair = create_template_pair(english, japanese)
            japanese_label = re.match(r"^[^:：]+[:：]", japanese)
            if template_pair and japanese_label:
                # Maxrollでは{s1}が「+4% Maximum Life」のような完成済み
                # 効果文なので、「1つ追加」ではなく効果と条件をそのまま示す。
                pairs = [
                    pair for pair in pairs if pair[0] != template_pair[0]
                ]
                pairs.insert(
                    0,
                    (
                        template_pair[0],
                        f"{japanese_label.group(0)} $1"
                        f"（{japanese_condition}）",
                    ),
                )
            pairs.append(
                (
                    rf"\({_escape_regex_text(english_condition.group(0))}\)",
                    f"（{japanese_condition}）",
                )
            )

    return list(dict.fromkeys(pairs))


def create_rune_tooltip_pairs(
    en_row: CsvRow, ja_row: CsvRow
) -> list[tuple[str, str]]:
    """連結ルーン名とルーンワードの表示用文言を含む規則を作る。"""
    if (
        en_row.file_name == "UIToolTips"
        and en_row.key == "RunewordCompleteWithFrequency"
    ):
        return [
            (
                rf"\({D4_VALUE_CAPTURE}\s+(?:times|time)\)",
                "（これを$1回行う）",
            )
        ]

    pairs = create_d4_description_pairs(
        en_row.translation,
        ja_row.translation,
    )
    if en_row.key in {"RuneDescription", "RuneInternalCooldown"}:
        # ルーン効果の{s1}は影の数などの実数値。数値用の経路で
        # 単複数指定も展開し、内部表記をそのまま照合しない。
        def numeric_rune_values(text: str) -> str:
            text = D4_PLURAL_TOKEN_RE.sub(
                lambda match: "|4" + match.group(1).strip() + ":"
                + (match.group(2) or match.group(1)).strip() + ";",
                text,
            )
            return re.sub(
                r"\{s(\d+)\}",
                lambda match: f"[D4T_RUNE_VALUE_{match.group(1)}]",
                text,
                flags=re.IGNORECASE,
            )

        rendered_pair = create_d4_description_pair(
            numeric_rune_values(en_row.translation),
            numeric_rune_values(ja_row.translation),
        )
        if rendered_pair and rendered_pair not in pairs:
            pairs.insert(0, rendered_pair)
    if en_row.key != "Name":
        return pairs

    english = clean_color_tags(en_row.translation)
    japanese = clean_color_tags(ja_row.translation)
    if not english or not japanese:
        return pairs

    # Maxrollは条件ルーン名と効果ルーン名を空白なしで連結する。
    # 通常の単語境界規則は残しつつ、連結位置だけを追加規則で補う。
    if re.match(r"^Item_(?:S\d+_)?Rune_Condition_", en_row.file_name):
        pairs.append(
            (
                rf"{_escape_regex_literal(english)}(?=[A-Z])",
                japanese,
            )
        )
    elif re.match(r"^Item_(?:S\d+_)?Rune_Effect_", en_row.file_name):
        pairs.append(
            (
                rf"(?<=[a-z]){_escape_regex_literal(english)}",
                japanese,
            )
        )
    return pairs


def create_drop_source_pairs(
    en_row: CsvRow, ja_row: CsvRow
) -> list[tuple[str, str]]:
    """カンマ区切りで照合するドロップ元ボス名辞書を作る。"""
    english = clean_color_tags(en_row.translation)
    japanese = clean_color_tags(ja_row.translation)
    if not english or not japanese:
        return []

    pairs = [(DROP_SOURCE_KEY_PREFIX + english, japanese)]
    if english == "Duriel":
        # Maxroll固有表記「Duriel, King of Maggots」の後半用。
        pairs.append(
            (
                DROP_SOURCE_KEY_PREFIX + "King of Maggots",
                "マゴット・キング",
            )
        )
    return pairs


def create_flavor_description_pairs(
    english: str, japanese: str
) -> list[tuple[str, str]]:
    """CSV版に加え、Maxrollが本文だけを引用符で囲む表示にも対応する。"""
    pairs = create_d4_description_pairs(english, japanese)
    clean_english = D4_FORMAT_TAG_RE.sub("", english).strip()
    attribution = FLAVOR_ATTRIBUTION_RE.match(clean_english)
    if attribution:
        maxroll_english = (
            f'"{attribution.group("body")}"'
            f'{attribution.group("spacing")}'
            f'{attribution.group("attribution")}'
        )
        maxroll_pair = create_d4_description_pair(maxroll_english, japanese)
        if maxroll_pair and maxroll_pair not in pairs:
            pairs.append(maxroll_pair)
    return pairs


def create_weapon_tooltip_pairs(
    en_row: CsvRow, ja_row: CsvRow
) -> list[tuple[str, str]]:
    """Maxrollの武器評価行を数値込みの日本語語順で生成する。"""
    english = D4_FORMAT_TAG_RE.sub("", en_row.translation).strip()
    japanese = D4_FORMAT_TAG_RE.sub("", ja_row.translation).strip()

    if en_row.key == "TooltipRatingLabelDPS":
        return [
            (
                rf"{D4_VALUE_CAPTURE}\s+{_escape_regex_text(english)}",
                f"$1 {japanese}",
            )
        ]

    if en_row.key == "TooltipRatingLabelDamagePerHit":
        english_label = TEMPLATE_TOKEN_RE.sub("", english).strip()
        japanese_label = TEMPLATE_TOKEN_RE.sub("", japanese).strip()
        return [
            (
                rf"{D4_VALUE_CAPTURE}\s+{_escape_regex_text(english_label)}",
                f"{japanese_label}$1",
            )
        ]

    if en_row.key == "TooltipRatingLabelAttackSpeed":
        english_label = TEMPLATE_TOKEN_RE.sub("", english).strip()
        japanese_label = TEMPLATE_TOKEN_RE.sub("", japanese).strip()
        return [
            (
                rf"{D4_VALUE_CAPTURE}\s+{_escape_regex_text(english_label)}"
                r"\s+(\([^)]*\))",
                f"{japanese_label}$1 $2",
            )
        ]

    return create_d4_description_pairs(en_row.translation, ja_row.translation)


def create_seal_slot_pairs(en_row: CsvRow, ja_row: CsvRow) -> list[tuple[str, str]]:
    """スロット数は文字列用の汎用captureではなく数値として扱う。"""
    def numeric_slots(text: str) -> str:
        text = text.replace("{s1}", "[D4T_SEAL_SLOTS]")
        return re.sub(
            r"\{c_number\}(\d+)\{/c\}",
            lambda match: f"[D4T_SEAL_COUNT_{match.group(1)}]",
            text,
        )
    pair = create_d4_description_pair(
        numeric_slots(en_row.translation), numeric_slots(ja_row.translation)
    )
    return [pair] if pair else []


def create_attribute_tooltip_pairs(
    en_row: CsvRow, ja_row: CsvRow
) -> list[tuple[str, str]] | None:
    """Maxrollの描画時に展開されるAttributeDescriptionsの制御記法を処理する。"""
    if _is_soul_splinter_file(en_row.file_name):
        english = clean_color_tags(en_row.translation)
        japanese = clean_color_tags(ja_row.translation)
        en_stat = re.fullmatch(r"\+(\d+(?:,\d{3})*(?:\.\d+)?)\s+(.+)", english)
        ja_stat = re.fullmatch(r"(.+)\+(\d+(?:,\d{3})*(?:\.\d+)?)", japanese)
        if en_stat:
            if not ja_stat or en_stat[1].replace(',', '') != ja_stat[2].replace(',', ''):
                return []
            # 4375と4,375の両方を一つの数値として扱う。サイトの値倍率にも追従する。
            return [(r"\+(\d+(?:,\d{3})*(?:\.\d+)?)\s+" + _escape_regex_text(en_stat[2]),
                     ja_stat[1] + "+$1")]
        return create_d4_description_pairs(english, japanese)
    if en_row.file_name == "UIToolTips" and en_row.key == "Socketable":
        return create_d4_description_pairs(en_row.translation, ja_row.translation)
    if re.fullmatch(r"S\d+_Socketable_\w+", en_row.key):
        # VALUEとPowerTag式が混在する長文。VALUEを安定した数値参照に
        # 正規化し、一般属性の長さ制限を通さず装備効果用の生成処理へ渡す。
        # 名前付き参照の照合は維持し、英日で別の効果を指す場合は除外する。
        def normalize_values(text: str) -> str:
            return TEMPLATE_TOKEN_RE.sub(
                lambda match: "[D4T_" + (_token_id(match.group(0)) or "").strip("{}") + "]",
                text,
            )

        english = normalize_values(en_row.translation)
        japanese = normalize_values(ja_row.translation)
        # S15の提供CSVではAzmodanの日本語にAndarielの効果が誤収録されている。
        # 確認済みの英日原文が両方一致する場合だけ、英文に基づく補正訳を使う。
        # 将来修正された日本語や別効果へ変更された英文には適用しない。
        expected_english = (
            'You gain [D4T_VALUE2] Maximum Life, but your Maximum Primary Resource '
            'is reduced by [PowerTag.S15_Socketable_Azmodan."Script Formula 1" * 100|%|].'
        )
        broken_japanese = (
            '攻撃速度とクリティカルヒット率が[D4T_VALUE2]上昇するが、プライマリリソースコストが'
            '[PowerTag.S15_Socketable_Andariel."Script Formula 1" * 100|%|]増加する。'
        )
        compact = lambda value: re.sub(r"\s+", "", strip_d4_format_tags_preserving_values(value))
        if (
            en_row.key == "S15_Socketable_Azmodan"
            and compact(english) == compact(expected_english)
            and compact(japanese) == compact(broken_japanese)
        ):
            japanese = (
                'ライフ最大値が[D4T_VALUE2]増加するが、プライマリリソース最大値が'
                '[PowerTag.S15_Socketable_Azmodan."Script Formula 1" * 100|%|]減少する。'
            )
        pairs = create_d4_description_pairs(english, japanese)
        if re.fullmatch(r"S\d+_Socketable_Skarn", en_row.key):
            # 全文内の下線付き用語を独立したspanとして保持するための対応。
            # 英日とも強調語が一つだけの場合に限り、CSVから訳を取り出す。
            term_re = r"\{c_important\}([^{}]+)\{/c\}"
            en_terms = re.findall(term_re, en_row.translation)
            ja_terms = re.findall(term_re, ja_row.translation)
            if en_terms == ["Monster Power"] and len(ja_terms) == 1:
                pairs.append((_escape_regex_text(en_terms[0]), ja_terms[0]))
        # この装着効果ではMaxrollの加算表記が「50%[+]」になる。
        # 既存カテゴリの生成キーを一括変更せず、この経路だけ対応する。
        socketable_capture = D4_VALUE_CAPTURE.replace(r"%\[x\]", r"%\[(?:x|\+)\]")
        return [(pattern.replace(D4_VALUE_CAPTURE, socketable_capture), value)
                for pattern, value in pairs]
    if en_row.key != "Evade_Reduce_Cooldown_On_Attack":
        return None

    english = D4_FORMAT_TAG_RE.sub("", en_row.translation).strip()
    japanese = D4_FORMAT_TAG_RE.sub("", ja_row.translation).strip()
    english_value = D4_VALUE_TOKEN_RE.search(english)
    japanese_value = D4_VALUE_TOKEN_RE.search(japanese)
    if not english_value or not japanese_value:
        return []

    english_prefix = english[: english_value.start()]
    english_suffix = english[english_value.end() :].strip()
    plural = re.fullmatch(r"\|4([^:;]+):([^;]+);", english_suffix)
    if not plural:
        return []

    japanese_replacement = (
        japanese[: japanese_value.start()]
        + "$1"
        + japanese[japanese_value.end() :]
    )
    plural_forms = sorted(
        (plural.group(1), plural.group(2)),
        key=len,
        reverse=True,
    )
    pattern = (
        _escape_regex_text(english_prefix)
        + D4_VALUE_CAPTURE
        + r"\s+(?:"
        + _escape_regex_text(plural_forms[0])
        + "|"
        + _escape_regex_text(plural_forms[1])
        + ")"
    )
    return [(pattern, japanese_replacement)]


def make_attribute_alias_pairs(
    en_row: CsvRow,
    ja_row: CsvRow,
    key: str,
    value: str,
    resource_names: Iterable[tuple[str, str]] = (),
) -> list[tuple[str, str]]:
    """Maxroll固有の属性値表記とパラゴン要件行を公式CSVから派生する。"""
    pairs: list[tuple[str, str]] = []

    if en_row.key in {"Resource_Regen_Per_Second", "Resource_Regen_Bonus_Percent"}:
        for en_name, ja_name in resource_names:
            english = en_row.translation.replace("{VALUE1}", en_name)
            japanese = ja_row.translation.replace("{VALUE1}", ja_name)
            pair = create_template_pair(english, japanese)
            if pair:
                pairs.append(pair)
                # 数値が別ノードでも、リソース名だけ先に翻訳されないようにする。
                en_label = TEMPLATE_TOKEN_RE.sub("", english).strip()
                ja_label = TEMPLATE_TOKEN_RE.sub("", japanese).strip()
                pairs.append((_escape_regex_text(en_label), ja_label))

    # Maximum Lifeには同じ英語形で「最大ライフ」と「ライフ最大値の」の
    # 2訳がある。パラゴンが使う百分率形式だけを限定し、公式の百分率訳を採る。
    if en_row.key in {
        "Hitpoints_Max_Percent_Bonus_Item",
        "Hitpoints_Max_Percent_Bonus",
    }:
        english_token = D4_VALUE_TOKEN_RE.search(en_row.translation)
        japanese_token = D4_VALUE_TOKEN_RE.search(ja_row.translation)
        if english_token and japanese_token:
            english_label = (
                en_row.translation[: english_token.start()]
                + en_row.translation[english_token.end() :]
            ).strip()
            japanese_replacement = (
                ja_row.translation[: japanese_token.start()]
                + "$1"
                + ja_row.translation[japanese_token.end() :]
            )
            pairs.append(
                (
                    rf"{PERCENT_CAPTURE}\s*"
                    rf"{_escape_regex_text(english_label)}",
                    japanese_replacement,
                )
            )

    # 条件付きノードのMaxroll表示は「必要値 / 現在値 Attribute」。
    # ゲーム内表示の「現在値 / Attribute+必要値」へ並べ替える。
    if en_row.key in {
        "Strength",
        "Intelligence",
        "Willpower",
        "Dexterity",
    }:
        english_token = D4_VALUE_TOKEN_RE.search(en_row.translation)
        japanese_token = D4_VALUE_TOKEN_RE.search(ja_row.translation)
        if english_token and japanese_token:
            english_label = (
                en_row.translation[: english_token.start()]
                + en_row.translation[english_token.end() :]
            ).strip()
            japanese_label = (
                ja_row.translation[: japanese_token.start()]
                + ja_row.translation[japanese_token.end() :]
            ).strip()
            if english_label and japanese_label:
                pairs.append(
                    (
                        rf"\+?{PARAGON_REQUIREMENT_VALUE_CAPTURE}\s*/\s*"
                        rf"{PARAGON_REQUIREMENT_VALUE_CAPTURE}\s+"
                        rf"{_escape_regex_text(english_label)}",
                        f"$1 / {japanese_label}+$2",
                    )
                )
                pairs.append(
                    (
                        rf"\+?{PARAGON_REQUIREMENT_VALUE_CAPTURE}\s*/\s*"
                        rf"{_escape_regex_text(english_label)}\s*\+?"
                        rf"{PARAGON_REQUIREMENT_VALUE_CAPTURE}",
                        f"$1 / {japanese_label}+$2",
                    )
                )

    return pairs


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
    is_generated_template = template_pair is not None
    if template_pair:
        english, japanese = template_pair
    elif "{" in english or "}" in english or "{" in japanese or "}" in japanese:
        return "", "", "unsupported-tag"

    if len(english) >= 200:
        return "", "", "too-long"
    if not is_generated_template and len(REGEX_SPECIAL_RE.findall(english)) > 14:
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
    with path.open("r", encoding="utf-8-sig") as handle:
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
    en_fallback_rows = unique_fallback_rows(en_rows.values())
    player_skill_names = {
        make_translation_pair(row.translation, "スキル名")[0]
        for row in en_rows.values()
        if row.file_name.startswith(PLAYER_SKILL_POWER_PREFIXES) and row.key in NAME_FIELDS
    }

    resource_names: list[tuple[str, str]] = []
    for row in en_rows.values():
        if row.file_name != "UIToolTips" or not row.key.startswith("Resource_Type_"):
            continue
        counterpart = ja_rows.get(row.identity)
        if counterpart is None and en_fallback_rows.get(fallback_identity(row)) is not None:
            counterpart = ja_fallback_rows.get(fallback_identity(row))
        if counterpart:
            en_name = clean_color_tags(row.translation)
            ja_name = clean_color_tags(counterpart.translation)
            if en_name and ja_name and not re.search(r"[{}\ufffd]", en_name + ja_name):
                resource_names.append((en_name, ja_name))

    stats: Counter[str] = Counter()
    category_selected: Counter[str] = Counter()
    category_added: Counter[str] = Counter()
    category_overwritten: Counter[str] = Counter()
    candidates: dict[str, tuple[str, str]] = {}
    conflicts: set[str] = set()

    for identity, en_row in en_rows.items():
        category = selected_category(en_row, categories)
        if category is None:
            continue
        # 装備のランダム名断片「The」は冠詞に誤爆するため取り込まない。
        if category == "rare-names" and clean_color_tags(en_row.translation).casefold() == "the":
            stats["rejected:common-article"] += 1
            continue
        stats["selected"] += 1
        category_selected[category] += 1

        ja_row = ja_rows.get(identity)
        if ja_row is None:
            ja_row = (
                ja_fallback_rows.get(fallback_identity(en_row))
                if en_fallback_rows.get(fallback_identity(en_row)) is not None
                else None
            )
            if ja_row is None:
                stats["missing-ja"] += 1
                continue
            stats["matched-ja-fallback"] += 1

        attribute_pairs = (
            create_attribute_tooltip_pairs(en_row, ja_row)
            if category == "attributes"
            else None
        )
        paragon_ui_pairs = (
            create_paragon_tooltip_ui_pairs(en_row, ja_row)
            if category == "paragon"
            and en_row.file_name == "ParagonBoardUI"
            else None
        )
        seal_slot_pairs = (
            create_seal_slot_pairs(en_row, ja_row)
            if en_row.file_name == "UIToolTips" and en_row.key == "SealSlotToolTip"
            else None
        )
        if paragon_ui_pairs is not None:
            if not paragon_ui_pairs:
                stats["rejected:unsupported-paragon-ui"] += 1
                continue
            pairs = paragon_ui_pairs
            rejection = None
        elif attribute_pairs is not None:
            if not attribute_pairs:
                stats["rejected:unsupported-attribute"] += 1
                continue
            pairs = attribute_pairs
            rejection = None
        elif seal_slot_pairs is not None:
            if not seal_slot_pairs:
                stats["rejected:unsupported-seal-slots"] += 1
                continue
            pairs = seal_slot_pairs
            rejection = None
        elif (
            category in TOOLTIP_TEXT_CATEGORIES
            or (
                category == "paragon"
                and _is_paragon_description_row(en_row)
            )
        ):
            effect_pairs = (
                create_d4_description_pairs(
                    ICON_TAG_RE.sub("", en_row.translation),
                    ICON_TAG_RE.sub("", ja_row.translation),
                )
                if category == "prism-descriptions"
                else create_seal_slot_pairs(en_row, ja_row)
                if en_row.file_name == "Affix_Talisman_SealAffix_AdditionalCharmSlot"
                else create_drop_source_pairs(en_row, ja_row)
                if category == "drop-sources"
                else create_weapon_tooltip_pairs(en_row, ja_row)
                if category == "weapon-tooltip"
                else create_rune_tooltip_pairs(en_row, ja_row)
                if category == "runes"
                else create_flavor_description_pairs(
                    en_row.translation, ja_row.translation
                )
                if category == "flavors"
                else create_d4_description_pairs(
                    en_row.translation, ja_row.translation
                )
            )
            if not effect_pairs:
                stats["rejected:unsupported-effect"] += 1
                continue
            pairs = effect_pairs
            rejection = None
        else:
            key, value, rejection = make_translation_pair(
                ICON_TAG_RE.sub("", en_row.translation).strip() if category == "items" else en_row.translation,
                ICON_TAG_RE.sub("", ja_row.translation).strip() if category == "items" else ja_row.translation,
            )
        if rejection:
            stats[f"rejected:{rejection}"] += 1
            continue

        if (
            category not in TOOLTIP_TEXT_CATEGORIES
            and attribute_pairs is None
            and paragon_ui_pairs is None
            and seal_slot_pairs is None
            and not (
                category == "paragon"
                and _is_paragon_description_row(en_row)
            )
        ):
            pairs = [(key, value)]
            if (category == "items"
                    and en_row.file_name.startswith("Item_X2_HoradricCube_TuningStone_")
                    and key.endswith(" Tuning Prism") and value.endswith("同調プリズム")):
                # 記事の複数形と共通見出し。個別名の長い規則を優先して照合する。
                pairs.extend([(key + "s", value), ("Tuning Prisms?", "同調プリズム")])
            if category == "attributes":
                pairs.extend(
                    make_attribute_alias_pairs(
                        en_row,
                        ja_row,
                        key,
                        value,
                        resource_names,
                    )
                )
            if category == "affixes" and _is_legendary_affix_file(en_row.file_name):
                # of Metamorphosis等から作る省略名で現行スキル名を上書きしない。
                # 正式な化身名の規則は残し、衝突する省略名だけを除外する。
                for alias_key, alias_value in make_affix_alias_pairs(key, value):
                    if alias_key in player_skill_names:
                        stats["affix-alias-shadowed-by-skill"] += 1
                    else:
                        pairs.append((alias_key, alias_value))

        for candidate_key, candidate_value in pairs:
            if candidate_key in conflicts:
                stats["conflict-row"] += 1
                continue
            previous = candidates.get(candidate_key)
            if previous and previous[0] != candidate_value:
                # Eagle等は装備のランダム名断片にも存在する。攻略用語として
                # 明示されたスキルタグを、CSVの並び順によらず優先する。
                if previous[1] == "rare-names" and category == "skill-tags":
                    candidates[candidate_key] = (candidate_value, category)
                    stats["skill-tag-preferred-over-rare-name"] += 1
                    continue
                if previous[1] == "skill-tags" and category == "rare-names":
                    stats["skill-tag-preferred-over-rare-name"] += 1
                    continue
                # 同じ英語効果に通常版・旧シーズン版・チャーム版で訳語差が
                # ある場合、先に現れる現行の基本版を採用する。
                if category in TOOLTIP_TEXT_CATEGORIES:
                    stats["effect-conflict-kept-first"] += 1
                    continue
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
        if key in existing and existing[key] != value:
            stats["existing-value-differs"] += 1
        if key in existing and not overwrite_existing:
            stats["kept-existing"] += 1
            continue
        if key in existing and existing[key] == value:
            stats["unchanged"] += 1
            continue
        if key in existing:
            stats["overwritten"] += 1
            category_overwritten[category] += 1
        else:
            stats["added"] += 1
            category_added[category] += 1
        merged[key] = value

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
        "overwritten_by_category": dict(category_overwritten),
        "counts": dict(stats),
        "conflict_keys": sorted(conflicts),
        "added_rules": [
            {"key": key, "value": value, "category": category}
            for key, (value, category) in candidates.items() if key not in existing
        ],
        "existing_value_differences": [
            {"key": key, "existing": existing[key], "candidate": value,
             "category": category}
            for key, (value, category) in candidates.items()
            if key in existing and existing[key] != value
        ],
        "overwritten_rules": [
            {"key": key, "previous": existing[key], "value": value,
             "category": category}
            for key, (value, category) in candidates.items()
            if overwrite_existing and key in existing and existing[key] != value
        ],
    }
    return merged, report


def compare_season_rules(previous: dict[str, str], current: dict[str, str],
                         existing: dict[str, str]) -> dict[str, object]:
    """生成済みルールで比較する。CSVの行数やゲーム内の新規実装数ではない。"""
    new_keys = sorted(current.keys() - previous.keys())
    changed = sorted(key for key in current.keys() & previous.keys()
                     if current[key] != previous[key])
    needed = current.keys() - existing.keys()
    return {
        "previous_rules": len(previous), "current_rules": len(current),
        "new_rule_keys": new_keys,
        "changed_translations": [
            {"key": key, "previous": previous[key], "current": current[key]}
            for key in changed
        ],
        "removed_rule_keys": sorted(previous.keys() - current.keys()),
        "new_rules_missing_from_dictionary": len(set(new_keys) & needed),
        "previous_rules_missing_from_dictionary": len(previous.keys() & needed),
    }


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
    parser.add_argument("--previous-en", type=Path, help="比較元シーズンの英語 CSV")
    parser.add_argument("--previous-ja", type=Path, help="比較元シーズンの日本語 CSV")
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
    print(f"Overwritten  : {counts.get('overwritten', 0)}")
    print(f"Kept existing: {counts.get('kept-existing', 0)}")
    print(f"Conflicts    : {counts.get('conflict-key', 0)}")
    print(f"Existing translation differences: {counts.get('existing-value-differs', 0)}")
    print(f"Corrupt skip : {counts.get('rejected:corrupt', 0)}")
    print(f"Result       : {report['result']}")
    print("Changes by category (added / overwritten):")
    added = report["added_by_category"]
    assert isinstance(added, dict)
    overwritten = report["overwritten_by_category"]
    for category in report["categories"]:
        print(f"  {category:12}: {added.get(category, 0)} / {overwritten.get(category, 0)}")
    if "season_comparison" in report:
        comparison = report["season_comparison"]
        print(f"New season rules missing: {comparison['new_rules_missing_from_dictionary']}")
        print(f"Previous rules missing  : {comparison['previous_rules_missing_from_dictionary']}")
        print(f"Changed translations    : {len(comparison['changed_translations'])}")
    print("Dry run: dictionary was not written." if dry_run else f"Saved: {output}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_categories:
        for name, rule in RULES.items():
            print(f"{name:12} {rule.description}")
        return 0
    if args.en is None or args.ja is None:
        parser.error("--en と --ja の両方を指定してください")
    if (args.previous_en is None) != (args.previous_ja is None):
        parser.error("--previous-en と --previous-ja は両方を指定してください")
    categories = args.categories

    try:
        base_path = args.base or args.output
        existing = load_json(base_path)
        merged, report = merge_csv_files(
            args.en,
            args.ja,
            existing,
            categories=categories,
            overwrite_existing=args.overwrite_existing,
        )
        if args.previous_en:
            previous, _ = merge_csv_files(args.previous_en, args.previous_ja, {},
                                           categories=categories)
            current, _ = merge_csv_files(args.en, args.ja, {}, categories=categories)
            report["season_comparison"] = compare_season_rules(previous, current, existing)
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
