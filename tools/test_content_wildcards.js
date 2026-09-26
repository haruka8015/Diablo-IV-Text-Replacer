// Run in a JS engine after exposing the unmodified content.js functions as api.
// This tests text replacement, not a synthetic approximation of Maxroll's DOM.
function runContentWildcardTests(api) {
  const equal = (actual, expected, label) => {
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(label + ': ' + JSON.stringify({ actual, expected }));
    }
  };
  equal(api.getWildcardCaptureIndexes(String.raw`(?:x)([0-9]+)\s*(.*?)`), [2], 'capture indexes');
  equal(api.getWildcardCaptureIndexes(String.raw`\(x\)[()](.*?)`), [1], 'escaped groups and classes');
  equal(api.getWildcardCaptureIndexes(String.raw`(?<value>x)(?<=x)(.*?)`), [2], 'named group and lookbehind');
  const pattern = /([0-9]+(?:,[0-9]{3})*)\s*(.*?)\s*Maximum Life/gi;
  equal(api.hasUnsafeWildcardMatch('4,375, You gain 50% Maximum Life', pattern, [2]), true, 'sentence boundary');
  equal(api.hasUnsafeWildcardMatch('50 翻訳済み Maximum Life', pattern, [2]), true, 'translated capture');
  equal(api.hasUnsafeWildcardMatch('50 Base Maximum Life', pattern, [2]), false, 'ordinary attribute');
  equal(api.hasUnsafeWildcardMatch('4,375 Maximum Life', /(.*?) Maximum Life/gi, [1]), false, 'thousands separator');
  equal(api.hasUnsafeWildcardMatch('50% Maximum Life, but your resource is reduced.', /(.*?) Maximum Life/gi, [1]), false, 'punctuation outside capture');
  equal(api.dynamicValue.test('50%[+]'), true, 'additive marker');
  equal(api.dynamicValue.test('50%[x]'), true, 'multiplicative marker');
  const raw = '+4,375 Lightning Resistance, You gain 50%[+] Maximum Life, but your Maximum Primary Resource is reduced by 30%.';
  const expected = '電撃耐性+4,375, ライフ最大値が50%[+]増加するが、プライマリリソース最大値が30%減少する。';
  let text = api.applyRegexTransformations(raw, [], null, {}, true);
  equal(text, expected, 'reported text');
  for (let pass = 0; pass < 3; pass++) {
    text = api.applyRegexTransformations(text, [], null, {}, true);
    equal(text, expected, 'repeated pass ' + pass);
  }
  const itemLabelCases = [
    ...Object.entries({Raw: '未加工の', Coarse: '荒い', Refined: '精製された', Volatile: '不安定な',
      Pure: '純粋な', Enhanced: '強化された', Attuned: '調和の取れた', Resonant: '共鳴する'}).map(
      ([prefix, ja]) => ['25x ' + prefix + ' Primordial Dust', '25x ' + ja + '原初の塵']),
    ['50x Infused Horadric Resin', '50x 浸染したホラドリムの樹脂'],
    ...Object.entries({Amethyst: 'アメジスト', Diamond: 'ダイヤモンド', Emerald: 'エメラルド',
      Ruby: 'ルビー', Sapphire: 'サファイア', Skull: '頭蓋骨', Topaz: 'トパーズ'}).flatMap(([gem, ja]) =>
      Object.entries({'': '', 'Crude ': '粗末な', 'Chipped ': '欠けた', 'Flawless ': '傷ひとつない',
        'Royal ': '王族の', 'Grand ': '豪奢な', 'Horadric ': 'ホラドリムの',
        'Flawless Horadric ': '傷ひとつないホラドリムの'}).map(([prefix, translated]) =>
        [prefix + gem, translated + ja])),
    ['The Empyrean Eye', '最高天の眼'],
    ['Used to target Offensive affixes during Transmutations in the Horadric Cube.', 'ホラドリムのキューブで使用することで、攻撃特性の変成が可能になる。'],
    ['Collected from:', '入手元:'],
    ['Cube Spoils in War Plans', '作戦計画のキューブの戦利品'],
    ['Cache Rewards from The Tree of Whispers', '囁きの木の箱の報酬'],
    ['Undercity of Kurast', 'クラスト地下都市'],
    ['"The materials of creation exist in abundance, in every particle of our world. Shaping them is a matter of will alone. Ours versus that of creation." -Zoltun Kulle', '「創造の素材は、この世界のあらゆる粒子の中に豊富に存在している。それをどう形成するかは、意志のみによって決定される。いわば我々の意志と創造の意志とのせめぎ合いなのだ」―ゾルタン・クーレ'],
    ['Aggressive Tuning Prism', '攻撃的な同調プリズム'],
    ['Protector’s Tuning Prisms', '守護者の同調プリズム'],
    ['Resourceful Tuning Prism', '豊穣な同調プリズム'],
    ['Pragmatic Tuning Prism', '実用的な同調プリズム'],
    ['Chromatic Tuning Prism', '色彩豊かな同調プリズム'],
    ["Adept's Tuning Prism", '熟達者の同調プリズム'],
    ['Entropic Tuning Prism', '無秩序な同調プリズム'],
    ['Kullean Tuning Prism', 'クーレの同調プリズム'],
    ['Tuning Prisms', '同調プリズム'],
    ['The', 'The'],
    ['Requires: 300 Offering', '必要: 300の供物'],
    ['Gain: 600 Offering', '獲得: 600の供物'],
    ['Cooldown: 1 second', 'クールダウン: 1秒'],
    ['Link with a Rune of Ritual in equipment with two Sockets to form a Runeword. Only two Runewords may be active at a time.', 'ソケットを2つ持つ装備上で儀式のルーンと連携してルーンワードを作成する。ルーンワードは一度に2つしか発動できない。'],
    ['Tir Eth Ith Ral', 'ティア エス イス ラル'],
    ['EthTir', 'エスティア'],
    ['Gain +2 Primary Resource on Kill for 8 seconds, up to +8.', '8秒間、キル時のプライマリリソース回復量が+2増加する。最大+8。'],
    ['Gain +5 Weapon Damage for 5 seconds, up to +125.', '5秒間、武器ダメージが+5上昇する。最大+125。'],
    ['Gain 250% Gold Find for 7 seconds.', '7秒間、ゴールド発見量が250%上昇する。'],
    ['Paragon', 'パラゴン'],
    ['PARAGON', 'パラゴン'],
    ['+8 Wrath Regeneration [8]', '憤怒回復量+8[8]'],
    ['Wrath Regeneration', '憤怒回復量'],
    ['+8.5 Wrath Regeneration', '憤怒回復量+8.5'],
    ['10% Wrath Regeneration per Second', '毎秒の憤怒回復量10%'],
    ['Abyssal Splinter of the Mother', '母の破片（深淵）'],
    ['ABYSSAL SPLINTER OF SIN', '罪悪の破片（深淵）'],
    ['Abyssal Splinter of Pain', '苦痛の破片（深淵）'],
    ['Can be inserted into equipment with sockets.', 'ソケット付きの装備にはめ込み可能。'],
    ['+4375 Physical Resistance', '物理耐性+4375'],
    ['+4,375 Physical Resistance', '物理耐性+4,375'],
    ['+437.5 Physical Resistance', '物理耐性+437.5'],
    ['"Break the chains, and discover who you were meant to be. Break the chains, and be beautiful in Sin."\n- Lilith, The Blessed Mother',
     '「鎖を断ち切り、お前の真の姿を見つけよ。鎖を断ち切り、罪の中で美しくあれ」\n―祝福されし母リリス']
  ];
  for (const [rawText, expectedText] of itemLabelCases) {
    let translated = api.applyRegexTransformations(rawText, [], null, {}, true);
    equal(translated, expectedText, 'item label: ' + rawText);
    translated = api.applyRegexTransformations(translated, [], null, {}, true);
    equal(translated, expectedText, 'item label repeated: ' + rawText);
  }
  const runeCases = [
    ['Cast 5 Skills then become exhausted for 3 seconds. (1 time)',
     'スキルを5回使用した後3秒間、消耗状態になる。 （これを1回行う）'],
    ["Gain 2 shadows, from the Rogue's Dark Shroud Skill, reducing damage taken per shadow.",
     'ローグのスキル〈ダークシュラウド〉の影を2個獲得し、影1つごとに受けるダメージを減少させる。'],
    ["Gain 1 shadow, from the Rogue’s Dark Shroud Skill, reducing damage taken per shadow.",
     'ローグのスキル〈ダークシュラウド〉の影を1個獲得し、影1つごとに受けるダメージを減少させる。'],
    ['(Overflow: Gain Multiple Shadows)', '(オーバーフロー: 複数の影を獲得)']
  ];
  runeCases.push([runeCases.map(pair => pair[0]).join('\n'), runeCases.map(pair => pair[1]).join('\n')]);
  for (const [rawText, expectedText] of runeCases) {
    let translated = api.applyRegexTransformations(rawText, [], null, {}, true);
    equal(translated, expectedText, 'rune: ' + rawText);
    translated = api.applyRegexTransformations(translated, [], null, {}, true);
    equal(translated, expectedText, 'rune repeated: ' + rawText);
  }
  return { passed: 14 + (itemLabelCases.length + runeCases.length) * 2, translated: text };
}

