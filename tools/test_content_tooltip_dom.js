// Browser DOM tests; see test_content_tooltip_dom.html for the standalone runner.
function runContentSorcererTooltipDomTests(api, table, fixtures) {
  let passed = 0;
  const check = (condition, name) => {
    if (!condition) throw new Error('Sorcerer: ' + name);
    passed++;
  };
  for (const {name, html} of fixtures) {
    const host = document.createElement('div');
    host.innerHTML = html;
    const elements = [...host.querySelectorAll('*')];
    const numbers = [...host.querySelectorAll('.d4-color-number')].map(e => [e, e.textContent]);
    const links = [...host.querySelectorAll('.d4-style-u')];
    let clicks = 0;
    links.forEach(e => e.addEventListener('click', () => clicks++));
    api.replaceText(host, table);
    check(!/[A-Za-z]{2,}/.test(host.textContent.replace(/\[(Damage|HP)\]/g, '')), name + ': English remained: ' + host.textContent);
    check(elements.every(e => host.contains(e)), name + ': elements retained');
    check(numbers.every(([e, text]) => e.textContent === text), name + ': numeric values retained: ' + JSON.stringify(numbers.filter(([e, text]) => e.textContent !== text).map(([e,text]) => [text,e.textContent])));
    links.forEach(e => e.click());
    check(clicks === links.length, name + ': listeners retained');
    const htmlAfter = host.innerHTML;
    api.replaceText(host, table);
    check(host.innerHTML === htmlAfter, name + ': repeated replacement');
  }
  check(api.applyRegexTransformations('Enchantments', []) === 'エンチャントメント', 'plural heading');
  check(api.applyRegexTransformations('Frost', []) === '寒気をまとう', 'ordinary affix unchanged');
  check(api.findStyledTranslationInSentence('Frost', '凍結スキルになり') === '凍結', 'skill tag in sentence');
  return {passed};
}

function runContentWarlockTooltipDomTests(api, table, fixtures) {
  let passed = 0;
  const check = (condition, name) => {
    if (!condition) throw new Error('Warlock: ' + name);
    passed++;
  };
  for (const {name, html} of fixtures) {
    const host = document.createElement('div');
    host.innerHTML = html;
    const elements = [...host.querySelectorAll('*')];
    const values = [...host.querySelectorAll('.d4-color-number')].map(e => [e, e.textContent]);
    const underlines = [...host.querySelectorAll('.d4-style-u')];
    let clicks = 0;
    underlines.forEach(e => e.addEventListener('click', () => clicks++));
    api.replaceText(host, table);
    const description = host.querySelector('.d4t-description');
    check(!/[A-Za-z]{2,}/.test(description.textContent.replaceAll('[Damage]', '')), name + ': English remained: ' + description.textContent);
    check(elements.every(e => host.contains(e)), name + ': elements retained');
    check(values.every(([e, value]) => e.textContent === value), name + ': numeric values retained');
    underlines.forEach(e => e.click());
    check(clicks === underlines.length, name + ': listeners retained');
    if (name === 'Ritualist Shard') {
      check(description.textContent.includes('蓄積1ごとに10.5%[x]') && description.textContent.includes('蓄積2ごとに効果範囲が30%[+]'), 'Ritualist numeric order');
      check([...host.querySelectorAll('.d4-color-important')].some(e => e.textContent === '邪教'), 'Occult style');
    }
    if (name === 'Mastermind Shard') check(description.querySelector('.d4-color-important').textContent === '再発動', 'Recast style');
    const translated = host.innerHTML;
    api.replaceText(host, table);
    check(host.innerHTML === translated, name + ': repeated replacement');
  }
  check(api.applyRegexTransformations('Occult', []) === '狂信者', 'ordinary Occult unchanged');
  check(api.applyRegexTransformations('Recast', []) === '再使用', 'ordinary Recast unchanged');
  check(api.findStyledTranslationInSentence('Occult Hellfire', '邪教の業火スキル') === '邪教の業火', 'contextual compound candidate');
  check(api.findStyledTranslationInSentence('Occult Hellfire', '邪教の業火と邪教業火') === null, 'ambiguous candidates rejected');
  check(api.findStyledTranslationInSentence('Occult Hellfire', '無関係な説明') === null, 'unmatched candidates rejected');
  return {passed};
}

