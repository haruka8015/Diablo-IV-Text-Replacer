// Translation service stub deliberately mistranslates unprotected Paragon.
// Exercise the real guide pipeline, including its node-by-node fallback.
async function runContentGuideTermTests(api, table, chromeStub, glyphFixture) {
  let passed = 0;
  const check = (ok, label) => {
    if (!ok) throw new Error(label);
    passed++;
  };
  const requests = [];
  let corrupt = false;
  chromeStub.runtime.sendMessage = (message, callback) => {
    if (message.action === 'translatorAvailability') {
      callback({ok: true, availability: 'available'});
      return;
    }
    requests.push(message.text);
    let text = message.text.replace(/Paragon|パラゴン/gi, '亀鑑').replace(/Choose/g, '選択');
    if (corrupt) text = text.replace(/ZXQJ\d{4}QJQXZ/g, '');
    callback({ok: true, text});
  };
  const host = document.createElement('div');
  host.className = 'maxroll-rich-text-editor';
  document.body.append(host);
  try {
    const style = document.createElement('style');
    style.textContent = '.glyph-color-test {color: rgb(232,232,232)} .glyph-color-test .d4-color-legendary {color: rgb(255,128,0)}';
    host.append(style);
    for (const prefix of ['\u200d', ' \u200b\u2060 ']) {
      const p = document.createElement('p');
      p.className = 'glyph-color-test';
      p.innerHTML = 'Choose ' + glyphFixture.replace('\u200d', prefix) + '.';
      host.append(p);
      const glyph = p.querySelector('.d4-glyph');
      const label = glyph.querySelector('.d4-color-legendary');
      const labelText = label.firstChild;
      const separator = label.previousSibling;
      const icon = glyph.querySelector('.d4t-sprite-icon');
      const color = getComputedStyle(label).color;
      let clicks = 0;
      glyph.addEventListener('click', () => clicks++);
      api.translateGuideSemanticElements(p, table);
      check(label.textContent === '優越' && label.firstChild === labelText, 'dictionary keeps colored text node');
      check(separator.nodeValue === prefix, 'decorative separator retained');
      await api.processMaxrollGuideRoot(p, table);
      check(label.textContent === '優越' && getComputedStyle(label).color === color, 'machine translation retains glyph color');
      check(p.contains(glyph) && glyph.contains(icon) && glyph.contains(label), 'glyph and icon identities retained');
      glyph.click();
      check(clicks === 1, 'glyph listener retained');
      const result = glyph.outerHTML;
      for (let pass = 0; pass < 3; pass++) api.translateGuideSemanticElements(p, table);
      check(glyph.outerHTML === result, 'glyph repeated translation stable');
      p.remove();
    }
    for (const input of ['Paragon', 'Choose Paragon.', 'Choose パラゴン and PARAGON.']) {
      const p = document.createElement('p');
      p.textContent = input;
      host.append(p);
      await api.processMaxrollGuideRoot(p, table);
      check(p.textContent.includes('パラゴン') && !/亀鑑|Paragon/i.test(p.textContent), 'guide keeps term: ' + input);
      check(!/ZXQJ/.test(p.textContent), 'no exposed token');
      p.remove();
    }
    const p = document.createElement('p');
    p.innerHTML = 'Choose <strong>Paragon</strong> and <a href="#test">boards</a>.';
    host.append(p);
    const strong = p.querySelector('strong');
    const link = p.querySelector('a');
    await api.processMaxrollGuideRoot(p, table);
    check(p.contains(strong) && p.contains(link) && strong.textContent === 'パラゴン', 'guide retains wrappers and links');
    const fallback = document.createElement('p');
    fallback.textContent = 'Choose Paragon and パラゴン.';
    host.append(fallback);
    check(await api.translateGuideTextNodesInPlace(fallback, table), 'fallback translated');
    check(fallback.textContent === '選択パラゴンandパラゴン.', 'fallback protects both forms');
    check(requests.length > 0 && requests.every(text => !/Paragon|パラゴン/i.test(text)), 'service never receives protected term');
    corrupt = true;
    fallback.textContent = 'Choose Paragon.';
    check(!await api.translateGuideTextNodesInPlace(fallback, table), 'fallback rejects missing term token');
    check(fallback.textContent === 'Choose Paragon.', 'failed fallback preserves source');
    const broken = document.createElement('p');
    broken.textContent = 'Choose Paragon.';
    host.append(broken);
    await api.processMaxrollGuideRoot(broken, table);
    check(broken.textContent.includes('パラゴン') && !broken.textContent.includes('亀鑑'), 'corrupt service output falls back to dictionary');
  } finally {
    host.remove();
    delete chromeStub.runtime.sendMessage;
  }
  return {passed};
}