// Optional standalone runner: node tools/test_content_wildcards.js
if (typeof require !== 'undefined' && require.main === module) {
  (async () => {
    const fs = require('node:fs');
    const path = require('node:path');
    const vm = require('node:vm');
    const root = path.resolve(__dirname, '..');
    const source = fs.readFileSync(path.join(root, 'sources/content.js'), 'utf8');
    const boundary = source.indexOf('    const guideBlockRecords');
    if (boundary < 0) throw new Error('content.js test extraction boundary is missing');
    const dictionary = JSON.parse(fs.readFileSync(path.join(root, 'sources/translations.json'), 'utf8'));
    const sandbox = {
      console, window: {},
      chrome: {
        storage: { onChanged: { addListener() {} }, sync: { get(keys, callback) { callback({ enabled: true }); } } },
        runtime: { getURL(value) { return value; } }
      },
      fetch: async () => ({ ok: true, json: async () => dictionary })
    };
    vm.runInNewContext(source.slice(0, boundary) +
      'window.api={loadTranslations,applyRegexTransformations,getWildcardCaptureIndexes,hasUnsafeWildcardMatch,dynamicValue:DYNAMIC_VALUE_TEXT}; }});',
      sandbox);
    await sandbox.window.api.loadTranslations();
    console.log(runContentWildcardTests(sandbox.window.api));
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
