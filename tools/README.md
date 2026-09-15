# Diablo IV Text Replacer ツール

このディレクトリには、translations.json を管理するためのPythonツールが含まれています。

## シーズン更新の手順

同じ6列の TSV なら既存ツールで CSV に変換できます。ただし、新しいアイテム系列や
説明文の形式は辞書生成の対象追加が必要な場合があります。
差分調査・取り込み漏れ確認・検証は [シーズン更新手順](season-update.md) を参照してください。
以下は S16 の例です。

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
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv --overwrite-existing --dry-run
# dry-run の確認後に実行
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv --overwrite-existing
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

### 攻略用のシーズン比較（辞書を更新せず確認）

```powershell
python tools/merge_csv_translations.py --en tmp/S15/en.csv --ja tmp/S15/ja.csv --previous-en tmp/S14/en.csv --previous-ja tmp/S14/ja.csv --overwrite-existing --dry-run --report tmp/S15/season-update-report.json
```

- ゲームアイテムのフレーバーテキストも取り込みます。NPC会話・クエスト本文は対象外です。
- シーズン更新では `--overwrite-existing` を指定し、生成できた同一キーの訳を
  最新CSVで更新します。英文が変わった場合は新しい英文に対応するルールを追加します。
  CSVから生成されないサイト専用ルール等は保持します。
  この指定を省略した場合は追加のみで、既存訳の更新にはなりません。
- ルーンワード装備名、ユニークチャーム名、ルーンワード・チャーム・セット・
  Hellfire Torch の効果文、および `Power_S<番号>_Triad[A-C]_Player_*` の
  プレイヤー能力説明にも対応します。ボス能力の説明はこの指定では追加しません。
- 英日で `Index` が違う場合は、残る4項目が両言語で一意な場合だけ対応付けます。
- スキルタグと装備のランダム名断片で同じ英語の訳が異なる場合は、スキルタグを優先します。
  例: `Eagle` はランダム名用の「鷲」ではなく、スキル分類の「イーグル」を採用します。
- `--previous-en` / `--previous-ja` は必ず両方指定します。同じカテゴリ・変換処理で
  両シーズンのルールを生成し、新しいキーと、以前からある未登録キーを分けます。
  件数は重複排除後の正規表現ルール数です。新規アイテム数ではありません。
  既存効果文の英文変更や、CSVの対応付け改善も新しいキーに含まれます。
- レポートの `added_rules` は追加候補、`overwritten_rules` は更新前後の訳とカテゴリ、
  `existing_value_differences` は既存訳との差、`season_comparison` は旧シーズンとの比較です。
  追加・上書き件数を別々に表示します。旧シーズンのみのキーは自動削除しません。
  同じ英文の訳が競合する名前や、対応付け・ルール生成できない行は引き続き除外されます。
- `--dry-run` では辞書は変更せず、`--report` の指定先だけを書き込みます。
  取り込み時は上のコマンドから `--dry-run` を外します。
- ローカルCSVによる候補生成のため、Maxrollの実DOM・実際の掲載範囲への一致は
  別途確認が必要です。

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
`attributes` の `S<番号>_Socketable_*` はソウルストーン系の長文効果として処理します。
`{VALUE2}` と `PowerTag` の数値式が混在していても参照を対応付け、割合・`%[x]`・`%[+]`・
数値範囲を保持します。英日で参照先が異なる効果は除外します。
S15 CSVの `S15_Socketable_Azmodan` は日本語側がAndarielの文になっているため、
確認済みの英日原文が両方一致する場合のみ、英文に基づく補正訳を生成します。
原文が修正・変更された場合はこの補正を適用しません。入力CSV自体は変更しません。
`flavors` は攻略用アイテムのフレーバーテキストを変換します。
ユニーク・ミシック・レジェンダリーに加え、セットチャームやルーンワード装備も含みます。
`Item_S<番号>_SoulSplinter_*` の魂の破片は、正式名を `items`、フレーバーを `flavors`、
基礎ステータス・使用条件を `attributes` として取り込みます。装着説明
`UIToolTips.Socketable` も対象です。基礎ステータスは `4375` / `4,375` / `437.5` の
いずれも一つの数値として保持します。Maxroll独自の短縮ラベルは正式名とは別の表記です。
`skill-tags` は `SkillTags` のタグ名と注釈本文を変換します。長い注釈ルールは
装備Tooltip内だけで照合されます。
`skills` はクラススキル名に加え、`Power_<クラス名>_*` の基本説明・強化説明を
Maxroll のスキルTooltip向け全文ルールへ変換します。`{payload:...}` などの
可変値と、Maxroll が付加する `x [Damage]` / `[262.5%]` 表示も保持します。
`{if:...}{else}...{/if}` は実際に表示される各分岐のルールへ展開します。
`runes` はルーン名、ルーンワード名、条件・効果・オーバーフロー説明を変換し、
英語・日本語CSV間のIndex差も吸収します。
ルーン効果の `{s1}` は数値として保持し、`|4 shadow:shadows;` のような
単複数指定は表示される英語に展開します。Tooltipの全文照合では、汎用
キャプチャの少なさを優先した上で実際の一致長を比較し、数値用正規表現の
長さだけで「3 seconds.」などの短い断片が全文より先に置換されるのを防ぎます。
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

## Tooltipの汎用ルール検証

`node tools/test_content_wildcards.js` で実際の `content.js` の文字列置換処理を検証できます。
数値保持、`%[+]`、繰り返し実行、汎用キャプチャが別の文や翻訳済み日本語を
巻き込まないことを確認します。Node.jsは任意で、拡張の実行には不要です。
DOMの実表示を保証するテストではありません。

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
