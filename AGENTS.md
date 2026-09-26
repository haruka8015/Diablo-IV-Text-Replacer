# AGENTS.md

## この文書の位置付け

このリポジトリ全体で作業するエージェント向けの開発ガイド。
もともと Claude Code で開発されており、既存の `CLAUDE.md` の知見を引き継ぎ、現行コードを確認して整理した。
ユーザーへの説明・作業報告は日本語を基本とする。

- `CLAUDE.md` は従来の開発資料として残す。移行を理由に削除したり、コードを一括再構成したりしない。
- `CLAUDE.md` のバージョン・辞書件数、「テストなし」、background によるスクリプト注入、「長文や改行は変換できない」という記述は現状と異なる。
- 現在の仕様は `sources/` の実装、ツールの引数、テストを突き合わせて確認する。古い説明やコードコメントだけを根拠にしない。
- バージョンの正本は `sources/manifest.json`。辞書件数は変動するため固定値を前提にしない。

### バージョン規則（ユーザー指定）

- 形式は `1.<ゲームのシーズン番号>.<公開回数>`。通常の公開回数は 1 から数える。
- 今回のシーズン15開始バージョンは、ユーザーの明示指定により `1.15.0` とする。以後の公開では `1.15.1`、`1.15.2` と進める。
- 一般的なセマンティックバージョニングとして番号を決めない。将来のシーズン開始時も、今回の 0 開始を無条件に一般化せずユーザー指定を確認する。
- バージョン変更時は manifest と `tools/test_extension_state.py` の対応するテスト名・期待値を揃える。

## プロジェクト概要

Diablo IV の攻略・ビルドサイトの英語表記を日本語に置換する Chrome 拡張機能。Manifest V3、素の JavaScript / HTML / JSON で構成される。

- 対象ドメイン：`mobalytics.gg`、`d4builds.gg`、`maxroll.gg`（対象パターンは manifest を参照）。
- 基本機能：専門用語・アイテム・スキル・効果説明などの辞書置換。
- Maxroll の追加機能：Chrome Translator API によるガイド本文の英日翻訳。専門用語とインライン装飾を保護する。
- Translator が使えない場合も辞書置換は動作する。モデルの初回準備は popup のダウンロードボタンから行う。
- npm やバンドラーによるコンパイルは不要。`sources/` をそのまま Chrome に読み込む。配布用 ZIP の作成ツールは存在する。
- Python の変換ツールとテストは標準ライブラリを使用する。

## ファイルと役割

| パス | 役割 |
| --- | --- |
| `sources/manifest.json` | 権限、対応サイト、content script の宣言、バージョン |
| `sources/content.js` | 辞書読み込み、正規表現照合、DOM・title 置換、動的更新監視、Maxroll 本文翻訳 |
| `sources/translations.json` | 英語文字列／正規表現 → 日本語の辞書。手動調整済みの訳を含む |
| `sources/background.js` | 設定初期化、offscreen 文書の作成・解放、翻訳メッセージの中継 |
| `sources/offscreen.html` / `offscreen.js` | Translator の保持、翻訳要求の直列処理、アイドル時の解放 |
| `sources/popup.html` / `popup.js` | 拡張・本文翻訳の切替、モデル準備、手動変換、バージョン表示 |
| `tools/merge_csv_translations.py` | 英日 CSV の対応付け、Web 表示向けルール生成、既存辞書へのマージ |
| `tools/convert_stringlist_to_translations.py` | 従来の StringList JSON からの抽出・マージ |
| `tools/test_extension_state.py` | 拡張の設定・DOM処理などのソース検査と辞書ルールの検証 |
| `tools/test_merge_csv_translations.py` | CSV 取り込み・数値・条件分岐・既存訳保持などの検証 |
| `tools/test_content_wildcards.js` | 実際のJS置換処理で数値保持・全文優先・繰り返し変換を検証 |
| `tools/season-update.md` | 毎シーズンの差分調査・取り込み漏れ確認・検証・配布の手順 |
| `tools/build_extension.py` / `create_release_zip.sh` | 配布用 ZIP 作成 |
| `tools/README.md` | 取り込みカテゴリ・ツールの説明。古い節は実装と照合する |
| `tools/archive/` | 過去の変換ツール。通常の作業では現行ツールを使う |
| `other_resources/` | アイコン原本・プロモーション素材 |
| `temp/` / `tmp/` | 入力データ・調査資料・配布 ZIP などの一時領域。Git 管理対象外 |

## 実装上の維持事項

### 設定とライフサイクル

- `chrome.storage.sync` の `enabled` と `guideTranslationEnabled` を使用する。インストール時の初期化は未設定値だけに適用し、更新時にユーザー設定を上書きしない。
- content script は manifest から読み込む。background から再注入して二重動作させない。
- 設定変更は各対象タブの content script が検知してページを再読み込みする。OFF 時に原文へ戻す仕組みを維持する。
- 翻訳通信は content → background → offscreen。`target` と `action` の対応を変更時に確認する。
- offscreen の翻訳キューは直列。Translator のアイドル解放と機能 OFF 時の文書解放を維持する。

