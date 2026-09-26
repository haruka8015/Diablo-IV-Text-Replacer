// Browser DOM tests; see test_content_tooltip_dom.html for the standalone runner.
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
    check(annotations.every(([node, text]) => node.textContent === text), 'planner preserves numeric annotations');
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
