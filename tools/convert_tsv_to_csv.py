#!/usr/bin/env python3
"""Convert Diablo IV raw TSV exports, restoring unescaped multiline text."""

import argparse
import csv
from pathlib import Path
import re


COLUMNS = ["SNO", "FileName", "Index", "KeyHash", "Key", "Translation"]


def read_tsv(path: Path) -> tuple[list[list[str]], int]:
    rows = []
    continuation_lines = 0
    parts = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = handle.readline().rstrip("\r\n").rstrip("\t").split("\t")
        if header != COLUMNS:
            raise ValueError(f"{path}:1: expected header: {COLUMNS}")
        for line_number, raw in enumerate(handle, 2):
            line = raw.rstrip("\r\n")
            fields = line.split("\t", 5)
            valid_identity = len(fields) >= 5 and all(
                re.fullmatch(r"[0-9]+", fields[i]) for i in (0, 2, 3)
            ) and bool(fields[1]) and bool(fields[4])
            if valid_identity and len(fields) == 6:
                if rows:
                    rows[-1][5] = "\n".join(parts)
                # Only discard trailing export separators on record lines.
                # The fifth separator still represents an empty Translation.
                fields[5] = fields[5].rstrip("\t")
                rows.append(fields)
                parts = [fields[5]]
            elif len(fields) >= 5 or (len(fields) > 1 and re.fullmatch(r"[0-9]+", fields[0])):
                raise ValueError(f"{path}:{line_number}: ambiguous or malformed record")
            elif not rows:
                raise ValueError(f"{path}:{line_number}: text before the first record")
            else:
                parts.append(line)
                continuation_lines += 1
    if not rows:
        raise ValueError(f"{path}: no records")
    rows[-1][5] = "\n".join(parts)
    return rows, continuation_lines


def convert_file(source: Path, destination: Path) -> tuple[int, int]:
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    rows, continuations = read_tsv(source)
    # Parse fully before creating output; never overwrite existing files.
    with destination.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return len(rows), continuations


def main() -> int:
    parser = argparse.ArgumentParser(description=(
        "Diablo IV の TSV を全フィールド引用符付き CSV に変換します。"
        "改行された説明文を復元し、ヘッダー・レコード末尾のタブを除去します。"))
    parser.add_argument("files", nargs="+", type=Path,
                        help="入力 TSV または TSV のあるフォルダー（複数指定可）")
    args = parser.parse_args()
    files = []
    seen = set()
    for path in args.files:
        if path.is_dir():
            candidates = sorted(p for p in path.iterdir()
                                if p.is_file() and p.suffix.lower() == ".tsv")
            if not candidates:
                parser.error(f"TSV files not found: {path}")
        elif path.is_file() and path.suffix.lower() == ".tsv":
            candidates = [path]
        else:
            parser.error(f"Expected an existing TSV file or directory: {path}")
        for candidate in candidates:
            if candidate.resolve() not in seen:
                seen.add(candidate.resolve())
                files.append(candidate)
    failed = False
    for source in files:
        destination = source.with_suffix(".csv")
        try:
            records, continuations = convert_file(source, destination)
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            print(f"ERROR: {error}")
            failed = True
        else:
            print(f"{source} -> {destination}: {records} records, "
                  f"{continuations} continuation lines restored")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