function runContentMinionTooltipDomTests(api, table, fixtures) {
  const descriptions = [
    'リーパーは強力な鎌で敵を切り裂き、10秒ごとに強力な振りかぶり攻撃で大ダメージを与える。スケルトンウォーリアが闇スキルの性質を併せ持つようになる。',
    'シャドウ・メイジが死後の世界の力を振るい、爆発するシャドウ・ボルトを撃つ。スケルトンメイジが闇スキルの性質を併せ持つようになる。',
    'アイアン・ゴーレムは圧倒的な力で敵を気絶させ、標的の動きを制限する。ゴーレムが闇スキルの性質を併せ持つようになる。',
  ];
  let checks = 0;
  const check = (condition, label) => {
    if (!condition) throw new Error('Minion: ' + label);
    checks++;
  };
  fixtures.forEach((fixture, index) => {
    const host = document.createElement('div');
    host.innerHTML = fixture;
    const elements = [...host.querySelectorAll('*')];
    const numbers = [...host.querySelectorAll('.d4t-description .d4-color-number')].map(e => [e, e.textContent]);
    api.replaceText(host, table);
    check(host.querySelector('.d4t-description').textContent.trim() === descriptions[index], 'complete description ' + index);
    check(host.querySelector('.d4t-header').textContent === '強化', 'upgrade heading');
    check(elements.every(e => host.contains(e)), 'original elements retained');
    check(numbers.every(([e, text]) => e.textContent === text), 'description numeric values retained');
    check(host.querySelectorAll('.d4-color-important')[1].textContent === '闇', 'styled skill tag retained');
    const html = host.innerHTML;
    api.replaceText(host, table);
    check(host.innerHTML === html, 'repeated replacement stable');
  });
  return {checks};
}

