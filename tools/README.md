# Diablo IV Text Replacer ツール

このディレクトリには、translations.json を管理するためのPythonツールが含まれています。

## シーズン更新の手順

シーズン番号やファイル名はコードに固定していません。同じ6列の TSV なら、
次シーズンもツールの修正なしで利用できます。以下は S16 の例です。

### 1. 手作業：D4Analyzer から TSV を保存する

1. 保存先として `tmp/<シーズン名>/`（例：`tmp/S16/`）を作成します。
2. D4Analyzer で出力したい言語を指定し、`translation` を選択します。
3. 行の一覧にフォーカスを合わせ、`Ctrl+A` ですべての行を選択します。
4. 選択した行を右クリックし、`Copy Selected` でクリップボードにコピーします。
5. テキストエディターの新規ファイルに貼り付け、UTF-8 で保存します。
   英語は `tmp/S16/en.tsv`、日本語は `tmp/S16/ja.tsv` としてください。
   貼り付けた内容のタブや改行はそのまま残します。
6. 言語を切り替えて同じ操作を繰り返し、英語・日本語の2ファイルを用意します。

### 2. ツールで CSV に変換し、辞書へ取り込む

次のコマンドで同じフォルダーに CSV を生成します。
dry-run で追加件数・除外・競合を確認し、問題がなければ辞書へ反映します。

```bash
python tools/convert_tsv_to_csv.py tmp/S16
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv --dry-run
# dry-run の確認後に実行
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv
```

以後は `S16` を対象シーズンのフォルダー名に置き換えます。CSV がすでにある場合は
上書きを防ぐためエラーになります。再エクスポート分は別フォルダーに置いて変換するか、
既存 CSV を退避してから再実行してください。入力形式が変わった場合は内容を確認してから対応します。

## convert_tsv_to_csv.py

旧 `check_tsv_columns.py` を置き換えた、Diablo IV の生 TSV エクスポート用の変換ツールです。
`SNO,FileName,Index,KeyHash,Key,Translation` の6列を読み取り、
説明文の改行を復元して全フィールドをダブルクォートで囲む CSV を作ります。
UTF-8（BOM ありも可）を読み取り、入力ファイルは変更しません。

```bash
python tools/convert_tsv_to_csv.py tmp/S15/en.tsv tmp/S15/ja.tsv
# フォルダー直下の TSV をまとめて変換（サブフォルダーは対象外）
python tools/convert_tsv_to_csv.py tmp/S15
```

- 入力と同じ場所に `en.csv` / `ja.csv` を出力します。既存の出力は上書きしません。
- ヘッダー末尾とレコード行末尾のタブを除去します。空の `Translation` は維持します。
- `SNO`・`Index`・`KeyHash` が半角数字で、`FileName`・`Key` が空でない6列の行をレコード開始と判断します。
  その他の通常の文章行・空行は直前の `Translation` に改行付きで連結します。
- レコードの先頭5区切り以降は説明文として扱い、内部のタブと引用符を保持します。
  継続行の末尾タブも保持します。CSV 内の引用符は `""` にエスケープします。
- 不正なヘッダー、データなし、先頭の孤立した文章行、レコードに見える不正行は行番号などを報告して停止します。
  不正行のあるファイルの出力は作成しません。複数ファイル指定時は他のファイルの処理を続けます。
- 入力側の引用符は通常文字です。引用符付き TSV 全般に対応するツールではありません。
  レコード開始条件を満たす説明文や、レコード末尾の意図的なタブは形式上区別できません。
- 終了コード: 成功は0、変換失敗は1、引数不正は2。
- 辞書への反映は別作業です。生成した CSV は既存の `merge_csv_translations.py` で読み込めます。

ツールは `tools/`、入力・出力は `tmp/` に置きます。既存の配布 ZIP 作成処理は
`sources/` のファイルだけを収録するため、これらは配布物に含まれません。

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
`attributes,drop-sources,weapon-tooltip,tooltip-labels,runes,items,affixes,effects,flavors,rare-names,powers,paragon,skill-tags,skills` です。
`effects` はレジェンダリー、ユニーク、ミシック効果の説明文からゲーム内の
装飾タグを除去し、Maxroll が表示する可変数値を正規表現に変換します。
`flavors` はユニーク、ミシック装備のフレーバーテキストを変換します。
`skill-tags` は `SkillTags` のタグ名と注釈本文を変換します。長い注釈ルールは
装備Tooltip内だけで照合されます。
`skills` はクラススキル名に加え、`Power_<クラス名>_*` の基本説明・強化説明を
Maxroll のスキルTooltip向け全文ルールへ変換します。`{payload:...}` などの
可変値と、Maxroll が付加する `x [Damage]` / `[262.5%]` 表示も保持します。
`{if:...}{else}...{/if}` は実際に表示される各分岐のルールへ展開します。
`runes` はルーン名、ルーンワード名、条件・効果・オーバーフロー説明を変換し、
英語・日本語CSV間のIndex差も吸収します。
`tooltip-labels` はアイテムパワー、品質、祖霊・レジェンダリーなどの装備Tooltip
共通ラベルを変換します。
`weapon-tooltip` は秒間ダメージ、命中ごとのダメージ、秒間攻撃回数と速度区分を
数値込みの行単位で変換します。
`drop-sources` はMaxrollのTooltip下部にあるドロップ元を対象に、
`ModifiedLootDescriptions` のボス名とMaxroll固有の別名を登録します。
`paragon` はボード・ノード・グリフ名に加え、`Power_Paragon_*`、
`Power_ParagonGlyph_*`、`ParagonGlyphAffix_*` の効果文と、
パラゴンTooltipのボーナス・要件テンプレート、グリフソケットの
見出し・レベル・分割表示される条件注記を登録します。
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
