# Diablo-IV-Text-Replacer
A Chrome extension that translates specific English terms on Diablo IV build sites into Japanese.

## これは何だ
Diablo IVのビルド情報サイト(mobalytics,d4builds,maxroll)を一部日本語名で表示するChrome拡張です。

英語と日本語のアイテム名・スキル名称を機械的に日本語に置換します。
また、メニューから簡単に機能をOFFにして元の言語に戻すことも可能です。

現状は主にmobalyticsサイト向けに調整しています。

Maxrollのビルドガイドでは、Chrome Translator APIを使って解説本文を
英語から日本語へ翻訳できます。既存のDiablo IV専門用語辞書を優先し、
スキル・アイテム・リンク・文字色などのインライン装飾を維持します。

解説文翻訳にはデスクトップ版Chrome 138以降が必要です。拡張機能メニューの
「英→日 翻訳モデルをダウンロード」から初回モデルを準備してください。
翻訳機能はデフォルトでONになり、設定はChrome Syncへ保存されます。
モデルが未導入または利用できない場合は、従来の専門用語変換だけを行います。

大半のソースコードはChatGPT(4o)に生成してもらっています。中身については１割くらいしか把握していません。
辞書登録だけがんばりました。

## 使い方 How to use.
使いたいだけの方は、公開済みのChrome拡張をインストールして上記対応サイトに訪れてください

[Chromeウェブストア](https://chromewebstore.google.com/detail/diablo-iv-text-replacer/eglplmdfdpmjenfngageophapmdcngcl)