function runContentTooltipDomTests(api, regexTable, fixture, sealFixture, skillFixtures, hellguardFixture) {
  let passed = 0;
  function check(condition, label) {
    if (!condition) throw new Error(label);
    passed++;
  }
  const host = document.createElement('div');
  const hellguard = document.createElement('div');
  hellguard.innerHTML = hellguardFixture;
  const hellguardElements = [...hellguard.querySelectorAll('*')];
  api.replaceText(hellguard, regexTable);
  check(hellguard.textContent === 'アボディアンは、〈アボディアンに命令〉の間、ブリムストーンを噴出する。移動中はブリムストーンを一定間隔で発射し、騎乗解除時に6個射出する。ブリムストーンはそれぞれ35% x [Damage]ダメージを与える。', 'Hellguard full paragraph: ' + hellguard.textContent);
  check(hellguardElements.every(e => hellguard.contains(e)), 'Hellguard styled elements retained');
  check(hellguard.querySelector('.d4-color-important').textContent === 'アボディアン', 'Hellguard Abodian style retained');
  check([...hellguard.querySelectorAll('.d4-style-u')].every(e => e.textContent === 'ブリムストーン'), 'Hellguard Brimstone underlines retained');
  const hellguardHtml = hellguard.innerHTML;
  api.replaceText(hellguard, regexTable);
  check(hellguard.innerHTML === hellguardHtml, 'Hellguard repeated translation stable');
  host.innerHTML = fixture;
  const tooltip = host.firstElementChild;
  const line = tooltip.querySelector('.d4t-list-affix');
  const wrapper = line.querySelector('.d4-color-unique');
  const underline = wrapper.querySelector('.d4-style-u');
  const duration = wrapper.querySelector('.d4-color-random');
  const values = [...wrapper.querySelectorAll('.d4-color-number')];
  const elements = [...tooltip.querySelectorAll('*')];
  let clicks = 0;
  underline.addEventListener('click', () => clicks++);
  const expected = '装飾品: エリートモンスターの群れを倒すと、25秒間にわたりモンスターパワーが1上昇し、獲得経験値量が25%増加する。';
  api.replaceText(tooltip, regexTable);
  check(line.textContent === expected, 'full sentence and trailing punctuation');
  check(elements.every(element => tooltip.contains(element)), 'all original elements retained');
  check(wrapper.querySelector('.d4-style-u') === underline && underline.textContent === 'モンスターパワー', 'underline retained');
  check(wrapper.querySelector('.d4-color-random') === duration && duration.textContent === '25', 'duration span retained');
  check(values[0].textContent === '1' && values[1].textContent === '25%', 'power and experience values retained');
  check([...wrapper.querySelectorAll('.d4-color-random,.d4-color-number')].map(e => e.textContent).join('/') === '25/1/25%', 'Japanese value order');
  underline.click();
  check(clicks === 1, 'existing listener retained');
  const translatedHtml = tooltip.outerHTML;
  for (let pass = 0; pass < 3; pass++) {
    api.replaceText(tooltip, regexTable);
    check(tooltip.outerHTML === translatedHtml, 'repeat pass ' + pass);
  }
  const outside = document.createElement('div');
  outside.innerHTML = fixture;
  outside.firstElementChild.className = '';
  api.replaceText(outside, regexTable);
  check(outside.textContent.includes('Killing an Elite Pack'), 'full sentence remains tooltip-only');

  const withProse = document.createElement('div');
  withProse.innerHTML = fixture;
  const effect = withProse.querySelector('.d4-color-unique');
  const suffix = effect.nextSibling;
  suffix.nodeValue += ' Additional prose.';
  api.replaceText(effect, regexTable);
  check(suffix.nodeValue === '. Additional prose.', 'does not consume adjacent prose');
  const sealHost = document.createElement('div');
  sealHost.innerHTML = sealFixture;
  const seal = sealHost.firstElementChild;
  const sealElements = [...seal.querySelectorAll('*')];
  const range = seal.querySelector('.d4-color-inactive');
  const rangeText = range.textContent;
  const demonform = seal.querySelector('.d4t-list-star .d4-color-important');
  api.replaceText(seal, regexTable);
  check(seal.querySelector('.d4t-list-affix').textContent === 'チャームスロットを7個解放', 'seal unlocked slots');
  check(seal.querySelector('.d4t-list-star').textContent === 'チャームスロット+1', 'seal extra slot');
  check(seal.querySelector('.d4t-list-mythic').textContent === 'セット・ボーナスに必要なチャーム数を1減らす（最低2個）。', 'seal set requirement');
  const effectLine = seal.querySelectorAll('.d4t-list-star')[1];
  check(effectLine.textContent === '悪鬼の肉塊:悪魔形態中のダメージ減少率+15%' + rangeText, 'seal set affix and numeric range');
  check(sealElements.every(element => seal.contains(element)), 'seal original elements retained');
  check(range.textContent === rangeText && demonform.textContent === '悪魔形態', 'seal range and emphasis retained');
  const sealHtml = seal.outerHTML;
  for (let pass = 0; pass < 3; pass++) {
    api.replaceText(seal, regexTable);
    check(seal.outerHTML === sealHtml, 'seal repeat pass ' + pass);
  }
  for (const [index, html] of skillFixtures.entries()) {
    // Test both HTML-parsed text and the adjacent Text nodes observed in React.
    for (const variant of (index === 0 ? ['raw', 'split', 'damage'] : ['raw', 'split'])) {
      const split = variant === 'split';
      const holder = document.createElement('div');
      holder.innerHTML = html;
      const tip = holder.firstElementChild;
      const description = tip.querySelector('.d4t-description');
      const originalElements = [...tip.querySelectorAll('*')];
      const numbers = [...description.querySelectorAll('.d4-color-number')];
      // 派生ケース: 実ダメージと倍率注記を表示するビルドの数値。
      if (variant === 'damage') {
        const amounts = {'245%': '157044', '25%': '158882', '250%': '1588821'};
        for (const node of numbers) {
          const multiplier = node.firstChild.nodeValue;
          if (amounts[multiplier]) {
            node.firstChild.nodeValue = amounts[multiplier];
            node.querySelector('.d4-color-lightgray').textContent = ` [${multiplier}]`;
          }
        }
      }
      const annotation = description.querySelector('.d4-color-lightgray');
      const wrapped = numbers.find(node => node.textContent.startsWith('('));
      if (split && wrapped) wrapped.firstChild.splitText(1);
      const active = [...description.querySelectorAll('.d4-color-label')]
        .find(node => node.textContent === 'Active');
      // Colon inside the label is also supported by the same common path.
      if (split && active) {
        active.firstChild.nodeValue += ':';
        active.nextSibling.nodeValue = active.nextSibling.nodeValue.slice(1);
      }
      let events = 0;
      annotation.addEventListener('click', () => events++);
      api.replaceText(tip, regexTable);
      const text = description.textContent;
      if (index === 0) {
        check(active.textContent === (split ? 'アクティブ:' : 'アクティブ'), `skill label colon boundary (split=${split}): ${active.textContent}`);
        check(text.includes('移動速度が4秒間60%[x]上昇する。'), 'Abodian duration and speed order');
        check(text.includes(variant === 'damage' ? '0.5秒ごとに158882 [25%]ダメージを与える。' : '0.5秒ごとに25% x [Damage]ダメージを与える。'), 'Abodian recurring damage');
        check(text.includes(variant === 'damage' ? '1588821 [250%]ダメージを与える。' : '250% x [Damage]ダメージを与える。'), 'Abodian dismount damage');
        check(!/Active|While|mount|Command|seconds|gaining|Abodian/.test(text), 'Abodian full translation');
      } else if (index === 1) {
        check(text.includes('最大ライフ（8% x [HP]）の8%を失う。'), 'duplicate percentage annotation association');
        check(wrapped.textContent === '8% x [HP]', 'split parentheses removed exactly once');
        check(!/Metamorphosis|Each|Skills|Burns|active|cancel/.test(text), 'modifier full translation');
      } else {
        check(text === '〈眩い咆哮〉はレッサー・デーモンの小さな頭蓋骨を放ち、その頭蓋骨が敵を探し、29.25% x [Damage]ダメージを与える。', 'Skull Splitter full translation');
      }
      check(originalElements.every(node => tip.contains(node)), 'skill original elements retained');
      annotation.click();
      check(events === 1, 'skill existing listener retained');
      const result = tip.outerHTML;
      for (let pass = 0; pass < 3; pass++) {
        api.replaceText(tip, regexTable);
        check(tip.outerHTML === result, 'skill repeated conversion stable');
      }
    }
  }
  return {passed};
}

