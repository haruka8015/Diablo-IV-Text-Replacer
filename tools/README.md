# Diablo IV Text Replacer ツール

このディレクトリには、translations.json を管理するためのPythonツールが含まれています。

## 現在使用中のツール

## convert_stringlist_to_translations.py

Diablo IVのStringListファイルから translations.json を生成するスクリプトです。
各シーズン（S9、S10、S11など）のStringListファイルに対応しています。

### 使い方

```bash
# 基本的な使い方
python convert_stringlist_to_translations.py output.json --en temp/StringList_en.json --jp temp/StringList_jp.json

# 既存のtranslations.jsonとマージ（実運用時）
python convert_stringlist_to_translations.py ../sources/translations.json --en temp/S10_StringList_en.json --jp temp/S10_StringList_jp.json --merge-existing

# フィルタリングを無効化（すべての変換を含む）
python convert_stringlist_to_translations.py output.json --en temp/StringList_en.json --jp temp/StringList_jp.json --no-filter
```

### 機能

1. **自動抽出**: 以下のカテゴリから自動的に変換ルールを抽出
   - AttributeDescriptions（アイテム属性の説明）
   - アイテム名（ユニーク、レジェンダリー、ルーンなど）
   - パワーと化身（Aspect）
   - スキル名

2. **正規表現パターン生成**: 数値やプレースホルダーを含む文章は自動的に正規表現パターンに変換

3. **既存変換の保持**: `--merge-existing` オプションで既存の手動編集した変換を保持

4. **自動ソート**: キーの長さで降順ソート（長いキーを優先）

### 必要なファイル

- 英語の文字列データ（例: `StringList_en.json`、`S9_StringList_en.json`）
- 日本語の文字列データ（例: `StringList_jp.json`、`S9_StringList_jp.json`）

ファイルは `--en` と `--jp` オプションで指定可能。指定しない場合は `../temp/` ディレクトリから自動検索します。

### 出力例

```json
{
    "Chance to Make Enemies (\\w+) for (([+-]?\\d{1,3}(,\\d{3})*(\\.\\d+)?|\\.\\d+)) Seconds": "確率で敵を$2秒間$1にする",
    "Critical Strike Chance Against Vulnerable Enemies": "脆弱状態の敵へのクリティカルヒット率",
    "Upheaval": "打ち払い"
}
```

## アーカイブされたツール

以下のツールは `archive/` ディレクトリに移動されました。現在は convert_s9_to_translations.py がすべての機能を統合しています。

### archive/KVS_JSON_Sorter.py
translations.json をキーの長さ順にソートし、オプションで重複を除去する古いツール。
- 現在は convert_s9_to_translations.py に統合済み

### archive/find_duplicate_keys.py
translations.json 内の重複キーを検出する古いツール。

### archive/convert_blizzard_file.py
最初の変換スクリプト。機能が限定的だったため、convert_s9_to_translations.py で置き換えられました。