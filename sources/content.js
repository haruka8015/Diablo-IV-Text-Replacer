// デバッグログの出力を切り替える変数
const D4DEBUG_DISPLAY = false;
// 初期化時変換をするまでのデバウンス待機時間(ms)
const DEBOUNCE_DELAY_MS = 1000;
// DOM変化時のデバウンス遅延時間を定義
const DEBOUNCE_DOM_DELAY_MS = 100;
// DOM変更に対するミューテーションの閾値を定義
const DOM_CHANGE_MUTATION_THRESHOLD = 5;

chrome.storage.sync.get(['enabled'], function(result) {
  if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded extension state:', result.enabled); // デバッグ用ログ
  if (result.enabled) {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Content script loaded'); // デバッグ用ログ

    let translationTable = {};

    function loadTranslations() {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Loading translations...'); // デバッグ用ログ
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
              // クォート文字に対応する正規表現を作成
              const escapedPattern = pattern.replace(/['’]/g, "['’]");
              regexTable.push([new RegExp(escapedPattern, 'gi'), replacement]);
            }
            if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded and sorted translation table:', regexTable); // デバッグ用ログ
            return regexTable;
          });
    }

    // 共通の変換処理関数
    function applyRegexTransformations(text, regexTable) {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Original text:', text); // デバッグ用ログ
      for (let [regex, replacement] of regexTable) {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Applying regex:', regex); // デバッグ用ログ
        const wordBoundaryRegex = new RegExp(`\\b${regex.source}\\b`, regex.flags);
        text = text.replace(wordBoundaryRegex, replacement);
      }
      return text;
    }

    function replaceText(node, regexTable) {
      if (node.nodeType === 3) { // テキストノード
        let newText = applyRegexTransformations(node.nodeValue, regexTable);
        if (newText !== node.nodeValue && D4DEBUG_DISPLAY) {
          console.log('[D4T] Text changed from:', node.nodeValue, 'to:', newText); // デバッグ用ログ
        }
        node.nodeValue = newText;
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
        let newTitle = applyRegexTransformations(el.getAttribute('title'), regexTable);
        if (newTitle !== el.getAttribute('title') && D4DEBUG_DISPLAY) {
          console.log('[D4T] Title changed from:', el.getAttribute('title'), 'to:', newTitle); // デバッグ用ログ
        }
        el.setAttribute('title', newTitle);
      });
    }

    let observeDOMTimer;

    function observeDOM(regexTable) {
      const observer = new MutationObserver(mutations => {
        if (D4DEBUG_DISPLAY) {
          console.log(`[D4T] Number of mutations observed: ${mutations.length}`);
        }

        if (mutations.length > DOM_CHANGE_MUTATION_THRESHOLD) {
          // すでにタイマーが設定されている場合はクリア
          if (observeDOMTimer) clearTimeout(observeDOMTimer);

          // mutationsが閾値を超えた場合はデバウンスで遅延させて全体をまとめて処理
          observeDOMTimer = setTimeout(() => {
            if (D4DEBUG_DISPLAY) {
              console.log('[D4T] Performing full-page translation due to high mutation count.');
            }
            replaceText(document.body, regexTable);
            replaceTitleAttributes(regexTable);
          }, DEBOUNCE_DOM_DELAY_MS);
        } else {
          // mutationsが閾値以下の場合は、逐次処理
          mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
              replaceText(node, regexTable);
              if (node.nodeType === 1 && node.hasAttribute('title')) {
                let title = node.getAttribute('title');
                let newTitle = applyRegexTransformations(title, regexTable);
                if (newTitle !== title && D4DEBUG_DISPLAY) {
                  console.log('[D4T] Title changed from:', title, 'to:', newTitle); // デバッグ用ログ
                }
                node.setAttribute('title', newTitle);
              }
            });
          });
        }
      });

      observer.observe(document.body, { childList: true, subtree: true });
      if (D4DEBUG_DISPLAY) console.log('[D4T] MutationObserver started'); // デバッグ用ログ
    }

    function applyTranslations() {
      if (D4DEBUG_DISPLAY) console.log('[D4T] applyTranslations started'); // デバッグ用ログ
      loadTranslations().then(regexTable => {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded regexTable:', regexTable); // デバッグ用ログ
        replaceText(document.body, regexTable);
        replaceTitleAttributes(regexTable);
        observeDOM(regexTable);

        document.body.addEventListener('mouseover', event => {
          handleMouseover(event, regexTable);
        });

        if (D4DEBUG_DISPLAY) console.log('[D4T] Translations applied on page load'); // デバッグ用ログ
      }).catch(error => {
        console.error('[D4T] Error loading translations:', error);
      });
    }

    let debounceTimer;

    function initialize() {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Initializing...'); // デバッグ用ログ

      // 既存のタイマーをクリアする
      if (debounceTimer) clearTimeout(debounceTimer);

      // 新しいタイマーを設定
      debounceTimer = setTimeout(() => {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Timeout completed'); // デバッグ用ログ
        applyTranslations();
      }, DEBOUNCE_DELAY_MS);
    }

    // DOMContentLoaded イベントを追加
    document.addEventListener('DOMContentLoaded', () => {
      if (D4DEBUG_DISPLAY) console.log('[D4T] DOMContentLoaded event triggered'); // デバッグ用ログ
      initialize();
    });

    // load イベントを追加
    window.addEventListener('load', () => {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Window load event triggered'); // デバッグ用ログ
      initialize();
    });

    // ページが既にロードされている場合にも対応
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Document already loaded'); // デバッグ用ログ
      initialize();
    }

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.action === 'convert') {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Manual convert triggered'); // デバッグ用ログ
        applyTranslations();
      }
    });

  } else {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Extension is disabled');
  }
});
