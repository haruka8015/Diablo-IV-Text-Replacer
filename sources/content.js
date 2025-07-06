// デバッグログの出力を切り替える変数
const D4DEBUG_DISPLAY = false;
// 初期化時変換をするまでのデバウンス待機時間(ms)
const DEBOUNCE_DELAY_MS = 1000;
// DOM変化時のデバウンス遅延時間を定義
const DEBOUNCE_DOM_DELAY_MS = 100;
// DOM変更に対するミューテーションの閾値を定義
const DOM_CHANGE_MUTATION_THRESHOLD = 50;

chrome.storage.sync.get(['enabled'], function(result) {
  if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded extension state:', result.enabled); // デバッグ用ログ
  if (result.enabled) {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Content script loaded'); // デバッグ用ログ

    let translationTable = {};
    let compiledPatterns = null;    // 事前コンパイルされた正規表現パターンの配列

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

            // 事前コンパイルされた正規表現パターンの配列を初期化
            compiledPatterns = [];

            // キーの長さが長い順に並び替える（長いフレーズを優先的に処理）
            const sortedKeys = Object.keys(translationTable).sort((a, b) => b.length - a.length);

            // すべてのパターンを事前にコンパイル
            sortedKeys.forEach(pattern => {
              const replacement = translationTable[pattern];
              const escapedPattern = pattern.replace(/['']/g, "['']");
              
              compiledPatterns.push({
                regex: new RegExp(`\\b${escapedPattern}\\b`, 'gi'),
                replacement,
                minLength: pattern.length  // パターン自体の長さ
              });
            });
            
            if (D4DEBUG_DISPLAY) {
              console.log('[D4T] Loaded translation table:', {
                patterns: compiledPatterns.length
              });
            }
            
            // 後方互換性のため、従来のregexTableも返す
            const regexTable = [];
            sortedKeys.forEach(pattern => {
              const replacement = translationTable[pattern];
              const escapedPattern = pattern.replace(/['']/g, "['']");
              regexTable.push([new RegExp(escapedPattern, 'gi'), replacement]);
            });
            
            return regexTable;
          });
    }

    // 最適化された変換処理関数
    function applyOptimizedTransformations(text, stats = null) {
      const textLength = text.length;
      
      // 事前コンパイルされたパターンを適用（長さフィルタ付き）
      for (let {regex, replacement, minLength} of compiledPatterns) {
        if (minLength <= textLength) {
          if (stats) stats.attempts++;
          const newText = text.replace(regex, replacement);
          if (newText !== text) {
            text = newText;
            if (stats) stats.replacements++;
          }
        }
      }
      
      return text;
    }

    // 共通の変換処理関数（後方互換性のため残す）
    function applyRegexTransformations(text, regexTable, stats = null) {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Original text:', text); // デバッグ用ログ
      
      // 新しい最適化実装が利用可能な場合はそちらを使用
      if (compiledPatterns) {
        return applyOptimizedTransformations(text, stats);
      }
      
      // 従来の実装
      for (let [regex, replacement] of regexTable) {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Applying regex:', regex); // デバッグ用ログ
        const wordBoundaryRegex = new RegExp(`\\b${regex.source}\\b`, regex.flags);
        if (stats) stats.attempts++;
        const newText = text.replace(wordBoundaryRegex, replacement);
        if (stats && newText !== text) {
          stats.replacements++;
        }
        text = newText;
      }
      return text;
    }

    function replaceText(node, regexTable, stats = {nodes: 0, attempts: 0, replacements: 0, chars: 0}) {
      if (node.nodeType === 3) { // テキストノード
        stats.nodes++;
        stats.chars += node.nodeValue.length;
        let originalText = node.nodeValue;
        let newText = applyRegexTransformations(node.nodeValue, regexTable, stats);
        if (newText !== originalText && D4DEBUG_DISPLAY) {
          console.log('[D4T] Text changed from:', originalText, 'to:', newText); // デバッグ用ログ
        }
        node.nodeValue = newText;
      } else if (node.nodeType === 1 && !['SCRIPT', 'STYLE'].includes(node.tagName)) { // 要素ノードでスクリプトとスタイルを除外
        let childNodes = Array.from(node.childNodes);
        for (let child of childNodes) {
          replaceText(child, regexTable, stats);
        }
      }
      return stats;
    }

    function replaceTitleAttributes(regexTable, stats = {elements: 0, replaced: 0}) {
      const elements = document.querySelectorAll('[title]');
      stats.elements = elements.length;
      elements.forEach(el => {
        const originalTitle = el.getAttribute('title');
        let newTitle = applyRegexTransformations(originalTitle, regexTable);
        if (newTitle !== originalTitle) {
          stats.replaced++;
          if (D4DEBUG_DISPLAY) {
            console.log('[D4T] Title changed from:', originalTitle, 'to:', newTitle); // デバッグ用ログ
          }
        }
        el.setAttribute('title', newTitle);
      });
      return stats;
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
            // console.log(`[D4T] Batch translation triggered by ${mutations.length} mutations`);
            if (D4DEBUG_DISPLAY) {
              console.log('[D4T] Performing full-page translation due to high mutation count.');
            }
            const batchStartTime = performance.now();
            const textStats = replaceText(document.body, regexTable);
            const replaceEndTime = performance.now();
            const titleStats = replaceTitleAttributes(regexTable);
            const batchEndTime = performance.now();
            const patternsCount = regexTable.length;
            // console.log(`[D4T] Batch translation completed: Total ${(batchEndTime - batchStartTime).toFixed(2)}ms, Text replacement ${(replaceEndTime - batchStartTime).toFixed(2)}ms (${patternsCount} patterns × ${textStats.nodes} nodes = ${textStats.attempts} attempts, ${textStats.replacements} replacements, ${textStats.chars} chars), Title replacement ${(batchEndTime - replaceEndTime).toFixed(2)}ms (${titleStats.elements} elements, ${titleStats.replaced} replaced)`);
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
      const startTime = performance.now();
      loadTranslations().then(regexTable => {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded regexTable:', regexTable); // デバッグ用ログ
        const replaceStartTime = performance.now();
        const textStats = replaceText(document.body, regexTable);
        const replaceEndTime = performance.now();
        const titleStats = replaceTitleAttributes(regexTable);
        const totalEndTime = performance.now();
        const patternsCount = regexTable.length;
        // console.log(`[D4T] Translation completed: Total ${(totalEndTime - startTime).toFixed(2)}ms, Text replacement ${(replaceEndTime - replaceStartTime).toFixed(2)}ms (${patternsCount} patterns × ${textStats.nodes} nodes = ${textStats.attempts} attempts, ${textStats.replacements} replacements, ${textStats.chars} chars), Title replacement ${(totalEndTime - replaceEndTime).toFixed(2)}ms (${titleStats.elements} elements, ${titleStats.replaced} replaced)`);
        observeDOM(regexTable);


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