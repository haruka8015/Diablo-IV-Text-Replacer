# CSVテスト資料

`s15_socketables_en.csv` / `s15_socketables_ja.csv` は、提供されたS15 CSVの
`AttributeDescriptions` / `S15_Socketable_*` 8行を抜き出したものです。
数値参照・タグ・英日で異なる数値の出現順を含め、原文を維持しています。

Azmodanの日本語行にはAndarielの文と数値参照が入っています。
誤った効果文を生成しないことの回帰テストとして、この不整合も保持します。

`s15_soul_splinters_en.csv` / `s15_soul_splinters_ja.csv` は魂の破片35種類の
名前・基礎ステータス・フレーバー・使用条件、および共通の装着説明を抜き出したものです。
原文のIndex差、複数行の引用と話者表記も保持しています。

`maxroll_skarn_tooltip.html` は2026-09-26に
[Blazing Scream Warlockガイド](https://maxroll.gg/d4/build-guides/blazing-scream-warlock-guide)
の `[data-d4-id="S15_SoulSplinter_Skarn_04"]` を実際にホバーして取得した
`.d4t-GameTooltip.d4t-tip-legendary` の効果リスト部分です。
色付き親spanの外にある句点、入れ子の下線付き用語、1・25%・25の順序を保持し、
日本語語順への変更と既存要素・イベントの保持をDOMテストで検証します。

`s15_seal_en.csv` / `s15_seal_ja.csv` はS15 CSVから抽出した、刻印の追加スロット、
セット条件軽減、悪魔形態中のダメージ減少、セット名、スロット解放表示の行です。
`maxroll_seal_tooltip.html` は同じガイドの装備欄にあるダイヤモンドの精神の刻印を
2026-09-26に実際にホバーして取得しました。本文中のアイテム名リンクの基本表示とは
異なり、装備欄の表示には追加効果と補足数値範囲が含まれます。
取得時の対象は `[class*="equipment_slot-20__"]`、Tooltipは
`.d4t-GameTooltip.d4t-tip-mythic` でした。装備アイコンの画像要素だけを除いています。

`s15_resource_regeneration_en.csv` / `s15_resource_regeneration_ja.csv` はS15 CSVの
リソース回復量2種類と `UIToolTips.Resource_Type_*` の行を抽出しています。
リソース名を汎用キャプチャに残さず、Wrath等の具体名を埋め込んだ規則と用語訳を
生成する検証に使用します。同じ英文に複数の訳がある行も原文のまま保持しています。
