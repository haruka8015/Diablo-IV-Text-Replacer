const TRANSLATOR_OPTIONS = {
  sourceLanguage: 'en',
  targetLanguage: 'ja'
};

let translatorPromise = null;
let translationQueue = Promise.resolve();
let translatorIdleTimer = null;
const TRANSLATOR_IDLE_TIMEOUT_MS = 30_000;

function clearTranslatorIdleTimer() {
  if (translatorIdleTimer) {
    clearTimeout(translatorIdleTimer);
    translatorIdleTimer = null;
  }
}

function scheduleTranslatorRelease() {
  clearTranslatorIdleTimer();
  translatorIdleTimer = setTimeout(() => {
    translatorIdleTimer = null;
    releaseTranslator().catch(() => {});
  }, TRANSLATOR_IDLE_TIMEOUT_MS);
}

async function getAvailability() {
  if (!('Translator' in self)) {
    return 'unsupported';
  }
  return Translator.availability(TRANSLATOR_OPTIONS);
}

async function getTranslator() {
  clearTranslatorIdleTimer();
  if (translatorPromise) {
    return translatorPromise;
  }

  translatorPromise = (async () => {
    const availability = await getAvailability();
    if (availability !== 'available') {
      throw new DOMException(
        `Translator is not ready: ${availability}`,
        'NotAllowedError'
      );
    }
    return Translator.create(TRANSLATOR_OPTIONS);
  })();

  try {
    return await translatorPromise;
  } catch (error) {
    translatorPromise = null;
    throw error;
  }
}

function enqueueTranslation(text) {
  const operation = translationQueue.then(async () => {
    const translator = await getTranslator();
    return translator.translate(text);
  });

  translationQueue = operation.catch(() => {});
  operation.then(scheduleTranslatorRelease, scheduleTranslatorRelease);
  return operation;
}

function releaseTranslator() {
  clearTranslatorIdleTimer();
  const operation = translationQueue.then(async () => {
    let translator = null;
    if (translatorPromise) {
      try {
        translator = await translatorPromise;
      } catch (error) {
        // 作成途中で失敗している場合も参照は破棄する。
      }
    }
    translatorPromise = null;
    translator?.destroy();
  });

  translationQueue = operation.catch(() => {});
  return operation;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.target !== 'offscreen') {
    return false;
  }

  if (message.action === 'translatorAvailability') {
    getAvailability()
      .then(availability => sendResponse({ok: true, availability}))
      .catch(error => {
        sendResponse({ok: false, error: error.message});
      });
    return true;
  }

  if (message.action === 'translateText') {
    enqueueTranslation(message.text)
      .then(text => sendResponse({ok: true, text}))
      .catch(error => {
        sendResponse({
          ok: false,
          error: error.message,
          errorName: error.name
        });
      });
    return true;
  }

  if (message.action === 'releaseTranslator') {
    releaseTranslator()
      .then(() => sendResponse({ok: true}))
      .catch(error => {
        sendResponse({
          ok: false,
          error: error.message,
          errorName: error.name
        });
      });
    return true;
  }

  return false;
});