### 辞書・正規表現

- キーは正規表現として扱われる。JSON のバックスラッシュと、訳文中の `$1` などのキャプチャ参照を正しく対応させる。
- 実行時は汎用キャプチャ `(.*?)` が少ない規則を優先する。通常ルールはその後にキーの長さ、Tooltip全文候補は実際の一致長を優先する。数値用正規表現の長さと表示文の長さを混同しない。
- 単語境界はパターンの先頭・末尾に応じて付ける。句読点で終わる文やルーン名の連結規則を壊さない。
- ASCII／曲線アポストロフィの両方を扱う。
- 長文ルールはゲーム Tooltip 内に適用範囲を限定する。一般のガイド本文への過剰適用を避ける。
- `__D4T_DROP_SOURCE__:` で始まるキーはドロップ元用の特別な辞書。通常の正規表現キーとして扱わない。
- `__D4T_SPLINTER_LABEL__:` はMaxrollの装備欄にある破片アイコン下の略称専用。通常の正規表現キーから除外し、本文や通常ルーンの同名単語には適用しない。
- ゲーム内の `{VALUE}` や `{payload:...}` はサイト上では数値等になる。生のゲーム文ではなく表示される文字列に一致する規則を生成する。
- 数値の範囲、桁区切り、割合、`[x]` / `[+]`、ダメージ注記、条件分岐、単複数指定、日本語での値の順序を確認する。`{s1}` と `|4shadow:shadows;` などが共存する場合も実際の表示文で照合する。

### DOM と性能

- Maxroll では文章が複数のテキストノードや `span`、リンク、`br` に分かれる。未翻訳の原因が辞書不足か、DOM の分割・適用範囲かを切り分ける。
- Tooltip、リンク、文字色、可変値の要素を保持する。親要素の `innerHTML`／`textContent` 一括置換で装飾やイベントを破壊しない。
- Tooltipの全文訳と装飾語の通常訳が異なる場合は、原文の語句に完全一致する辞書候補から全文中の対応先を確認する。名前ごとの例外を安易に追加せず、複数候補で曖昧な場合は装飾位置を推測しない。
- Maxroll ガイド本文は専用経路で処理する。保護トークンの欠落・重複・破損を検証し、不正な翻訳結果で DOM を再構成しない。
- 辞書による用語変換を機械翻訳の完了待ちにしない。
- React のテキスト書き換え、Tooltip の後挿入、非表示タブの切替にも対応する。
- MutationObserver の属性監視を不用意に拡大しない。特に `class` の常時監視や毎回の全ページ走査を避ける。
- パターン索引、正規表現の遅延生成と上限制キャッシュ、WeakMap、表示領域に応じた本文翻訳を維持する。
- パラゴン盤面の高頻度 DOM 更新を本文翻訳から除外する一方、パラゴン章の説明文は翻訳対象に保つ。
- Maxroll の不具合調査ではホバー後の実 DOM と原文を確認する。スクリーンショットだけから要素構造を推測しない。利用可能なら `inspect-maxroll-dom` スキルに従う。

## 開発・検証手順

以下のコマンドはリポジトリルートで実行する。`python` は環境に応じて `python3` や `py` に読み替える。

`python` が PATH にない場合も、未導入と判断する前に `.venv/`、`venv/`、`tmp/uv-cache/` 内の `pyvenv.cfg` と Python 実行ファイル、uv 管理の Python を確認する。
この Windows 環境では `tmp/uv-cache/archive-v0/` 配下の仮想環境と、その参照先の Python 3.10.20 が実行可能だった。キャッシュ内のディレクトリ名は固定しない。
確認済みの本体を直接使う例（他の環境ではパスを確認する）：

```powershell
& 'C:/Users/bcd80/AppData/Roaming/uv/python/cpython-3.10-windows-x86_64-none/python.exe' -m unittest discover -s tools -p 'test_*.py'
```

### 自動検証

```powershell
python -m unittest discover -s tools -p "test_*.py"
```

既存テストは実ブラウザの動作を保証しない。特に `test_extension_state.py` にはソース文字列の検査が多いため、DOM 処理やライフサイクルの変更では手動確認も行う。
Node.js が利用できる場合は、変更した JavaScript の構文を `node --check sources/content.js` などで確認できる。
辞書や置換処理を変更した場合は `node tools/test_content_wildcards.js` で実装を通した検証も行う。Pythonの正規表現一致だけでは、JSの索引・優先順位・繰り返し適用の問題は確認できない。Node.jsが使えない場合は実施した代替検証と未確認範囲を明記する。

バージョン検証の期待値は上記の公開規則と manifest に合わせる。テストに合わせるためだけに製品バージョンを下げない。

### Chrome での確認

