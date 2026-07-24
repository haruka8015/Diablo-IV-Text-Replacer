// デバッグログの出力を切り替える変数
const D4DEBUG_DISPLAY = false;
// 初期化時変換をするまでのデバウンス待機時間(ms)
const DEBOUNCE_DELAY_MS = 1000;
// DOM変化時のデバウンス遅延時間を定義
const DEBOUNCE_DOM_DELAY_MS = 100;
// DOM変更に対するミューテーションの閾値を定義
const DOM_CHANGE_MUTATION_THRESHOLD = 50;

let extensionEnabled = false;

const BLOCK_BOUNDARY_TAGS = new Set([
  'ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 'BR', 'DIV', 'DL', 'DT', 'DD',
  'FIELDSET', 'FIGCAPTION', 'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3',
  'H4', 'H5', 'H6', 'HEADER', 'HR', 'LI', 'MAIN', 'NAV', 'OL', 'P', 'PRE',
  'SECTION', 'TABLE', 'TBODY', 'TD', 'TFOOT', 'TH', 'THEAD', 'TR', 'UL'
]);
const IGNORED_TEXT_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT']);
const DYNAMIC_VALUE_TEXT = /^\s*(\[?[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?(?:\s*[-–]\s*[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?)?\]?(?:%x|x%|%|x|\+)?)\s*$/;
const SUPPLEMENTARY_VALUE_MARKER_TEXT =
  /^\s*\[(?:x|\+|HP|Damage)\]\s*$/i;
const LONG_TEXT_TOOLTIP_SELECTOR =
  '.d4t-GameTooltip, .d4t-SkillTagTooltip';

// popup で状態が変わったら、開いているすべての対象タブへ即時反映する。
// OFF時はリロードによって既に変換済みのDOMも元の表示へ戻す。
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== 'sync' || !changes.enabled) {
    return;
  }

  const newEnabled = changes.enabled.newValue === true;
  if (newEnabled === extensionEnabled) {
    return;
  }

  extensionEnabled = newEnabled;
  window.location.reload();
});

