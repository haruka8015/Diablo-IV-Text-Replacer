async function runContentResourceTests(createApi, defaultApi, chromeStub, fixture) {
  let passed = 0;
  const check = (ok, label) => {if (!ok) throw new Error(label); passed++;};
  const originalUrl = location.href;
  const getSettings = chromeStub.storage.sync.get;
  const host = document.createElement('div');
  host.innerHTML = fixture;
  document.body.append(host);
  const requests = [];
  chromeStub.runtime.sendMessage = (message, callback) => {
    if (message.action === 'translatorAvailability') {
      callback({ok: true, availability: 'available'});
    } else {
      requests.push(message.text);
      callback({ok: true, text: '翻訳済み: ' + message.text});
    }
  };
  try {
    check(defaultApi.collectGuideBlocks(host).length === 0, 'resource selectors do not affect other paths');
    history.replaceState(null, '', '/d4/resources/horadric-cube');
    const api = createApi();
    const table = await api.loadTranslations();
    const root = host.firstElementChild;
    const blocks = api.collectGuideBlocks(root);
    for (const selector of ['p', 'h2', 'li', 'td', 'th']) {
      check(blocks.some(e => e.matches(selector)), 'resource includes ' + selector);
    }
    const mark = root.querySelector('mark');
    const link = root.querySelector('a');
    const sublist = root.querySelector('li ul');
    const rune = root.querySelector('[data-d4-id="2681166"]');
    await api.processMaxrollGuideRoot(root, table);
    check(requests.some(text => text.startsWith('The Horadric Cube')), 'raw English reaches translation');
    check(requests.some(text => text.includes('Utilize the')), 'nested list parent translated');
    check(requests.some(text => text.includes('target farmable')), 'nested list child translated');
    check(root.contains(mark) && root.contains(link) && root.contains(sublist), 'mark links and nested list retained');
    check(rune.querySelector('.d4-color-common').textContent === 'ティア', 'new rune label retains markup');
    check(!root.textContent.includes('唯一無二なる'), 'article The never replaced');
    const before = requests.length;
    await api.processMaxrollGuideRoot(root, table);
    check(requests.length === before, 'translated resources not sent again');
    chromeStub.storage.sync.get = (keys, callback) => callback({enabled: true, guideTranslationEnabled: false});
    const dictionaryApi = createApi();
    const dictionaryTable = await dictionaryApi.loadTranslations();
    host.innerHTML = fixture;
    await dictionaryApi.processMaxrollGuideRoot(host.firstElementChild, dictionaryTable);
    check(requests.length === before, 'translation OFF sends no text');
    check(host.querySelector('.d4-color-common').textContent === 'ティア', 'dictionary works with translation OFF');
  } finally {
    history.replaceState(null, '', originalUrl);
    chromeStub.storage.sync.get = getSettings;
    delete chromeStub.runtime.sendMessage;
    host.remove();
  }
  return {passed};
}
