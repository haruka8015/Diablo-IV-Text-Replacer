# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Diablo IVのビルド情報サイト（mobalytics.gg、d4builds.gg、maxroll.gg）の英語テキストを日本語に変換するChrome拡張機能です。Manifest V3準拠で、ビルドプロセスや外部依存関係はありません。

現在のバージョン: 0.9.1（2025年7月時点）
翻訳エントリ数: 3,663個

## 開発タスク

### 拡張機能のローカルテスト
1. Chromeで `chrome://extensions/` を開く
2. 右上の「デベロッパーモード」を有効化
3. 「パッケージ化されていない拡張機能を読み込む」をクリックし、`sources`ディレクトリを選択
4. 対象サイト（mobalytics.gg、d4builds.gg、maxroll.gg）でテスト

### 翻訳辞書の更新

新しいシーズンのデータから翻訳を更新する場合：
```bash
# StringListファイルから翻訳を抽出してマージ
python3 tools/convert_stringlist_to_translations.py sources/translations.json \
  --en temp/S10_StringList_en.json \
  --jp temp/S10_StringList_jp.json \
  --merge-existing
```

重要：
- `--en` と `--jp` オプションで英語と日本語のStringListファイルを指定（必須）
- `--merge-existing` で既存の翻訳を保持しながら新規追加
- ファイル名の命名規則は任意（S9、S10などのシーズン番号も含む）

### リリース用zipファイルの作成

Chrome Web Storeへの提出用にzipファイルを作成する場合：
```bash
./tools/create_release_zip.sh
```

このスクリプトは：
- `manifest.json`からバージョンを自動取得
- `temp/Diablo_Translate_{version}.zip`を作成
- Chrome Web Storeが要求する`Diablo_Translate/`ディレクトリ構造で出力

## アーキテクチャ

### コアコンポーネント
- **background.js**: 拡張機能のライフサイクル管理とコンテンツスクリプトの注入
- **content.js**: メイン変換エンジン
  - translations.json読み込み
  - 長さ順ソート済み正規表現パターン生成
  - テキストノードとtitle属性の置換
  - MutationObserverによる動的コンテンツ対応
  - デバウンス処理（mutation: 100ms、初期化: 1000ms）
- **popup.js/html**: ON/OFF切り替えと手動変換のUI

### 実装の重要点
- 単語境界（`\b`）使用で部分一致を防止
- パターンを長さ順にソートして複雑な用語を優先処理（同じ長さは辞書順）
- 50件以上のDOM変更をバッチ処理してパフォーマンス向上
  - 事前コンパイルされた正規表現により5-10倍の高速化を実現
- Chrome sync storageで有効/無効状態を保持
- クォート文字の違いを吸収（`'` と `'` を同一視）

### 翻訳パターン形式
`translations.json`でサポートされる形式：
- 単純な置換: `"Health": "ライフ"`
- 正規表現パターン: `"\\+\\[(\\d+)-(\\d+)\\] Maximum Life": "+[$1-$2] 最大ライフ"`
- プレースホルダーを含む複雑なゲーム固有フォーマット

## 重要な注意事項
- ビルドプロセスなし - JavaScriptファイルを直接編集
- テストフレームワークなし - ローカルで拡張機能を読み込んで手動テスト
- 対象ユーザーは日本のDiablo IVプレイヤー
- JSONで正規表現パターンはバックスラッシュをエスケープ（例: `\\b`）
- 攻略サイトではHTMLタグで文章が分割されるため、長い文章や改行を含む変換は機能しない
- ゲーム内プレースホルダー（`{VALUE}`など）は攻略サイトでは実際の値に置換されるため使えない

## ディレクトリ構造
```
/
├── sources/              # Chrome拡張機能のソースコード
│   ├── manifest.json    # v0.9.1
│   ├── translations.json # 3,663個の変換ルール
│   ├── content.js       # メイン変換処理
│   ├── background.js    # サービスワーカー
│   └── popup.html/js    # ポップアップUI
├── tools/               # 開発ツール
│   ├── convert_stringlist_to_translations.py  # メイン変換ツール
│   └── archive/         # 古いツール（参考用）
├── temp/                # 一時ファイル（.gitignore対象）
└── other_resources/     # プロモーション素材など
```