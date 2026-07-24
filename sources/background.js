chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(
    ['enabled', 'guideTranslationEnabled'],
    function(result) {
      const defaults = {};

      // 未設定値だけを初期化し、更新・再読み込み時はユーザー設定を維持する。
      if (typeof result.enabled === 'undefined') {
        defaults.enabled = true;
      }
      if (typeof result.guideTranslationEnabled === 'undefined') {
        defaults.guideTranslationEnabled = true;
      }
      if (Object.keys(defaults).length > 0) {
        chrome.storage.sync.set(defaults);
        console.log('[D4T] Initialized extension defaults', defaults);
      }
    }
  );
});

const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';
let creatingOffscreenDocument = null;
let releasingOffscreenDocument = null;
let extensionFeatureEnabled = false;
let guideTranslationFeatureEnabled = true;

const translationSettingsReady = new Promise(resolve => {
  chrome.storage.sync.get(
    ['enabled', 'guideTranslationEnabled'],
    result => {
      extensionFeatureEnabled = result.enabled === true;
      guideTranslationFeatureEnabled =
        result.guideTranslationEnabled !== false;
      resolve();
      if (!isTranslationRuntimeEnabled()) {
        releaseTranslationRuntime().catch(error => {
          console.error(
            '[D4T] Failed to release stale translation runtime:',
            error
          );
        });
      }
    }
  );
});

function isTranslationRuntimeEnabled() {
  return extensionFeatureEnabled && guideTranslationFeatureEnabled;
}

async function hasOffscreenDocument() {
  if (typeof chrome.offscreen?.hasDocument === 'function') {
    return chrome.offscreen.hasDocument();
  }

  const offscreenUrl = chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH);
  const contexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
    documentUrls: [offscreenUrl]
  });
  return contexts.length > 0;
}

async function ensureOffscreenDocument() {
  if (releasingOffscreenDocument) {
    await releasingOffscreenDocument;
  }
  if (await hasOffscreenDocument()) {
    return;
  }
  if (creatingOffscreenDocument) {
    await creatingOffscreenDocument;
    return;
  }

  creatingOffscreenDocument = chrome.offscreen.createDocument({
    url: OFFSCREEN_DOCUMENT_PATH,
    reasons: ['DOM_PARSER'],
    justification:
      'Keep Chrome Translator API available while translating Maxroll guide text.'
  });

  try {
    await creatingOffscreenDocument;
  } finally {
    creatingOffscreenDocument = null;
  }
}

function sendToOffscreen(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      {...message, target: 'offscreen'},
      response => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response);
      }
    );
  });
}

async function releaseTranslationRuntime() {
  if (releasingOffscreenDocument) {
    return releasingOffscreenDocument;
  }

  releasingOffscreenDocument = (async () => {
    if (creatingOffscreenDocument) {
      try {
        await creatingOffscreenDocument;
      } catch (error) {
        // 作成失敗時は閉じる対象がないため、そのまま終了する。
      }
    }
    if (!await hasOffscreenDocument()) {
      return;
    }

    try {
      await sendToOffscreen({action: 'releaseTranslator'});
    } catch (error) {
      // 文書が既に破棄済みでも、closeDocument の確認へ進む。
    }

    if (await hasOffscreenDocument()) {
      await chrome.offscreen.closeDocument();
    }
  })();

  try {
    await releasingOffscreenDocument;
  } finally {
    releasingOffscreenDocument = null;
  }
}

function forwardToOffscreen(message, sendResponse) {
  translationSettingsReady
    .then(() => {
      if (!isTranslationRuntimeEnabled()) {
        throw new DOMException(
          'Guide translation is disabled',
          'AbortError'
        );
      }
      return ensureOffscreenDocument();
    })
    .then(() => {
      chrome.runtime.sendMessage(
        {...message, target: 'offscreen'},
        response => {
          if (chrome.runtime.lastError) {
            sendResponse({
              ok: false,
              error: chrome.runtime.lastError.message
            });
            return;
          }
          sendResponse(response);
        }
      );
    })
    .catch(error => {
      sendResponse({
        ok: false,
        error: error.message,
        errorName: error.name
      });
    });
}

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== 'sync') {
    return;
  }
  if (changes.enabled) {
    extensionFeatureEnabled = changes.enabled.newValue === true;
  }
  if (changes.guideTranslationEnabled) {
    guideTranslationFeatureEnabled =
      changes.guideTranslationEnabled.newValue !== false;
  }
  if (
    (changes.enabled || changes.guideTranslationEnabled) &&
    !isTranslationRuntimeEnabled()
  ) {
    releaseTranslationRuntime().catch(error => {
      console.error('[D4T] Failed to release translation runtime:', error);
    });
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.target !== 'background') {
    return false;
  }

  if (
    message.action === 'translatorAvailability' ||
    message.action === 'translateText'
  ) {
    forwardToOffscreen(message, sendResponse);
    return true;
  }

  return false;
});
