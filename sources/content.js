chrome.storage.sync.get(['enabled'], function(result) {
  console.log('[D4T] Loaded extension state:', result.enabled); // デバッグ用ログ
  if (result.enabled) {
    console.log('[D4T] Content script loaded'); // デバッグ用ログ

    let translationTable = {};

    function loadTranslations() {
      console.log('[D4T] Loading translations...'); // デバッグ用ログ
      const url = chrome.runtime.getURL('translations.json');
      return fetch(url)
        .then(response => {
          if (!response.ok) {
            throw new Error(`[D4T] Failed to load translations.json, status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          translationTable = data;

          // キーの長さが長い順に並び替える
          const sortedKeys = Object.keys(translationTable).sort((a, b) => b.length - a.length);
          const sortedTranslationTable = {};
          sortedKeys.forEach(key => {
            sortedTranslationTable[key] = translationTable[key];
          });

          const regexTable = [];
          for (let [pattern, replacement] of Object.entries(sortedTranslationTable)) {
            regexTable.push([new RegExp(pattern, 'gi'), replacement]);
          }
          console.log('[D4T] Loaded and sorted translation table:', regexTable); // デバッグ用ログ
          return regexTable;
        });
    }

    function replaceText(node, regexTable) {
      if (node.nodeType === 3) { // テキストノード
        let text = node.nodeValue;
        console.log('[D4T] Original text:', text); // デバッグ用ログ
        for (let [regex, replacement] of regexTable) {
          text = text.replace(regex, replacement);
        }
        node.nodeValue = text;
        console.log('[D4T] Replaced text:', text); // デバッグ用ログ
      } else if (node.nodeType === 1 && !['SCRIPT', 'STYLE'].includes(node.tagName)) { // 要素ノードでスクリプトとスタイルを除外
        let childNodes = Array.from(node.childNodes);
        for (let child of childNodes) {
          replaceText(child, regexTable);
        }
      }
    }

    function replaceTitleAttributes(regexTable) {
      const elements = document.querySelectorAll('[title]');
      elements.forEach(el => {
        let title = el.getAttribute('title');
        console.log('[D4T] Original title:', title); // デバッグ用ログ
        for (let [regex, replacement] of regexTable) {
          title = title.replace(regex, replacement);
        }
        el.setAttribute('title', title);
        console.log('[D4T] Replaced title:', title); // デバッグ用ログ
      });
    }

    function observeDOM(regexTable) {
      const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
          mutation.addedNodes.forEach(node => {
            replaceText(node, regexTable);
            if (node.nodeType === 1 && node.hasAttribute('title')) {
              let title = node.getAttribute('title');
              for (let [regex, replacement] of regexTable) {
                title = title.replace(regex, replacement);
              }
              node.setAttribute('title', title);
            }
          });
        });
      });

      observer.observe(document.body, { childList: true, subtree: true });
      console.log('[D4T] MutationObserver started'); // デバッグ用ログ
    }

    function applyTranslations() {
      console.log('[D4T] applyTranslations started'); // デバッグ用ログ
      loadTranslations().then(regexTable => {
        replaceText(document.body, regexTable);
        replaceTitleAttributes(regexTable);
        observeDOM(regexTable);

        document.body.addEventListener('mouseover', event => {
          if (event.target.hasAttribute('title')) {
            let title = event.target.getAttribute('title');
            for (let [regex, replacement] of regexTable) {
              title = title.replace(regex, replacement);
            }
            event.target.setAttribute('title', title);
          }
        });
        console.log('[D4T] Translations applied on page load'); // デバッグ用ログ
      }).catch(error => {
        console.error('[D4T] Error loading translations:', error);
      });
    }

    function initialize() {
      console.log('[D4T] Initializing...'); // デバッグ用ログ
      setTimeout(() => {
        console.log('[D4T] Timeout completed'); // デバッグ用ログ
        applyTranslations();
      }, 500); // 500ミリ秒の遅延を追加
    }

    // DOMContentLoaded イベントを追加
    document.addEventListener('DOMContentLoaded', () => {
      console.log('[D4T] DOMContentLoaded event triggered'); // デバッグ用ログ
      initialize();
    });

    // load イベントを追加
    window.addEventListener('load', () => {
      console.log('[D4T] Window load event triggered'); // デバッグ用ログ
      initialize();
    });

    // ページが既にロードされている場合にも対応
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      console.log('[D4T] Document already loaded'); // デバッグ用ログ
      initialize();
    }

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.action === 'convert') {
        console.log('[D4T] Manual convert triggered'); // デバッグ用ログ
        applyTranslations();
      }
    });
  } else {
    console.log('[D4T] Extension is disabled');
  }
});
