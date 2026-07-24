# Diablo IV Text Replacer ツール

このディレクトリには、translations.json を管理するためのPythonツールが含まれています。

## merge_csv_translations.py

`SNO,FileName,Index,KeyHash,Key,Translation` 形式の英語・日本語 CSV を
複合キーで対応付け、`sources/translations.json` に追加します。既存訳は維持され、
文字化けした日本語、対応のない行、同じ英語に対する競合訳は自動的に除外されます。

```bash
# まず追加件数や文字化け件数だけを確認
python tools/merge_csv_translations.py \
  --en tmp/S14/en.csv --ja tmp/S14/ja.csv --dry-run

# 確認後に sources/translations.json を更新
python tools/merge_csv_translations.py \
  --en tmp/S14/en.csv --ja tmp/S14/ja.csv

# 対象カテゴリを限定する例
python tools/merge_csv_translations.py output.json \
  --en tmp/S14/en.csv --ja tmp/S14/ja.csv \
  --categories items,affixes,paragon
```

既定カテゴリは
`attributes,weapon-tooltip,tooltip-labels,runes,items,affixes,effects,flavors,rare-names,powers,paragon,skill-tags,skills` です。
`effects` はレジェンダリー、ユニーク、ミシック効果の説明文からゲーム内の
装飾タグを除去し、Maxroll が表示する可変数値を正規表現に変換します。
`flavors` はユニーク、ミシック装備のフレーバーテキストを変換します。
`skill-tags` は `SkillTags` のタグ名と注釈本文を変換します。長い注釈ルールは
装備Tooltip内だけで照合されます。
`runes` はルーン名、ルーンワード名、条件・効果・オーバーフロー説明を変換し、
英語・日本語CSV間のIndex差も吸収します。
`tooltip-labels` はアイテムパワー、品質、祖霊・レジェンダリーなどの装備Tooltip
共通ラベルを変換します。
`weapon-tooltip` は秒間ダメージ、命中ごとのダメージ、秒間攻撃回数と速度区分を
数値込みの行単位で変換します。
レシピ名も必要な場合は `recipes` を `--categories` に追加できます。
`--list-categories` で内容を確認できます。既存訳を CSV で置き換える場合だけ
`--overwrite-existing` を指定してください。

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
