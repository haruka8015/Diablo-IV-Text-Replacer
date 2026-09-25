# CSVテスト資料

`maxroll_abodian_tooltip.html`、`maxroll_destruction_demon_tooltip.html`、
`maxroll_skull_splitter_tooltip.html` は2026-09-26に
[Warlockガイド](https://maxroll.gg/d4/build-guides/blazing-scream-warlock-guide)
を実際にホバーして取得したスキルTooltipです。対象はそれぞれ
`[data-d4-id="Warlock_Command_Vanguard_Demon"]`、
`[data-d4-id="Warlock_ArchDemon"][data-d4-index="6"]`、
`[data-d4-id="Warlock_BurningSkull:4"]` です。
Activeの見出しspanの外にあるコロン、同値の割合とHP注記の配置、既存要素・
イベントと繰り返し変換を検証します。Destruction Demonでは実DOMの開き括弧と
数値が別々の隣接Textノードだったため、HTML読込で結合されるノードをテストで
再分割します。コロンを見出し内に移したケースと、実ダメージ値・倍率注記を
表示するケースは比較用の派生ケースです。

`maxroll_planner_meta_tooltip.html`、`maxroll_planner_sigil_tooltip.html`、
`maxroll_planner_molten_tooltip.html` は同日・同ガイドのSkillsをList表示に切り替え、
Metamorphosis、Sigil of Subversion、Molten Bombのスキルアイコンを実際にホバーして
取得した、ビルド数値入りのモディファイア一覧です。対象は
`[class*="list_Skill__icon"][style*="333689995"]`、同`2639026498`、同`959487912`。
このアイコンにはdata-d4-id/data-d4-modsがありませんでした。
`runContentPlannerTooltipDomTests` は実装のMutationObserverを起動した後に
Tooltipを追加し、自動変換、複合タグの空白差、名前欄と効果文の訳語差、数値注記を検証します。
刻印も同じ自動変換経路で再検証します。

`maxroll_planner_prison_tooltip.html` は同じ手順で取得したDark Prisonの
ビルド数値入りTooltipです。対象は
`[class*="list_Skill__icon"][style*="2358501978"]`。
下線付きのFortifiesをFortifyの訳「強化」に対応付け、1%と(597)を保持して
日本語の語順に移し替える自動変換と、下線・イベントの保持を検証します。

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
