// Browser DOM tests; see test_content_tooltip_dom.html for the standalone runner.
function runContentTooltipDomTests(api, regexTable, fixture, sealFixture) {
  let passed = 0;
  function check(condition, label) {
    if (!condition) throw new Error(label);
    passed++;
  }
  const host = document.createElement('div');
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
  return {passed};
}
