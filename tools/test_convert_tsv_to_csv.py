import csv
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from convert_tsv_to_csv import COLUMNS, convert_file
from merge_csv_translations import load_csv


class ConvertTsvToCsvTests(unittest.TestCase):
    def test_cli_converts_arbitrary_season_directory_and_deduplicates_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            season = Path(directory) / "S99"
            season.mkdir()
            for name in ("en.tsv", "ja.TSV"):
                (season / name).write_text("\t".join(COLUMNS) + "\t\n"
                                          "1\tName\t0\t2\tDesc\ttext\n", encoding="utf-8")
            (season / "notes.txt").write_text("ignore", encoding="utf-8")
            nested = season / "nested"
            nested.mkdir()
            (nested / "other.tsv").write_text("ignore", encoding="utf-8")
            command = [sys.executable, str(Path(__file__).with_name("convert_tsv_to_csv.py"))]
            result = subprocess.run(command + [str(season), str(season / "en.tsv")],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(sorted(p.name for p in season.glob("*.csv")), ["en.csv", "ja.csv"])
            self.assertFalse((nested / "other.csv").exists())
            result = subprocess.run(command + [str(season)], capture_output=True)
            self.assertEqual(result.returncode, 1)

    def test_cli_rejects_empty_directory_and_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(Path(__file__).with_name("convert_tsv_to_csv.py"))]
            for path in (Path(directory), Path(directory) / "missing.tsv"):
                result = subprocess.run(command + [str(path)], capture_output=True)
                self.assertEqual(result.returncode, 2)

    def test_multiline_quotes_tabs_empty_value_and_importer(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.tsv"
            output = source.with_suffix(".csv")
            original = ("\ufeff" + "\t".join(COLUMNS) + "\t\r\n"
                        '1\tName\t0\t2\tDesc\t日本語, "quoted"\t\r\n'
                        "\r\n1.\tLicense\t\r\n"
                        "2\tName\t1\t3\tEmpty\t\r\n"
                        "3\tName\t2\t4\tTabbed\tleft\tright\t\r\n").encode("utf-8")
            source.write_bytes(original)
            self.assertEqual(convert_file(source, output), (3, 2))
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle, strict=True))
            self.assertEqual(rows[0], COLUMNS)
            self.assertTrue(all(len(row) == 6 for row in rows))
            self.assertEqual(rows[1][5], '日本語, "quoted"\n\n1.\tLicense\t')
            self.assertEqual(rows[2][5], "")
            self.assertEqual(rows[3][5], "left\tright")
            self.assertIn('"日本語, ""quoted""', output.read_text(encoding="utf-8"))
            loaded, duplicates = load_csv(output)
            self.assertEqual(duplicates, 0)
            self.assertEqual(loaded[tuple(rows[1][:5])].translation, rows[1][5])
            self.assertEqual(source.read_bytes(), original)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                convert_file(source, output)
            self.assertEqual(output.read_bytes(), before)

    def test_rejects_invalid_input_without_creating_output(self):
        header = "\t".join(COLUMNS) + "\n"
        cases = ["", "bad header\n", header, header + "orphan\n",
                 header + "1\tName\t0\t2\tDesc\n",
                 header + "1\tName\tbad\t2\tDesc\ttext\n",
                 header + "1\tName\t0\t2\tDesc\ttext\n2\tbroken\n"]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.tsv"
            output = source.with_suffix(".csv")
            for content in cases:
                with self.subTest(content=content):
                    source.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, r"input.tsv:"):
                        convert_file(source, output)
                    self.assertFalse(output.exists())

    def test_rejects_same_input_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.tsv"
            source.write_text("unchanged", encoding="utf-8")
            with self.assertRaises(ValueError):
                convert_file(source, source)
            self.assertEqual(source.read_text(encoding="utf-8"), "unchanged")


if __name__ == "__main__":
    unittest.main()
