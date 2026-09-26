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
    ['Weapon Expertise', '武器の専門知識'],
    ['Spirit Boons', '精霊の恩恵'],
    ['Specializations', 'カテゴリー'],
    ['Enchantment Effect', 'エンチャントメントの効果'],
    ['Spirit Hall', '精霊の広間'],
    ['Oaths', '誓約'],
    ['Soul Shards', 'ソウル・シャード'],
    ['12.5% of damage dealt as Bleed damage.', 'ダメージの12.5%を流血ダメージとして与える。'],
    ['Killing an enemy grants +8.5% Attack Speed for 2 seconds.', '敵をキルすると2秒間、攻撃速度が8.5%上昇する。'],
    ['You have a 7.5% chance to generate 3 Fury when hitting a crowd controlled enemy.',
     '行動制御効果を受けた敵に攻撃を当てると7.5%の確率で怒気3を得る。'],
    ['Rank 3/10', 'ランク 3/10'],
    ['Next Rank: 4', '次ランク: 4'],
    ['This Enchantment Slot is locked. Reach Level 30 to unlock it.',
     'エンチャントメントスロットはロックされています。レベル30で解放されます。'],
    ["Each time you Summon a Conjuration that isn’t a Familiar, you have a 25% chance to Summon a Familiar of the same Element.",
     '使い魔以外の召喚を行うたび、25%の確率で同属性の使い魔を1体召喚する。'],
    ['You can pick a Passive Skill for both the Spirit slots.', '精霊のスロットの両方にパッシブ・スキルを選択できます。'],
    ["Grants the Summon Ae'grom skill.", 'アエ=グロム召喚スキルを付与する。'],
    ['Grants the Summon Abodian skill.', 'アヴォディアン召喚スキルを付与する。'],
    ['Grants the Summon Laalish skill.', 'スキル「ラアリシュ召喚」を付与する。'],
    ['Grants the Summon Valloch skill.', 'スキル「ヴァロク召喚」を付与する。'],
    ['Casting a Juggernaut Skill consumes a stack of Resolve to deal 20% more damage.',
     '重装者スキルを使用すると決意の蓄積が1消費されてダメージが20%増加する。'],
    ['Book of the Dead', '死者の書'],
    ['UPGRADES', '強化'],
    ['Reapers wield a powerful cleaving scythe and have a wind-up attack that deals heavy damage every 10 seconds.',
     'リーパーは強力な鎌で敵を切り裂き、10秒ごとに強力な振りかぶり攻撃で大ダメージを与える。'],
    ['Shadow Mages wield power from the beyond, firing bursting shadow bolts.',
     'シャドウ・メイジが死後の世界の力を振るい、爆発するシャドウ・ボルトを撃つ。'],
    ['Skeleton Warrior is also a Bone Skill.', 'スケルトンウォーリアが骨スキルの性質を併せ持つようになる。'],
    ['Skeleton Warrior is also a Darkness Skill.', 'スケルトンウォーリアが闇スキルの性質を併せ持つようになる。'],
    ['Skeleton Mage is also a Darkness Skill.', 'スケルトンメイジが闇スキルの性質を併せ持つようになる。'],
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
      console, window: { location: { hostname: 'maxroll.gg' } },
      chrome: {
        storage: { onChanged: { addListener() {} }, sync: { get(keys, callback) { callback({ enabled: true }); } } },
        runtime: { getURL(value) { return value; } }
      },
      fetch: async () => ({ ok: true, json: async () => dictionary })
    };
    const dropStart = source.indexOf('    function replaceDropSourceText(');
    const dropEnd = source.indexOf('    function replaceTitleAttributes(', dropStart);
    if (dropStart < 0 || dropEnd < 0) throw new Error('drop source extraction boundary is missing');
    const labelStart = source.indexOf('    function getSplinterLabelTranslation(');
    const labelEnd = source.indexOf('    function replaceTextNodeRun(', labelStart);
    if (labelStart < 0 || labelEnd < 0) throw new Error('splinter label extraction boundary is missing');
    const testSource = source.slice(0, boundary) + source.slice(dropStart, dropEnd) + source.slice(labelStart, labelEnd) +
      'window.api={loadTranslations,applyRegexTransformations,replaceDropSourceText,getSplinterLabelTranslation,findStyledTranslationInSentence,getWildcardCaptureIndexes,hasUnsafeWildcardMatch,dynamicValue:DYNAMIC_VALUE_TEXT}; }});';
    vm.runInNewContext(testSource, sandbox);
    await sandbox.window.api.loadTranslations();
    // 特定のスキル名によらず、完全一致の候補を全文と照合する。
    const styledSandbox = {
      ...sandbox, window: {},
      fetch: async () => ({ok: true, json: async () => ({
        'Test\\s+Term': '第一訳', 'Test Term': '第二訳',
        'Test (.*?)': '汎用訳', "Hero's": '所有格訳',
        '__D4T_STYLED_TERM__:Context Term': '文脈訳\n別の文脈訳',
      })}),
    };
    vm.runInNewContext(testSource, styledSandbox);
    await styledSandbox.window.api.loadTranslations();
    const styledCases = [
      ['Context Term', '文脈訳を使う。', '文脈訳'],
      ['Context Term', '文脈訳と別の文脈訳を使う。', null],
      ['Context Term', '対応しない文章。', null],
      ['Test Term', '第二訳を使用する。', '第二訳'],
      ['Test Term', '第一訳を使用する。', '第一訳'],
      ['Test Term', '第一訳と第二訳を使用する。', null],
      ['Test Term', '対応する訳がない。', null],
      ['Prefix Test Term', '第二訳を使用する。', null],
      ['Test Anything', '汎用訳を使用する。', null],
      ['Hero’s', '所有格訳を使用する。', '所有格訳'],
    ];
    for (const [raw, sentence, expected] of styledCases) {
      if (styledSandbox.window.api.findStyledTranslationInSentence(raw, sentence) !== expected) throw new Error('styled term candidate: ' + raw + ' / ' + sentence);
    }
    if (sandbox.window.api.findStyledTranslationInSentence('The Protector', '〈守護者〉は離れた場所に召喚できる。') !== '守護者') throw new Error('Protector full-sentence candidate');
    if (sandbox.window.api.applyRegexTransformations('The Protector', []) !== '庇護者') throw new Error('Protector ordinary translation changed');
    console.log({styledTermChecks: styledCases.length + 2});
    if (styledSandbox.window.api.applyRegexTransformations('Context Term', []) !== 'Context Term') throw new Error('styled metadata leaked into ordinary replacement');
    // Maxroll S15_SeasonalSocketable全8系統。装備欄は英語名の末尾語を表示する。
    const labelCases = [
      ['Soulstone', 'ソウルストーン'], ['Anguish', '苦悶'], ['Pain', '苦痛'],
      ['Damnation', '断罪'], ['Mother', '母'], ['Hellfire', '業火'],
      ['Sin', '罪悪'], ['Lies', '欺瞞'],
    ];
    const registeredLabels = Object.keys(dictionary).filter(key => key.startsWith('__D4T_SPLINTER_LABEL__:')).map(key => key.slice('__D4T_SPLINTER_LABEL__:'.length)).sort();
    if (JSON.stringify(registeredLabels) !== JSON.stringify(labelCases.map(([name]) => name).sort())) throw new Error('splinter label coverage');
    const labelElement = { matches: () => true };
    for (const [raw, expected] of labelCases) {
      const actual = sandbox.window.api.getSplinterLabelTranslation([{parentElement:labelElement}], ' ' + raw.toUpperCase() + ' ');
      if (actual !== expected) throw new Error('splinter label: ' + raw);
    }
    const generalLabelCases = [['Pain', '痛む'], ['Damnation', '断罪を呼びし'], ['Soulstone', 'Soulstone'], ['Mother', 'Mother'], ['Sin', '罪'], ['Hellfire', '業火']];
    for (const [raw, expected] of generalLabelCases) {
      const actual = sandbox.window.api.applyRegexTransformations(raw, [], null, {}, true);
      if (actual !== expected) throw new Error('general dictionary changed: ' + raw + ' => ' + actual);
    }
    const labelMisses = [
      [[{parentElement:{matches:()=>false}}], 'Pain'],
      [[{parentElement:labelElement}], 'Unknown'],
      [[{parentElement:labelElement}], 'Abyssal Splinter of Pain'],
      [[{parentElement:labelElement}], 'Terror'],
      [[{parentElement:labelElement}], 'Destruction'],
      [[{parentElement:labelElement}], 'Hatred'],
      [[{parentElement:labelElement}, {parentElement:{matches:()=>true}}], 'Pain'],
    ];
    for (const [nodes, raw] of labelMisses) {
      if (sandbox.window.api.getSplinterLabelTranslation(nodes, raw) !== null) throw new Error('splinter scope: ' + raw);
    }
    sandbox.window.location.hostname = 'mobalytics.gg';
    if (sandbox.window.api.getSplinterLabelTranslation([{parentElement:labelElement}], 'Pain') !== null) throw new Error('splinter host scope');
    sandbox.window.location.hostname = 'maxroll.gg';
    console.log({ splinterLabelChecks: 1 + labelCases.length + generalLabelCases.length + labelMisses.length + 1 });
    const dropCases = [
      ['The Butcher', 'ブッチャー'],
      ['The Beast in the Ice', '氷に包まれた獣'],
      ['Grigoire, The Galvanic Saint', '電撃の聖人グリゴワール'],
      ['The Butcher, Grigoire, The Galvanic Saint, The Beast in the Ice', 'ブッチャー, 電撃の聖人グリゴワール, 氷に包まれた獣'],
      [' grigoire , the galvanic saint ', '電撃の聖人グリゴワール'],
      ['Grigoire, Andariel', 'グリゴワール, アンダリエル'],
      ['Butcher, Beast In The Ice, Grigoire', 'ブッチャー, 氷に包まれた獣, グリゴワール'],
      ['The Butcher, Duriel, King of Maggots', 'ブッチャー, デュリエル, マゴット・キング'],
    ];
    for (const [raw, expected] of dropCases) {
      const textNode = { nodeType: 3, nodeValue: raw };
      const element = { children: [], childNodes: [textNode], firstChild: textNode };
      for (let pass = 0; pass < 3; pass++) {
        sandbox.window.api.replaceDropSourceText(element, { nodes: 0, chars: 0, replacements: 0 });
        textNode.nodeValue = sandbox.window.api.applyRegexTransformations(textNode.nodeValue, [], null, {}, true);
        if (textNode.nodeValue !== expected) throw new Error('drop source: ' + JSON.stringify({raw, expected, actual: textNode.nodeValue, pass}));
      }
    }
    console.log({ dropSourceChecks: dropCases.length * 3 });
    console.log(runContentWildcardTests(sandbox.window.api));
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
