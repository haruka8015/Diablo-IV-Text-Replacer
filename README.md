# Diablo4 攻略サイト日本語化ツール

Diablo IVの英語攻略サイトを、日本語のゲーム内名称で読みやすくするChrome拡張機能です。
アイテム・スキル・パラゴンなどの名称や効果説明を辞書で変換し、Maxrollでは攻略記事の解説本文も英語から日本語へ翻訳します。

**現在はMaxrollを中心に調整・改善しています。** mobalyticsとd4buildsでも辞書による用語変換を利用できます。

[Chromeウェブストアからインストール](https://chromewebstore.google.com/detail/diablo-iv-text-replacer/eglplmdfdpmjenfngageophapmdcngcl)

## 対応サイトと機能

| サイト | 辞書による用語・効果説明の変換 | 解説本文の英日翻訳 |
| --- | --- | --- |
| Maxroll | 対応。現在の主な調整対象 | ビルドガイド、ホラドリムキューブなどのResources記事 |
| mobalytics | 対応 | 対象外 |
| d4builds | 対応 | 対象外 |

### ゲーム用語・ポップアップの変換

- アイテム、スキル、スキルのモディファイア、パラゴン、グリフなどの名称・効果説明を日本語化します。
- ルーン、宝石、魂の破片、同調プリズム、作成素材なども辞書に収録しています。
- アイテムのフレーバーテキストも変換対象です。
- Maxrollのホバー表示や動的に追加される表示に対応し、数値・リンク・文字色・下線などを保持するよう調整しています。

辞書にはゲームの英日データとサイト表示に合わせた補正を使用しています。
サイト独自の表記、未登録の名称、アップデートによる変更などで、英語が残る場合があります。

### Maxrollの解説本文を翻訳

Chrome内蔵のTranslator APIを使い、ビルドの解説や手順、対応記事の表・箇条書きを翻訳します。
ゲーム用語の辞書を優先し、スキル・アイテムへのリンクや装飾を保持します。
パラゴン盤面など、頻繁に更新される操作領域は本文翻訳から除外しています。

本文翻訳には**デスクトップ版Chrome 138以降**と英日翻訳モデルが必要です。
利用可否は拡張機能のメニューで確認できます。Chrome側の対応条件は
[Translator APIの公式説明](https://developer.chrome.com/docs/ai/translator-api)を参照してください。

モデルが未導入、または本文翻訳を利用できない環境でも、辞書による変換は動作します。
本文は機械翻訳のため、意味が不自然な場合は原文も確認してください。

## 使い方

1. [Chromeウェブストア](https://chromewebstore.google.com/detail/diablo-iv-text-replacer/eglplmdfdpmjenfngageophapmdcngcl)から拡張機能をインストールします。
2. 対応サイトを開きます。既に開いていたタブは再読み込みしてください。
3. 拡張機能のメニューで「変換機能」がONになっていることを確認します。
4. Maxrollの本文も翻訳する場合は「英→日 翻訳モデルをダウンロード」で初回の準備を行い、「Maxroll解説文を翻訳」をONにします。準備完了後、対象ページを再読み込みしてください。

| メニュー | 動作 |
| --- | --- |
| 変換機能 | 拡張全体のON/OFF。OFFにするとページを再読み込みして原文に戻します |
| Maxroll解説文を翻訳 | 本文翻訳のON/OFF。OFFでも辞書による変換は利用できます |
| 英→日 翻訳モデルをダウンロード | 本文翻訳に使うモデルの初回準備 |
| 手動で変換 | 現在のタブで変換処理を再実行 |

ON/OFFの設定は保存されます。設定変更時は、開いている対応サイトのタブが再読み込みされます。
本文翻訳は表示領域に応じて処理するため、スクロール後に翻訳が進む場合があります。

## 変換されない・表示がおかしいとき

- 拡張機能がONか確認し、対象ページを再読み込みしてください。
- 本文だけ英語のままなら、「Maxroll解説文を翻訳」と翻訳モデルの状態を確認してください。
- 開発版を使用する場合は、**ストア版と開発版を同時にONにしないでください。** 先に旧版が部分変換すると、新版の全文ルールが一致しなくなる場合があります。
- 開発版のファイルを更新した後は、`chrome://extensions/` で拡張機能を再読み込みし、対象ページも再読み込みしてください。

不具合を報告する際は、ページURL、原文または崩れた訳、スクリーンショット、拡張のバージョンを添えてください。
Maxrollのポップアップなら、選択中のビルドと、どのリンク・アイコンから開いたかも分かると再現しやすくなります。

## 開発版の導入

1. このリポジトリを取得します。
2. Chromeで `chrome://extensions/` を開き、デベロッパーモードをONにします。
3. 「パッケージ化されていない拡張機能を読み込む」から **`sources/` フォルダー**を選択します。
4. ストア版をOFFにし、対象ページを再読み込みします。

拡張本体は素のJavaScript・HTML・JSONで構成されています。npmやバンドラーによるコンパイルは不要です。
開発版のバージョンは [sources/manifest.json](sources/manifest.json) を参照してください。ストア公開版と異なる場合があります。

## 開発・辞書更新

| ファイル・資料 | 内容 |
| --- | --- |
| [sources/content.js](sources/content.js) | 辞書置換、動的表示への対応、Maxroll本文翻訳 |
| [sources/translations.json](sources/translations.json) | 変換辞書 |
| [tools/merge_csv_translations.py](tools/merge_csv_translations.py) | 英日CSVからの辞書生成・マージ |
| [シーズン更新手順](tools/season-update.md) | 新シーズンの差分調査、取り込み、検証 |
| [ツールの説明](tools/README.md) | 辞書生成ツールの引数・カテゴリ・使い方 |
| [開発ガイド](AGENTS.md) | 実装上の維持事項、検証・配布手順 |

辞書更新用のCSVは別途用意します。まずdry-runで差分を確認してください。
取り込み対象は攻略に関わる名称・効果説明・アイテムのフレーバーです。NPC会話やストーリー本文は対象外です。

### テスト

リポジトリのルートで実行します。

```powershell
python -m unittest discover -s tools -p "test_*.py"
node tools/test_content_wildcards.js
```

DOMを使うブラウザテストは、次のコマンドでローカルサーバーを起動し、
`http://127.0.0.1:8765/tools/test_content_tooltip_dom.html` をChromeで開きます。

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

自動テストに加え、変更箇所の実ページ・ホバー表示・ON/OFFも確認してください。
Pythonの実行環境を見つけられない場合は [開発ガイド](AGENTS.md) を参照してください。

### 配布用ZIPの作成

VS Codeでは **Ctrl+Shift+B**、または「ターミナル → タスクの実行 → 拡張機能: 配布用ZIPを作成」を選びます。
Windows用タスクは現在の開発環境のuv管理Pythonを指定しています。別環境では
[.vscode/tasks.json](.vscode/tasks.json) の `windows.command` を変更してください。

コマンドから作成する場合：

```powershell
python tools/build_extension.py
```

manifestのバージョンに応じて `temp/Diablo_Translate_<version>.zip` を生成します。
ZIP内は `Diablo_Translate/` 配下に拡張ファイルを配置します。ストアへのアップロード・公開は別途行います。

## ライセンス

[MIT License](LICENSE)