- ストア版と開発版が同じページで同時に有効でないことを確認する。旧版が先に部分置換すると、新版の全文ルールが一致しなくなる。再読み込み後も旧訳が残る場合は、拡張ID・読み込み先・重複登録を切り分ける。
- Maxrollの個別モディファイアリンクと、Skillsのビルド数値入りモディファイア一覧は別々に検証する。置換関数の直接呼び出しに加え、MutationObserverによる後挿入Tooltipの自動変換も確認する。

1. `chrome://extensions/` でデベロッパーモードを有効にし、`sources/` を「パッケージ化されていない拡張機能」として読み込む。
2. 編集後は拡張を再読み込みし、対象ページも再読み込みする。
3. 変更対象に応じて、初期表示、遅延表示、ホバー Tooltip、タブ切替、手動変換を確認する。
4. ON/OFF と設定保持、複数の対象タブへの反映、原文への復帰を確認する。
5. 本文翻訳の変更では、モデル利用可／不可、本文翻訳 OFF、リンク・色・スキル要素の保持も確認する。

テストを実行できなかった場合は、その理由と未確認範囲を報告する。

## 辞書更新

入力ファイルは別途用意する。下記のパスは例であり、リポジトリに含まれる前提にしない。

### 毎シーズン維持する方針

- 詳細は [シーズン更新手順](tools/season-update.md) を参照する。
- 対象は攻略用の名前・分類・効果・条件・説明と、アイテムのフレーバーテキスト。NPC会話やクエスト・ストーリー本文は対象外。話者名や引用文があることだけでアイテムのフレーバーを除外しない。
- 新しいシーズン要素は名前、効果、フレーバー、使用条件が別のCSV行・カテゴリに分かれる。効果の取り込み成功だけで全体が対応済みと判断しない。新しい `FileName` 系列や `Key` が既定カテゴリに入るか確認する。
- 最新CSVの既存訳まで反映する更新には `--overwrite-existing` が必要。これも選択・生成できたルールのマージであり、CSV全件の完全同期ではない。
- 旧CSVにだけあるルールは削除可能と断定しない。過去装備・旧ガイド・サイト独自表記で使う場合がある。現時点で旧辞書の削除は保留するというユーザー方針を維持し、シーズン更新に自動削除を混ぜない。
- CSV由来の不具合は生成スクリプトと回帰テストを修正する。原文の誤りへの補正は対象行と確認済みの英日原文に限定し、将来の原文修正を上書きしない。

### CSV からの更新

```powershell
python tools/merge_csv_translations.py --list-categories
python tools/merge_csv_translations.py --en tmp/S14/en.csv --ja tmp/S14/ja.csv --dry-run
python tools/merge_csv_translations.py --en tmp/S14/en.csv --ja tmp/S14/ja.csv
```

- 入力列は `SNO,FileName,Index,KeyHash,Key,Translation`。複合キーで対応付け、一意な対応では言語間の Index 差も補完する。
- まず dry-run で件数・除外・競合を確認し、更新後は JSON の差分と関連テストを確認する。
- 原則として既存訳を優先する。既存訳を置換する意図がある場合だけ `--overwrite-existing` を使う。
- 対象を絞るには `--categories items,affixes,paragon` などを指定する。詳細は `tools/README.md` と `--help` を参照する。

### StringList JSON からの更新

```powershell
python tools/convert_stringlist_to_translations.py sources/translations.json --en temp/StringList_en.json --jp temp/StringList_jp.json --merge-existing
```

`--en` と `--jp` は必須。`--merge-existing` は既存の `sources/translations.json` を優先してマージする。CSV ツールとの引数・マージ元の違いに注意する。

## 配布用 ZIP

```powershell
python tools/build_extension.py
```

manifest のバージョンから `temp/Diablo_Translate_{version}.zip` を生成し、ZIP 内では `Diablo_Translate/` 配下に `sources/` のファイルを配置する。これは現行ツールの出力形式であり、ストアが要求する形式との断定はしない。
Bash と `zip` が使える環境では `bash tools/create_release_zip.sh` も存在する。
`sources/` 内のファイルが配布物に含まれるため、調査資料や入力 CSV を置かない。ZIP 作成とストアへの公開は別作業として扱う。

## 変更時の基本方針

- 既存の素の JavaScript と Python ツールの構成に合わせ、依頼と無関係な依存追加・全面リファクタリングを避ける。
- ファイルは UTF-8 で扱う。Windows PowerShell で日本語を読む際は `Get-Content -Encoding UTF8` を使い、表示上の文字化けをファイル破損と取り違えない。
- 翻訳辞書の大量変更は取り込み理由と差分を確認し、手動訳を不用意に失わない。
- 仕様・コマンドを変更したら関連文書も確認する。`CLAUDE.md` と本書に異なる現行手順を増やさない。
- 完了報告には変更内容、実施した検証、既存の失敗や未確認事項を簡潔に記載する。
