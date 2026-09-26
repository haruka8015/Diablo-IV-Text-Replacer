# CSVテスト資料

`hellguard_csv_markup.html` は S15 CSV の `Power_Warlock_ClassMechanic_Vanguard_A`
の desc 第2段落の色・下線タグをspanに展開した再現用フィクスチャ（実DOMの取得物ではない）。
数値は報告画像の6・35%を使用し、既存の実測スキルTooltipと同じ形式でダメージ注記を付けた。
色付きAbodianの全文訳への対応付け、文の並べ替え、数値・下線・注記の保持を検証する。

`s15_cube_material_names_en.csv` / `s15_cube_material_names_ja.csv` は S15 CSV の
`Item_X2_HoradricCube_CraftingMaterial_*` と `Item_X2_Talisman_CraftingMaterial_*`
の Name 全9行。原初の塵8種類と浸染したホラドリムの樹脂について、
アイコン指定除去・正式名・レシピ表示の数量保持を検証する。

`s15_new_runes_en.csv` / `s15_new_runes_ja.csv` はS15 CSVの
`Item_S15_Rune_*` 12種類の40行と、供物・連携・クールダウンの共通UI5行、
誤爆確認用の装備名断片「The」1行です。名前だけでなく効果・連結名を検証します。
`maxroll_cube_article.html` は2026-09-26に
[Horadric Cube記事](https://maxroll.gg/d4/resources/horadric-cube)から取得した抜粋です。
通常段落、markによる色分け、見出し、入れ子リスト、表、Tirのゲームリンクを保持しています。
Resourcesパスでのみ翻訳対象になること、本文が翻訳サービスへ渡ること、
子リストの翻訳で親を再翻訳しないこと、翻訳OFF時の辞書処理を検証します。
翻訳サービスの返答はテスト用の代替応答です。

`maxroll_guide_glyph.html` は同じWarlockガイドの本文で取得した
`.d4-glyph[data-d4-id="Rare_133_Intelligence_Side"]`（Superiority）です。
アイコンの後にあるZWJ（U+200D）と`.d4-color-legendary`内の名前を保持しています。
名前の実測色は`rgb(255, 128, 0)`、親本文は`rgb(232, 232, 232)`でした。
本文の辞書変換と機械翻訳経路の両方で、訳語を元の色付きTextノードに残し、
アイコン・イベントを保持することを検証します。空白・別の不可視区切り文字は派生ケースです。

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
`maxroll_hesha_link_tooltip.html` / `maxroll_hesha_equipment_tooltip.html` は
2026-09-26に https://maxroll.gg/d4/build-guides/touch-of-death-spiritborn-guide
で実際にホバーして取得した「Hesha e Kesungi」のTooltipです。
本文リンクは `[data-d4-id="Gloves_Unique_Spiritborn_100"]`、装備欄は
`[class*="equipment_slot-13__"]` を対象にしています。
それぞれ `.d4t-GameTooltip.d4t-tip-unique` と `.d4t-GameTooltip.d4t-tip-mythic` です。
「The Protector」の通常訳「庇護者」と効果文中の「〈守護者〉」の差による全文置換の失敗、
神秘装備の色、数値・補足範囲・倍率記号の保持、後挿入時の自動変換を検証します。

# 同調プリズムの名前

`s15_gem_names_en.csv` / `s15_gem_names_ja.csv` は S15 CSV の `Item_Gem_*`
の Name 全64行（重複を除く57名称）。7種類の宝石の全8品質と最高天の眼を
検証する。Royal などの単語単位の既存訳より、宝石名全体の公式訳を優先する。

`s15_prism_tooltips_en.csv` / `s15_prism_tooltips_ja.csv` は同じ8種類の
Name・Description・Flavorの全24行。用途・使用条件・入手元・フレーバーの
取り込みと、説明文のアイコン指定除去を検証する。

`s15_prism_names_en.csv` / `s15_prism_names_ja.csv` は S15 CSV の
`Item_X2_HoradricCube_TuningStone_1` ～ `_8` の Name 行をそのまま抽出したもの。
カテゴリの取り込み漏れ、名前中のアイコン指定の除去、単数・複数形を検証する。
Maxroll の Horadric Cube 記事では `data-d4-id="2533710"` の表示名が
`Aggressive Tuning Prism` であることを取得済み記事DOMで確認した。