chrome.storage.sync.get(['enabled'], function(result) {
  if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded extension state:', result.enabled); // デバッグ用ログ
  extensionEnabled = result.enabled === true;
  if (extensionEnabled) {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Content script loaded'); // デバッグ用ログ

    let translationTable = {};
    let compiledPatterns = null;    // 通常の短い正規表現パターン
    let compiledWholeSentencePatterns = null; // Tooltip内だけで使う長文パターン

    function createTranslationRegex(pattern) {
      // Maxroll側のタイポグラフィ変換でASCIIの'が’になる場合も照合する。
      const escapedPattern = pattern.replace(/['’]/g, "['’]");
      const leadingBoundary = /^[A-Za-z0-9_]/.test(pattern) ? '\\b' : '';
      const trailingBoundary = /[A-Za-z0-9_]$/.test(pattern) ? '\\b' : '';
      return new RegExp(`${leadingBoundary}${escapedPattern}${trailingBoundary}`, 'gi');
    }

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
            compiledWholeSentencePatterns = [];

            // キーの長さが長い順に並び替える（長いフレーズを優先的に処理）
            const wildcardCount = pattern =>
              (pattern.match(/\(\.\*\?\)/g) || []).length;
            const sortedKeys = Object.keys(translationTable).sort((a, b) => {
              const wildcardDifference = wildcardCount(a) - wildcardCount(b);
              return wildcardDifference || b.length - a.length;
            });

            // すべてのパターンを事前にコンパイル
            sortedKeys.forEach(pattern => {
              const replacement = translationTable[pattern];
              
              const wholeSentence =
                pattern.includes('\\s+') &&
                (
                  pattern.includes('\\.') ||
                  pattern.includes(':') ||
                  pattern.length >= 80
                );
              const compiledPattern = {
                regex: createTranslationRegex(pattern),
                replacement,
                wholeSentence,
                // 正規表現キーの文字数は実際の表示文字数より長くなるため、
                // 長さによる除外を行わない。
                minLength: /[\\()[\]{}+*?|]/.test(pattern) ? 0 : pattern.length
              };
              if (wholeSentence) {
                compiledWholeSentencePatterns.push(compiledPattern);
              } else {
                compiledPatterns.push(compiledPattern);
              }
            });
            
            if (D4DEBUG_DISPLAY) {
              console.log('[D4T] Loaded translation table:', {
                patterns: compiledPatterns.length,
                tooltipPatterns: compiledWholeSentencePatterns.length
              });
            }
            
            // 後方互換性のため、従来のregexTableも返す
            const regexTable = [];
            sortedKeys.forEach(pattern => {
              const replacement = translationTable[pattern];
              regexTable.push([createTranslationRegex(pattern), replacement]);
            });
            
            return regexTable;
          });
    }

    // 最適化された変換処理関数
    function applyCompiledPatternList(text, patterns, stats, matchInfo) {
      const textLength = text.length;

      for (let {regex, replacement, minLength, wholeSentence} of patterns) {
        if (minLength <= textLength) {
          if (stats) stats.attempts++;
          const newText = text.replace(regex, replacement);
          if (newText !== text) {
            text = newText;
            if (stats) stats.replacements++;
            if (matchInfo && wholeSentence) {
              matchInfo.wholeSentence = true;
            }
          }
        }
      }

      return text;
    }

    function applyOptimizedTransformations(
      text,
      stats = null,
      matchInfo = null,
      allowWholeSentence = false
    ) {
      // 長文リストはTooltip内だけで走査し、通常ページの置換コストから完全に外す。
      if (allowWholeSentence) {
        text = applyCompiledPatternList(
          text,
          compiledWholeSentencePatterns,
          stats,
          matchInfo
        );
      }
      return applyCompiledPatternList(text, compiledPatterns, stats, matchInfo);
    }

    // 共通の変換処理関数（後方互換性のため残す）
    function applyRegexTransformations(
      text,
      regexTable,
      stats = null,
      matchInfo = null,
      allowWholeSentence = false
    ) {
      if (D4DEBUG_DISPLAY) console.log('[D4T] Original text:', text); // デバッグ用ログ
      
      // 新しい最適化実装が利用可能な場合はそちらを使用
      if (compiledPatterns) {
        return applyOptimizedTransformations(
          text,
          stats,
          matchInfo,
          allowWholeSentence
        );
      }
      
      // 従来の実装
      for (let [regex, replacement] of regexTable) {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Applying regex:', regex); // デバッグ用ログ
        if (stats) stats.attempts++;
        const newText = text.replace(regex, replacement);
        if (stats && newText !== text) {
          stats.replacements++;
        }
        text = newText;
      }
      return text;
    }

    function replaceTextNodeRun(
      textNodes,
      regexTable,
      stats,
      supplementaryRangeNodes = [],
      containerNode = null
    ) {
      const originalText = textNodes.map(textNode => textNode.nodeValue).join('');
      stats.nodes += textNodes.length;
      stats.chars += originalText.length;

      const tooltipContainer =
        containerNode?.nodeType === 1
          ? containerNode.closest(LONG_TEXT_TOOLTIP_SELECTOR)
          : textNodes[0]?.parentElement?.closest(LONG_TEXT_TOOLTIP_SELECTOR);
      const matchInfo = {wholeSentence: false};
      const newText = applyRegexTransformations(
        originalText,
        regexTable,
        stats,
        matchInfo,
        Boolean(tooltipContainer)
      );
      if (newText === originalText) {
        return false;
      }

      if (D4DEBUG_DISPLAY) {
        console.log('[D4T] Text changed from:', originalText, 'to:', newText);
      }

      // Tooltip全文では、装飾spanと可変数値を既存位置に残して文章を配分する。
      const isTooltipSentence =
        matchInfo.wholeSentence &&
        Boolean(tooltipContainer);
      const anchors = [];
      let requiredAnchorCount = 0;
      const occupiedAnchorRanges = [];

      function isStyledTextNode(textNode) {
        let element = textNode.parentElement;
        while (element && element !== containerNode) {
          if (
            element.classList.contains('d4-style-u') ||
            element.classList.contains('d4-color-important')
          ) {
            return true;
          }
          element = element.parentElement;
        }
        return false;
      }

      textNodes.forEach((textNode, nodeIndex) => {
        const dynamicMatch = textNode.nodeValue.match(DYNAMIC_VALUE_TEXT);
        let value = dynamicMatch?.[1] || null;

        if (!value && isTooltipSentence && isStyledTextNode(textNode)) {
          value = applyRegexTransformations(
            textNode.nodeValue,
            regexTable
          ).trim();
        }

        if (!value) {
          return;
        }
        requiredAnchorCount++;
        let valuePosition = newText.indexOf(value);
        while (
          valuePosition >= 0 &&
          occupiedAnchorRanges.some(range =>
            valuePosition < range.end &&
            valuePosition + value.length > range.start
          )
        ) {
          valuePosition = newText.indexOf(value, valuePosition + 1);
        }
        if (valuePosition < 0) {
          return;
        }
        anchors.push({nodeIndex, value, valuePosition});
        occupiedAnchorRanges.push({
          start: valuePosition,
          end: valuePosition + value.length
        });
      });

      function writeSegment(startIndex, endIndex, value) {
        if (startIndex >= endIndex) {
          return value.length === 0;
        }
        for (let index = startIndex; index < endIndex; index++) {
          const replacement = index === startIndex ? value : '';
          if (textNodes[index].nodeValue !== replacement) {
            textNodes[index].nodeValue = replacement;
          }
        }
        return true;
      }

      // Maxroll が色分けした可変数値の Text ノードはその場に残し、
      // 数値間の文章だけを既存ノードへ格納する。
      let nodePosition = 0;
      let textPosition = 0;
      const canKeepAnchors =
        anchors.length > 0 &&
        anchors.length === requiredAnchorCount &&
        anchors.every(anchor => {
          if (anchor.valuePosition < textPosition) {
            return false;
          }
          const segment = newText.slice(textPosition, anchor.valuePosition);
          const hasRoom = segment.length === 0 || anchor.nodeIndex > nodePosition;
          nodePosition = anchor.nodeIndex + 1;
          textPosition = anchor.valuePosition + anchor.value.length;
          return hasRoom;
        }) &&
        (
          newText.slice(textPosition).length === 0 ||
          nodePosition < textNodes.length
        );

      if (canKeepAnchors) {
        nodePosition = 0;
        textPosition = 0;
        anchors.forEach(anchor => {
          writeSegment(
            nodePosition,
            anchor.nodeIndex,
            newText.slice(textPosition, anchor.valuePosition)
          );
          textNodes[anchor.nodeIndex].nodeValue = anchor.value;
          nodePosition = anchor.nodeIndex + 1;
          textPosition = anchor.valuePosition + anchor.value.length;
        });
        writeSegment(nodePosition, textNodes.length, newText.slice(textPosition));
        return true;
      }

      // 日本語化で「数値→項目名」が「項目名→数値」になる場合は、
      // Maxrollの既存spanをそのまま移動して色・下線を維持する。
      if (
        isTooltipSentence &&
        containerNode?.nodeType === 1 &&
        anchors.length > 0 &&
        anchors.length === requiredAnchorCount
      ) {
        function topLevelChild(textNode) {
          let child = textNode;
          while (child.parentNode && child.parentNode !== containerNode) {
            child = child.parentNode;
          }
          return child.parentNode === containerNode ? child : null;
        }

        const orderedAnchors = [...anchors].sort(
          (left, right) => left.valuePosition - right.valuePosition
        );
        const anchorRoots = orderedAnchors.map(anchor =>
          topLevelChild(textNodes[anchor.nodeIndex])
        );
        const supplementaryRoots = supplementaryRangeNodes
          .map(topLevelChild)
          .filter((root, index, roots) =>
            root && roots.indexOf(root) === index
          );
        const movableRoots = new Set([...anchorRoots, ...supplementaryRoots]);
        const canReorder =
          anchorRoots.every(Boolean) &&
          new Set(anchorRoots).size === anchorRoots.length &&
          Array.from(containerNode.childNodes).every(child =>
            child.nodeType === 3 ||
            movableRoots.has(child) ||
            (child.nodeType === 1 && child.textContent.trim() === '')
          );

        if (canReorder) {
          const emptyElements = Array.from(containerNode.children).filter(
            child => child.textContent.trim() === '' && !movableRoots.has(child)
          );
          const fragment = document.createDocumentFragment();
          emptyElements.forEach(element => fragment.appendChild(element));
          let outputPosition = 0;
          orderedAnchors.forEach((anchor, index) => {
            const segment = newText.slice(
              outputPosition,
              anchor.valuePosition
            );
            if (segment) {
              fragment.appendChild(document.createTextNode(segment));
            }
            textNodes[anchor.nodeIndex].nodeValue = anchor.value;
            fragment.appendChild(anchorRoots[index]);
            outputPosition = anchor.valuePosition + anchor.value.length;
          });
          const trailingText = newText.slice(outputPosition);
          if (trailingText) {
            fragment.appendChild(document.createTextNode(trailingText));
          }
          supplementaryRoots.forEach(root => fragment.appendChild(root));
          containerNode.replaceChildren(fragment);
          return true;
        }
      }

      if (isTooltipSentence && requiredAnchorCount > 0) {
        return false;
      }

      // 通常テキストは従来どおり、先頭ノードへ変換結果を格納する。
      textNodes.forEach((textNode, index) => {
        textNode.nodeValue = index === 0 ? newText : '';
      });
      return true;
    }

    function collectInlineTextNodes(
      node,
      textNodes,
      supplementaryRangeNodes = []
    ) {
      node.childNodes.forEach(child => {
        if (child.nodeType === 3) {
          textNodes.push(child);
          return;
        }
        if (
          child.nodeType !== 1 ||
          IGNORED_TEXT_TAGS.has(child.tagName) ||
          child.isContentEditable
        ) {
          return;
        }
        // Equipment の実アイテムTooltipでは、現在値の直後に
        // <span class="d4-color-inactive">[最小値 - 最大値]</span> が追加される。
        // これは原文データには存在しない補足表示なので、効果文の照合から外す。
        // span 自体はDOMに残るため、Maxrollの色・配置・数値表示は維持される。
        if (
          child.classList.contains('d4-color-inactive') &&
          (
            DYNAMIC_VALUE_TEXT.test(child.textContent) ||
            SUPPLEMENTARY_VALUE_MARKER_TEXT.test(child.textContent)
          )
        ) {
          collectInlineTextNodes(child, supplementaryRangeNodes);
          return;
        }
        collectInlineTextNodes(child, textNodes, supplementaryRangeNodes);
      });
    }

    function hasBlockBoundaryChild(node) {
      return Array.from(node.children).some(child =>
        BLOCK_BOUNDARY_TAGS.has(child.tagName)
      );
    }

    function replaceInlineRunsBetweenBlockBoundaries(
      node,
      regexTable,
      stats
    ) {
      let textNodes = [];
      let supplementaryRangeNodes = [];

      function flushRun() {
        if (textNodes.length) {
          replaceTextNodeRun(
            textNodes,
            regexTable,
            stats,
            supplementaryRangeNodes,
            node
          );
        }
        textNodes = [];
        supplementaryRangeNodes = [];
      }

      node.childNodes.forEach(child => {
        if (
          child.nodeType === 1 &&
          BLOCK_BOUNDARY_TAGS.has(child.tagName)
        ) {
          flushRun();
          return;
        }
        if (child.nodeType === 3) {
          textNodes.push(child);
          return;
        }
        if (
          child.nodeType === 1 &&
          !IGNORED_TEXT_TAGS.has(child.tagName) &&
          !child.isContentEditable
        ) {
          if (
            child.classList.contains('d4-color-inactive') &&
            (
              DYNAMIC_VALUE_TEXT.test(child.textContent) ||
              SUPPLEMENTARY_VALUE_MARKER_TEXT.test(child.textContent)
            )
          ) {
            collectInlineTextNodes(child, supplementaryRangeNodes);
            return;
          }
          collectInlineTextNodes(
            child,
            textNodes,
            supplementaryRangeNodes
          );
        }
      });
      flushRun();
    }

    function replaceText(node, regexTable, stats = {nodes: 0, attempts: 0, replacements: 0, chars: 0}) {
      if (node.nodeType === 3) {
        replaceTextNodeRun([node], regexTable, stats);
      } else if (
        node.nodeType === 1 &&
        !IGNORED_TEXT_TAGS.has(node.tagName) &&
        !node.isContentEditable
      ) {
        // Maxroll の効果文は数値や強調語ごとに span へ分割される。
        // ブロック境界を含まない要素では子孫テキストを一続きの文章として照合し、
        // 要素を作り直さず既存 Text ノードだけを書き換える。
        const hasBlockBoundary = hasBlockBoundaryChild(node);
        if (!hasBlockBoundary) {
          const inlineTextNodes = [];
          const supplementaryRangeNodes = [];
          collectInlineTextNodes(
            node,
            inlineTextNodes,
            supplementaryRangeNodes
          );
          if (inlineTextNodes.length > 1) {
            const replaced = replaceTextNodeRun(
              inlineTextNodes,
              regexTable,
              stats,
              supplementaryRangeNodes,
              node
            );
            if (replaced) {
              return stats;
            }
          }
        } else {
          // MaxrollはCSV内の改行を、同じ効果<li>内の<br>として描画する。
          // <br>間を1行として結合し、行内の装飾spanをまたいで照合する。
          replaceInlineRunsBetweenBlockBoundaries(node, regexTable, stats);
        }

        const childNodes = Array.from(node.childNodes);

        for (let index = 0; index < childNodes.length;) {
          const child = childNodes[index];
          if (child.nodeType !== 3) {
            replaceText(child, regexTable, stats);
            index++;
            continue;
          }

          const textNodes = [];
          while (index < childNodes.length && childNodes[index].nodeType === 3) {
            textNodes.push(childNodes[index]);
            index++;
          }
          replaceTextNodeRun(textNodes, regexTable, stats);
        }
      }
      return stats;
    }

    function replaceTitleAttributes(regexTable, stats = {elements: 0, replaced: 0}, root = document) {
      const elements = [];
      if (root.nodeType === 1 && root.hasAttribute('title')) {
        elements.push(root);
      }
      if (typeof root.querySelectorAll === 'function') {
        elements.push(...root.querySelectorAll('[title]'));
      }
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
        if (newTitle !== originalTitle) {
          el.setAttribute('title', newTitle);
        }
      });
      return stats;
    }

    let observeDOMTimer;

    function observeDOM(regexTable) {
      const pendingRoots = new Set();

      function scheduleTranslation(root) {
        if (!root || !root.isConnected) {
          return;
        }
        pendingRoots.add(root.nodeType === 3 ? root.parentElement : root);

        if (observeDOMTimer) clearTimeout(observeDOMTimer);
        observeDOMTimer = setTimeout(() => {
          if (!extensionEnabled) {
            pendingRoots.clear();
            return;
          }

          const roots = pendingRoots.size > DOM_CHANGE_MUTATION_THRESHOLD
            ? [document.body]
            : Array.from(pendingRoots).filter(candidate =>
                candidate && candidate.isConnected &&
                !Array.from(pendingRoots).some(other =>
                  other !== candidate &&
                  other.nodeType === 1 &&
                  other.contains(candidate)
                )
              );
          pendingRoots.clear();

          roots.forEach(root => {
            replaceText(root, regexTable);
            replaceTitleAttributes(regexTable, undefined, root);
          });
        }, DEBOUNCE_DOM_DELAY_MS);
      }

      const observer = new MutationObserver(mutations => {
        if (!extensionEnabled) {
          return;
        }
        if (D4DEBUG_DISPLAY) {
          console.log(`[D4T] Number of mutations observed: ${mutations.length}`);
        }

        mutations.forEach(mutation => {
          if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(node => {
              scheduleTranslation(node);
            });
          } else if (mutation.type === 'characterData') {
            // React はタブ切替時に要素を追加せず、既存 Text ノードだけを
            // 英語へ書き戻すことがある。親要素から再評価して分割文も連結する。
            scheduleTranslation(mutation.target.parentElement);
          } else if (mutation.type === 'attributes') {
            // 非表示の Equipment / Stat Priority パネルが表示された場合や、
            // tooltip の title が後から設定された場合も対象にする。
            scheduleTranslation(mutation.target);
          }
        });
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['hidden', 'class', 'aria-selected', 'data-state', 'title']
      });
      if (D4DEBUG_DISPLAY) console.log('[D4T] MutationObserver started'); // デバッグ用ログ
    }

    function applyTranslations() {
      if (!extensionEnabled) {
        return;
      }
      if (D4DEBUG_DISPLAY) console.log('[D4T] applyTranslations started'); // デバッグ用ログ
      const startTime = performance.now();
      loadTranslations().then(regexTable => {
        if (!extensionEnabled) {
          return;
        }
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
        if (!extensionEnabled) {
          return;
        }
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
      if (message.action === 'convert' && extensionEnabled) {
        if (D4DEBUG_DISPLAY) console.log('[D4T] Manual convert triggered'); // デバッグ用ログ
        applyTranslations();
      }
    });

  } else {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Extension is disabled');
  }
});