async function runContentHeshaTooltipDomTests(api, table, fixtures) {
  let passed = 0;
  const check = (condition, label) => {
    if (!condition) throw new Error(label);
    passed++;
  };
  api.observeDOM(table);
  for (const [index, html] of fixtures.entries()) {
    for (const automatic of [false, true]) {
      const host = document.createElement('div');
      host.innerHTML = html;
      const tip = host.firstElementChild;
      const effect = tip.querySelector('.d4t-list-unique');
      const elements = [...tip.querySelectorAll('*')];
      const protector = effect.querySelector('.d4-color-important');
      const gorilla = [...effect.querySelectorAll('.d4-color-important')][1];
      const value = effect.querySelector(index ? '.d4t-value' : '.d4-color-random');
      const valueText = value.textContent;
      const notes = [...effect.querySelectorAll('.d4-color-inactive')].map(e => [e, e.textContent]);
      let clicks = 0;
      protector.addEventListener('click', () => clicks++);
      if (automatic) {
        document.body.append(host);
        await new Promise(resolve => setTimeout(resolve, 250));
      } else {
        api.replaceText(tip, table);
      }
      const amount = index ? '78%[x] [78]%' : '[50 - 60]%[x]';
      const expected = `〈守護者〉は離れた場所に召喚でき、叩きつけで敵を引き寄せるようになる。その範囲内にいる敵に対して自身のゴリラスキルで与えるダメージが${amount}増加する。敵がノックダウンされているかボスの場合、与えるダメージは2倍になる。`;
      check(effect.textContent.startsWith(expected), `Hesha full effect (${index}, observer=${automatic}): ${effect.textContent}`);
      check(elements.every(e => tip.contains(e)), 'Hesha original elements retained');
      check(protector.textContent === '守護者' && gorilla.textContent === 'ゴリラ', 'Hesha skill emphasis retained');
      check(value.textContent === valueText, 'Hesha numeric span retained');
      check(notes.every(([e, text]) => e.textContent === text), 'Hesha multiplier and range retained');
      if (index) check(effect.querySelector('.d4-color-mythic').textContent.startsWith(expected), 'Hesha mythic effect color retained');
      protector.click();
      check(clicks === 1, 'Hesha listener retained');
      const translated = tip.outerHTML;
      for (let pass = 0; pass < 3; pass++) {
        api.replaceText(tip, table);
        check(tip.outerHTML === translated, 'Hesha repeated translation stable');
      }
      host.remove();
    }
  }
  return {passed};
}

async function runContentPlannerTooltipDomTests(api, table, fixtures, sealFixture) {
  let passed = 0;
  const check = (condition, label) => {
    if (!condition) throw new Error(label);
    passed++;
  };
  api.observeDOM(table);
  for (const [index, html] of [...fixtures, sealFixture].entries()) {
    const host = document.createElement('div');
    host.innerHTML = html;
    const tip = host.firstElementChild;
    const originals = [...tip.querySelectorAll('*')];
    const modifiers = [...tip.querySelectorAll('ul li')].filter(e =>
      /becomes|makes you|does not replace|increases your|Hitting enemies/.test(e.textContent));
    const fortify = [...tip.querySelectorAll('.d4-style-u')].find(e => e.textContent === 'Fortifies');
    let fortifyClicks = 0;
    fortify?.addEventListener('click', () => fortifyClicks++);
    const annotations = [...tip.querySelectorAll('.d4-color-lightgray,.d4-color-inactive')]
      .map(node => [node, node.textContent]);
    document.body.append(host); // Real observer path, no direct replaceText call.
    await new Promise(resolve => setTimeout(resolve, 250));
    check(originals.every(node => tip.contains(node)), 'planner preserves original elements');
    check(annotations.every(([node, text]) => node.textContent === text.replace('Item Contribution', '装備による加算')), 'planner preserves numeric annotations');
    check(modifiers.length > 0 || index === fixtures.length, 'planner modifier fixture present');
    for (const row of modifiers) {
      check(!/becomes|Skill|makes you|Each|enemies|Stagger|Brimstones|Fortifies/.test(row.textContent), 'planner full modifier translation: ' + row.textContent);
    }
    if (index === 0) {
      check(tip.textContent.includes('行動制御効果を受けるたびに、10のよろめき状態'), 'contextual Incapacitated phrase');
      check(tip.textContent.includes('最大ライフ（4,774）の8%'), 'planner HP value preserved');
    } else if (index === 1) {
      check(tip.textContent.includes('176150 [138.25%]ダメージ'), 'lava damage annotation');
      check([...tip.querySelectorAll('.d4-style-u')].some(e => e.textContent === 'ブリムストーン'), 'Brimstones underline retained with contextual name');
    } else if (index === 2) {
      check(tip.textContent.includes('悪魔信仰召喚スキル'), 'compound styled tag');
      check(tip.textContent.includes('1564591 [246.19%]ダメージ'), 'turret damage annotation');
    } else if (index === 3) {
      check(modifiers.some(e => e.textContent.trim() === '〈闇の牢獄〉内の敵に命中すると、最大ライフ（597）の1%だけ自身が強化される。'), 'Fortifies complete sentence and value order');
      check(fortify?.textContent === '強化', 'Fortifies underline retained');
      fortify.click();
      check(fortifyClicks === 1, 'Fortifies listener retained');
    } else {
      check(tip.querySelector('.d4t-list-mythic').textContent === 'セット・ボーナスに必要なチャーム数を1減らす（最低2個）。', 'seal observer regression');
    }
    const translated = tip.outerHTML;
    api.replaceText(tip, table);
    check(tip.outerHTML === translated, 'planner repeated translation stable');
    host.remove();
  }
  return {passed};
}
