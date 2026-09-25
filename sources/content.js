// デバッグログの出力を切り替える変数
const D4DEBUG_DISPLAY = false;
// 初期化時変換をするまでのデバウンス待機時間(ms)
const DEBOUNCE_DELAY_MS = 1000;
// DOM変化時のデバウンス遅延時間を定義
const DEBOUNCE_DOM_DELAY_MS = 100;
let extensionEnabled = false;
let guideTranslationEnabled = true;

const BLOCK_BOUNDARY_TAGS = new Set([
  'ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 'BR', 'DIV', 'DL', 'DT', 'DD',
  'FIELDSET', 'FIGCAPTION', 'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3',
  'H4', 'H5', 'H6', 'HEADER', 'HR', 'LI', 'MAIN', 'NAV', 'OL', 'P', 'PRE',
  'SECTION', 'TABLE', 'TBODY', 'TD', 'TFOOT', 'TH', 'THEAD', 'TR', 'UL'
]);
const IGNORED_TEXT_TAGS = new Set([
  'SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'CANVAS',
  'IFRAME', 'OBJECT'
]);
const DYNAMIC_VALUE_TEXT = /^\s*[\(（]?(\[?[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?(?:\s*[-–]\s*[+-]?(?:\d+(?:,\d{3})*|\.\d+)(?:\.\d+)?)?\]?(?:%\[(?:x|\+)\]|%x|x%|%|x|\+)?)[\)）]?\s*$/;
const DYNAMIC_ORDINAL_TEXT = /^\s*(\d+)(?:st|nd|rd|th)\s*$/i;
const SUPPLEMENTARY_VALUE_MARKER_TEXT =
  /^\s*\[(?:x|\+|HP|Damage)\]\s*$/i;
const MAXROLL_DAMAGE_ANNOTATION_TEXT =
  /^\s*(?:x\s*)?\[[^\]\r\n]+\]\s*$/i;
const PARAGON_CONDITIONAL_BONUS_TEXT =
  /^\s*Bonus:\s*Another\b[\s\S]*\bif\s+requirements\s+met:?\s*$/i;
const PARAGON_ATTRIBUTE_REQUIREMENT_TEXT =
  /^\s*(?:[◆♦•·]\s*)?(?:Required(?:\s*\([^)]*\))?:\s*)?[+-]?\d[\d,.]*\s*\/[\s\S]*\b(?:Strength|Intelligence|Willpower|Dexterity)\b/i;
const LONG_TEXT_TOOLTIP_SELECTOR =
  '.d4t-GameTooltip, .d4t-SkillTagTooltip';
const SKILL_TOOLTIP_SELECTOR = [
  '.d4t-SkillTagTooltip',
  '.d4t-tip-skill' +
    ':not(.d4t-tip-common)' +
    ':not(.d4t-tip-magic)' +
    ':not(.d4t-tip-rare)' +
    ':not(.d4t-tip-legendary)'
].join(', ');
const DROP_SOURCE_ITEM_SELECTOR = '.d4t-source li';
const DROP_SOURCE_KEY_PREFIX = '__D4T_DROP_SOURCE__:';
const MAXROLL_GUIDE_ROOT_SELECTOR = '#main-article, main article';
const MAXROLL_INTERACTIVE_PARAGON_SELECTOR =
  '[class*="_D4PlannerPageParagon__embed_"]';
// パラゴン章の説明文はChrome Translator APIで翻訳し、
// 大量のDOM更新が発生するボード描画領域だけをAPI翻訳から除外する。
const MAXROLL_CHROME_TRANSLATION_EXCLUDED_SELECTOR =
  MAXROLL_INTERACTIVE_PARAGON_SELECTOR;
const MAXROLL_GUIDE_BLOCK_SELECTOR = [
  'main article h1',
  '.maxroll-rich-text-editor p',
  '.maxroll-rich-text-editor li',
  '.maxroll-rich-text-editor :is(h1, h2, h3, h4, h5, h6) strong',
  '.maxroll-rich-text-editor ' +
    ':is(h1, h2, h3, h4, h5, h6) > span:not(:has(strong, em))',
  '.maxroll-rich-text-editor ' +
    ':is(h1, h2, h3, h4, h5, h6):not(:has(span, strong, em))',
  '.maxroll-rich-text-editor blockquote',
  '.maxroll-rich-text-editor figcaption',
  '.maxroll-rich-text-editor td',
  '.maxroll-rich-text-editor th',
  '[class*="_PlannerPageSection__content_"] > div > p',
  '[id$="-header"] > [class*="_PlannerPageSectionHeading__title_"]',
  '[class*="_PostTopSection__gameVersion_"]',
  '[class*="_StrAndWeak__blockListItemText_"]',
  '[class*="_D4PlannerPageLevelingPostList__header_"]',
  '[class*="_D4PlannerPageQuote_"]',
  '[class*="_ArticleAccordion__itemHeaderTitle_"] ' +
    '.maxroll-rich-text-editor > div > span',
  '[class*="_ArticleChangelog__itemHeaderTitle_"] ' +
    '.maxroll-rich-text-editor > div > span'
].join(', ');
const GUIDE_TOKEN_PATTERN = /ZXQJ\d{4}QJQXZ/g;
const GUIDE_TOKEN_PADDED_PATTERN = /\s*(ZXQJ\d{4}QJQXZ)\s*/g;
const GUIDE_TRANSLATION_MAX_ATTEMPTS = 2;
const MAX_PENDING_GUIDE_ROOTS = 256;
const MAX_CACHED_TRANSLATION_REGEXES = 4096;

// popup で状態が変わったら、開いているすべての対象タブへ即時反映する。
// OFF時はリロードによって既に変換済みのDOMも元の表示へ戻す。
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (
    areaName !== 'sync' ||
    (!changes.enabled && !changes.guideTranslationEnabled)
  ) {
    return;
  }

  extensionEnabled = changes.enabled
    ? changes.enabled.newValue === true
    : extensionEnabled;
  guideTranslationEnabled = changes.guideTranslationEnabled
    ? changes.guideTranslationEnabled.newValue !== false
    : guideTranslationEnabled;
  window.location.reload();
});

chrome.storage.sync.get(
  ['enabled', 'guideTranslationEnabled'],
  function(result) {
  if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded extension state:', result.enabled); // デバッグ用ログ
  extensionEnabled = result.enabled === true;
  guideTranslationEnabled = result.guideTranslationEnabled !== false;
  if (extensionEnabled) {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Content script loaded'); // デバッグ用ログ

    let dropSourceTranslations = new Map();
    let compiledPatterns = null;    // 通常の短い正規表現パターン
    let compiledWholeSentencePatterns = null; // Tooltip内だけで使う長文パターン
    let compiledPatternIndex = null;
    let compiledWholeSentencePatternIndex = null;
    let activeRegexTable = null;
    let domObserverStarted = false;
    let translationsLoadPromise = null;
    const translationRegexCache = new Map();

    function getWildcardCaptureIndexes(sourcePattern) {
      const indexes = [];
      let captureIndex = 0;
      let inCharacterClass = false;
      for (let index = 0; index < sourcePattern.length; index++) {
        const character = sourcePattern[index];
        if (character === '\\') { index++; continue; }
        if (character === '[') { inCharacterClass = true; continue; }
        if (character === ']') { inCharacterClass = false; continue; }
        if (inCharacterClass || character !== '(') continue;
        if (sourcePattern[index + 1] === '?') {
          if (sourcePattern[index + 2] !== '<' || /[=!]/.test(sourcePattern[index + 3])) continue;
        }
        captureIndex++;
        if (sourcePattern.startsWith('(.*?)', index)) indexes.push(captureIndex);
      }
      return indexes;
    }

    function hasUnsafeWildcardMatch(text, regex, captureIndexes) {
      if (!captureIndexes.length) return false;
      // 汎用の項目名キャプチャが別の文や翻訳済みテキストまで飲み込むと、
      // 数値の移動・再変換が起きる。数値内の「4,375」は許容する。
      regex.lastIndex = 0;
      for (const match of text.matchAll(regex)) {
        if (captureIndexes.some(index => /[\u3040-\u30ff\u3400-\u9fff]|[,;!?]\s|\.\s/.test(match[index] || ''))) {
          return true;
        }
      }
      return false;
    }

    function createTranslationRegex(pattern) {
      // Maxroll側のタイポグラフィ変換でASCIIの'が’になる場合も照合する。
      const escapedPattern = pattern.replace(/['’]/g, "['’]");
      const leadingBoundary = /^[A-Za-z0-9_]/.test(pattern) ? '\\b' : '';
      const trailingBoundary = /[A-Za-z0-9_]$/.test(pattern) ? '\\b' : '';
      // 空白なしで連結されたルーン名の補助規則はCamelCase境界を使う。
      // Unique末尾の"que"などを誤変換しないよう、この規則だけ大小を区別する。
      const isConcatenatedRunePattern =
        pattern.includes('(?=[A-Z])') ||
        pattern.includes('(?<=[a-z])');
      const flags = isConcatenatedRunePattern ? 'g' : 'gi';
      return new RegExp(
        `${leadingBoundary}${escapedPattern}${trailingBoundary}`,
        flags
      );
    }

    function getTranslationRegex(pattern) {
      const cached = translationRegexCache.get(pattern);
      if (cached) {
        // 挿入順を更新し、上限制キャッシュをLRUとして動作させる。
        translationRegexCache.delete(pattern);
        translationRegexCache.set(pattern, cached);
        return cached;
      }

      const regex = createTranslationRegex(pattern);
      translationRegexCache.set(pattern, regex);
      if (translationRegexCache.size > MAX_CACHED_TRANSLATION_REGEXES) {
        translationRegexCache.delete(
          translationRegexCache.keys().next().value
        );
      }
      return regex;
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
            translationRegexCache.clear();
            dropSourceTranslations = new Map();
            const translationEntries = [];
            Object.entries(data).forEach(([pattern, replacement]) => {
              if (pattern.startsWith(DROP_SOURCE_KEY_PREFIX)) {
                const bossName = pattern.slice(DROP_SOURCE_KEY_PREFIX.length);
                dropSourceTranslations.set(
                  bossName.toLocaleLowerCase('en-US'),
                  replacement
                );
                return;
              }
              translationEntries.push([pattern, replacement]);
            });

            // 正規表現のメタデータ配列を初期化（RegExp自体は必要時に生成）
            compiledPatterns = [];
            compiledWholeSentencePatterns = [];

            // キーの長さが長い順に並び替える（長いフレーズを優先的に処理）
            const wildcardCount = pattern =>
              (pattern.match(/\(\.\*\?\)/g) || []).length;
            const sortedEntries = translationEntries.sort(
              ([leftPattern], [rightPattern]) => {
                const wildcardDifference =
                  wildcardCount(leftPattern) - wildcardCount(rightPattern);
                return (
                  wildcardDifference ||
                  rightPattern.length - leftPattern.length
                );
              }
            );

            // すべてのパターンを事前にコンパイル
            sortedEntries.forEach(([pattern, replacement]) => {
              const paragonRequirementPattern =
                pattern.includes('\\s*/\\s*') &&
                /(?:Strength|Intelligence|Willpower|Dexterity)/i.test(pattern);
              const wholeSentence =
                paragonRequirementPattern ||
                (
                  pattern.includes('\\s+') &&
                  (
                    pattern.includes('\\.') ||
                    pattern.includes(':') ||
                    pattern.length >= 80
                  )
              );
              const compiledPattern = {
                // RegExpは元のパターン文字列より数倍多くメモリを使う場合がある。
                // 現在のページに索引語が現れたルールだけをコンパイルする。
                replacement,
                wholeSentence,
                wildcardCaptureIndexes: pattern.includes('(.*?)')
                  ? getWildcardCaptureIndexes(pattern) : [],
                sourcePattern: pattern,
                order: 0,
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

            compiledPatterns.forEach((pattern, order) => {
              pattern.order = order;
            });
            compiledWholeSentencePatterns.forEach((pattern, order) => {
              pattern.order = order;
            });
            compiledPatternIndex = buildCompiledPatternIndex(compiledPatterns);
            compiledWholeSentencePatternIndex = buildCompiledPatternIndex(
              compiledWholeSentencePatterns
            );
            
            if (D4DEBUG_DISPLAY) {
              console.log('[D4T] Loaded translation table:', {
                patterns: compiledPatterns.length,
                tooltipPatterns: compiledWholeSentencePatterns.length,
                dropSources: dropSourceTranslations.size
              });
            }
            
            // 上の最適化済みテーブルだけを正規表現ルールの保持元にする。
            // 呼び出し側との互換性を保ちつつ、完全なRegExpテーブルを
            // もう一組保持しないようにする。
            return compiledPatterns;
          });
    }

    function buildCompiledPatternIndex(patterns) {
      const byFirstWord = new Map();
      const unindexed = [];

      function findTopLevelLiteralWord(sourcePattern) {
        let groupDepth = 0;
        let inCharacterClass = false;
        let literalMatch = null;

        for (let index = 0; index < sourcePattern.length; index++) {
          const character = sourcePattern[index];
          if (character === '\\') {
            index++;
            continue;
          }
          if (character === '[') {
            inCharacterClass = true;
            continue;
          }
          if (character === ']' && inCharacterClass) {
            inCharacterClass = false;
            continue;
          }
          if (inCharacterClass) {
            continue;
          }
          if (character === '(') {
            groupDepth++;
            continue;
          }
          if (character === ')') {
            groupDepth = Math.max(0, groupDepth - 1);
            continue;
          }
          if (character === '|' && groupDepth === 0) {
            // 最上位の選択肢では片側の単語が必ず現れるとは限らないため、
            // このパターンは安全側の全件候補に残す。
            return null;
          }
          if (groupDepth !== 0 || !/[A-Za-z0-9_]/.test(character)) {
            continue;
          }

          const match = sourcePattern.slice(index).match(
            /^([A-Za-z0-9_]{2,})/
          );
          if (match && !literalMatch) {
            literalMatch = match;
            index += match[1].length - 1;
          }
        }
        return literalMatch;
      }

      patterns.forEach(pattern => {
        // 先頭またはトップレベルの通常単語は、この正規表現が一致する際に
        // 必ず含まれる。安全な必須語を抽出できない規則だけ全件候補に残す。
        const match =
          pattern.sourcePattern.match(/^([A-Za-z0-9_]{2,})/) ||
          findTopLevelLiteralWord(pattern.sourcePattern);
        if (!match) {
          unindexed.push(pattern);
          return;
        }
        const key = match[1].toLocaleLowerCase('en-US');
        const bucket = byFirstWord.get(key) || [];
        bucket.push(pattern);
        byFirstWord.set(key, bucket);
      });

      return {byFirstWord, unindexed};
    }

    function selectCompiledPatterns(text, patterns, patternIndex) {
      if (!/[A-Za-z]/.test(text)) {
        return [];
      }
      if (!patternIndex) {
        return patterns;
      }

      const candidates = new Set(patternIndex.unindexed);
      const words = text.match(/[A-Za-z0-9_]+/g) || [];
      words.forEach(word => {
        const bucket = patternIndex.byFirstWord.get(
          word.toLocaleLowerCase('en-US')
        );
        bucket?.forEach(pattern => candidates.add(pattern));
      });
      return Array.from(candidates).sort(
        (left, right) => left.order - right.order
      );
    }

    // 最適化された変換処理関数
    function applyCompiledPatternList(
      text,
      patterns,
      patternIndex,
      stats,
      matchInfo
    ) {
      const textLength = text.length;
      let candidates = selectCompiledPatterns(
        text,
        patterns,
        patternIndex
      );

      if (patterns === compiledWholeSentencePatterns) {
        // 数値用の正規表現は長くても、実際には「3 seconds.」だけに
        // 一致することがある。全文より先に末尾だけを翻訳しないよう、
        // Tooltip候補は実際の一致長で比較する。汎用captureの優先順位は維持。
        candidates = candidates.map(pattern => {
          const regex = getTranslationRegex(pattern.sourcePattern);
          regex.lastIndex = 0;
          let matchedLength = 0;
          for (const match of text.matchAll(regex)) {
            matchedLength = Math.max(matchedLength, match[0].length);
          }
          return {pattern, matchedLength};
        }).filter(candidate => candidate.matchedLength > 0).sort((left, right) =>
          left.pattern.wildcardCaptureIndexes.length -
            right.pattern.wildcardCaptureIndexes.length ||
          right.matchedLength - left.matchedLength ||
          left.pattern.order - right.pattern.order
        ).map(candidate => candidate.pattern);
      }

      for (const pattern of candidates) {
        const {replacement, minLength, wholeSentence} = pattern;
        if (minLength <= textLength) {
          if (stats) stats.attempts++;
          const regex = getTranslationRegex(pattern.sourcePattern);
          if (hasUnsafeWildcardMatch(text, regex, pattern.wildcardCaptureIndexes)) {
            continue;
          }
          const newText = text.replace(regex, replacement);
          if (newText !== text) {
            text = newText;
            if (stats) stats.replacements++;
            if (matchInfo && wholeSentence) {
              matchInfo.wholeSentence = true;
            }
            if (wholeSentence && matchInfo?.stopAfterWholeSentence) {
              return text;
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
          compiledWholeSentencePatternIndex,
          stats,
          matchInfo
        );
        if (
          matchInfo?.wholeSentence &&
          matchInfo.stopAfterWholeSentence
        ) {
          return text;
        }
      }
      return applyCompiledPatternList(
        text,
        compiledPatterns,
        compiledPatternIndex,
        stats,
        matchInfo
      );
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

    const guideBlockRecords = new WeakMap();
    const pendingGuideRoots = new Set();
    let guideTranslationQueue = Promise.resolve();
    let guideTranslationQueued = false;
    let guideTranslatorAvailability = null;
    let guideTranslationSuspended = false;
    let guideIntersectionObserver = null;
    const pendingGuideViewportBlocks = new Set();
    let guideScrollTimer = null;
    let guideScrollListenerStarted = false;

    function createGuideTokenAllocator(sourceText) {
      GUIDE_TOKEN_PATTERN.lastIndex = 0;
      if (GUIDE_TOKEN_PATTERN.test(sourceText)) {
        GUIDE_TOKEN_PATTERN.lastIndex = 0;
        return null;
      }
      GUIDE_TOKEN_PATTERN.lastIndex = 0;

      let nextTokenId = 0;
      const tokens = new Map();
      return {
        tokens,
        allocate(payload) {
          if (nextTokenId > 9999) {
            throw new RangeError('Maxroll guide block has too many tokens');
          }
          const token =
            `ZXQJ${String(nextTokenId++).padStart(4, '0')}QJQXZ`;
          tokens.set(token, payload);
          return token;
        }
      };
    }

    function forEachGuideTextPart(text, callback) {
      GUIDE_TOKEN_PATTERN.lastIndex = 0;
      let cursor = 0;
      for (const match of text.matchAll(GUIDE_TOKEN_PATTERN)) {
        if (match.index > cursor) {
          callback({type: 'text', value: text.slice(cursor, match.index)});
        }
        callback({type: 'token', value: match[0]});
        cursor = match.index + match[0].length;
      }
      if (cursor < text.length) {
        callback({type: 'text', value: text.slice(cursor)});
      }
      GUIDE_TOKEN_PATTERN.lastIndex = 0;
    }

    function applyGuideDictionary(text, regexTable) {
      let result = '';
      forEachGuideTextPart(text, part => {
        result += part.type === 'token'
          ? part.value
          : applyRegexTransformations(part.value, regexTable);
      });
      return result;
    }

    function prepareGuideTranslationInput(text) {
      return text.replace(GUIDE_TOKEN_PATTERN, token => ` ${token} `);
    }

    function normalizeGuideTranslationTokens(text) {
      return text.replace(
        GUIDE_TOKEN_PADDED_PATTERN,
        (match, token) => token
      );
    }

    function isMaxrollGuideNode(node) {
      const element = node?.nodeType === 3 ? node.parentElement : node;
      return Boolean(
        element?.nodeType === 1 &&
        element.closest(MAXROLL_GUIDE_BLOCK_SELECTOR)
      );
    }

    function isD4SemanticElement(element) {
      return (
        element.hasAttribute('data-d4-id') ||
        Array.from(element.classList).some(className =>
          className === 'd4-tag' || className.startsWith('d4-')
        )
      );
    }

    function isAtomicGuideElement(element) {
      return (
        isD4SemanticElement(element) ||
        ['BR', 'IMG', 'SVG', 'VIDEO', 'AUDIO', 'CANVAS'].includes(
          element.tagName
        )
      );
    }

    function shouldKeepGuideWrapper(element) {
      if (element.tagName !== 'SPAN') {
        return true;
      }
      return (
        element.attributes.length > 0 ||
        element.classList.length > 0
      );
    }

    function setElementTextPreservingMarkup(element, value) {
      if (!value || ['BR', 'IMG', 'SVG'].includes(element.tagName)) {
        return;
      }

      const textNodes = [];
      function collectTextNodes(node) {
        node.childNodes.forEach(child => {
          if (child.nodeType === 3) {
            textNodes.push(child);
            return;
          }
          if (
            child.nodeType !== 1 ||
            ['SCRIPT', 'STYLE', 'SVG'].includes(child.tagName)
          ) {
            return;
          }
          collectTextNodes(child);
        });
      }
      collectTextNodes(element);

      if (!textNodes.length) {
        element.appendChild(document.createTextNode(value));
        return;
      }
      textNodes.forEach((textNode, index) => {
        textNode.nodeValue = index === 0 ? value : '';
      });
    }

    function translateGuideSemanticElements(block, regexTable) {
      const semanticElements = [];
      if (isD4SemanticElement(block)) {
        semanticElements.push(block);
      }
      block.querySelectorAll?.('[data-d4-id], .d4-tag')
        .forEach(element => semanticElements.push(element));

      semanticElements.forEach(element => {
        const originalLabel = element.textContent;
        const translatedLabel = applyRegexTransformations(
          originalLabel,
          regexTable
        );
        if (translatedLabel !== originalLabel) {
          setElementTextPreservingMarkup(element, translatedLabel);
        }
      });
    }

    async function translateGuideTextNodesInPlace(block, regexTable) {
      const textNodes = [];

      function collect(node) {
        node.childNodes.forEach(child => {
          if (child.nodeType === 3) {
            if (/[A-Za-z]{2}/.test(child.nodeValue)) {
              textNodes.push(child);
            }
            return;
          }
          if (
            child.nodeType !== 1 ||
            IGNORED_TEXT_TAGS.has(child.tagName) ||
            isD4SemanticElement(child)
          ) {
            return;
          }
          collect(child);
        });
      }
      collect(block);

      const replacements = [];
      for (const textNode of textNodes) {
        const response = await sendBackgroundMessage({
          action: 'translateText',
          text: textNode.nodeValue
        });
        if (!response.ok) {
          return false;
        }
        replacements.push([
          textNode,
          applyRegexTransformations(response.text, regexTable)
        ]);
      }

      replacements.forEach(([textNode, value]) => {
        textNode.nodeValue = value;
      });
      translateGuideSemanticElements(block, regexTable);
      return replacements.length > 0;
    }

    function prepareGuideBlock(block, regexTable) {
      const originalText = block.textContent;
      const allocator = createGuideTokenAllocator(originalText);
      if (!allocator) {
        return null;
      }

      let source = '';

      function serializeNode(node) {
        if (node.nodeType === 3) {
          source += node.nodeValue;
          return;
        }
        if (
          node.nodeType !== 1 ||
          IGNORED_TEXT_TAGS.has(node.tagName)
        ) {
          return;
        }

        if (isAtomicGuideElement(node)) {
          const label = node.textContent
            ? applyRegexTransformations(node.textContent, regexTable)
            : '';
          source += allocator.allocate({
            type: 'node',
            node,
            label
          });
          return;
        }

        if (shouldKeepGuideWrapper(node)) {
          const openToken = allocator.allocate({
            type: 'open',
            node
          });
          const closeToken = allocator.allocate({
            type: 'close',
            node
          });
          source += openToken;
          node.childNodes.forEach(serializeNode);
          source += closeToken;
          return;
        }

        node.childNodes.forEach(serializeNode);
      }

      block.childNodes.forEach(serializeNode);

      return {
        source,
        tokens: allocator.tokens,
        status: 'prepared',
        renderedText: null
      };
    }

    function validateGuideTranslation(text, tokens) {
      const counts = new Map(
        Array.from(tokens.keys(), token => [token, 0])
      );
      const wrapperStack = [];
      let valid = true;

      forEachGuideTextPart(text, part => {
        if (part.type !== 'token') {
          return;
        }
        const payload = tokens.get(part.value);
        if (!payload) {
          valid = false;
          return;
        }
        counts.set(part.value, counts.get(part.value) + 1);

        if (payload.type === 'open') {
          wrapperStack.push(payload.node);
        } else if (payload.type === 'close') {
          if (
            !wrapperStack.length ||
            wrapperStack.pop() !== payload.node
          ) {
            valid = false;
          }
        }
      });

      return (
        valid &&
        wrapperStack.length === 0 &&
        Array.from(counts.values()).every(count => count === 1)
      );
    }

    function renderGuideBlock(block, text, tokens) {
      if (!validateGuideTranslation(text, tokens)) {
        return false;
      }

      const rootFragment = document.createDocumentFragment();
      const stack = [{fragment: rootFragment, node: null}];
      let plainText = '';

      function currentFragment() {
        return stack[stack.length - 1].fragment;
      }

      function flushPlainText() {
        if (plainText) {
          currentFragment().appendChild(
            document.createTextNode(plainText)
          );
          plainText = '';
        }
      }

      forEachGuideTextPart(text, part => {
        if (part.type !== 'token') {
          plainText += part.value;
          return;
        }

        flushPlainText();
        const payload = tokens.get(part.value);
        if (payload.type === 'node') {
          setElementTextPreservingMarkup(payload.node, payload.label);
          currentFragment().appendChild(payload.node);
        } else if (payload.type === 'open') {
          stack.push({
            fragment: document.createDocumentFragment(),
            node: payload.node
          });
        } else if (payload.type === 'close') {
          const wrapper = stack.pop();
          wrapper.node.replaceChildren(wrapper.fragment);
          currentFragment().appendChild(wrapper.node);
        }
      });
      flushPlainText();

      if (stack.length !== 1) {
        return false;
      }
      block.replaceChildren(rootFragment);
      return true;
    }

    function sendBackgroundMessage(message) {
      return new Promise(resolve => {
        chrome.runtime.sendMessage(
          {...message, target: 'background'},
          response => {
            if (chrome.runtime.lastError) {
              resolve({
                ok: false,
                error: chrome.runtime.lastError.message
              });
              return;
            }
            resolve(response || {ok: false, error: 'No response'});
          }
        );
      });
    }

    function isVisibleGuideBlock(block) {
      let element = block;
      while (element && element !== document.documentElement) {
        if (
          element.hidden ||
          getComputedStyle(element).display === 'none' ||
          getComputedStyle(element).visibility === 'hidden'
        ) {
          return false;
        }
        element = element.parentElement;
      }
      return true;
    }

    function collectGuideBlocks(root, visibleOnly = true) {
      const element = root?.nodeType === 3 ? root.parentElement : root;
      if (!element) {
        return [];
      }

      const blocks = new Set();
      const articles = new Set();
      const elementIsDocument = element.nodeType === 9;

      if (!elementIsDocument && element.nodeType === 1) {
        const closestBlock = element.closest?.(
          MAXROLL_GUIDE_BLOCK_SELECTOR
        );
        if (closestBlock) {
          blocks.add(closestBlock);
        }
        if (element.matches?.(MAXROLL_GUIDE_BLOCK_SELECTOR)) {
          blocks.add(element);
        }

        const closestArticle = element.closest?.(
          MAXROLL_GUIDE_ROOT_SELECTOR
        );
        if (!closestArticle) {
          element.querySelectorAll?.(MAXROLL_GUIDE_ROOT_SELECTOR)
            .forEach(article => articles.add(article));
        } else if (!closestBlock) {
          element.querySelectorAll?.(MAXROLL_GUIDE_BLOCK_SELECTOR)
            .forEach(block => blocks.add(block));
        }
      } else {
        element.querySelectorAll?.(MAXROLL_GUIDE_ROOT_SELECTOR)
          .forEach(article => articles.add(article));
      }

      articles.forEach(article => {
        article.querySelectorAll(MAXROLL_GUIDE_BLOCK_SELECTOR)
          .forEach(block => blocks.add(block));
      });

      return Array.from(blocks).filter(block =>
        !block.querySelector(MAXROLL_GUIDE_BLOCK_SELECTOR) &&
        !block.closest(MAXROLL_CHROME_TRANSLATION_EXCLUDED_SELECTOR) &&
        (!visibleOnly || isVisibleGuideBlock(block)) &&
        block.textContent.trim()
      );
    }

    async function processMaxrollGuideRoot(root, regexTable) {
      const blocks = collectGuideBlocks(root);
      if (!blocks.length) {
        return;
      }

      let translatorAvailable = false;
      if (guideTranslationEnabled && !guideTranslationSuspended) {
        if (guideTranslatorAvailability === null) {
          const response = await sendBackgroundMessage({
            action: 'translatorAvailability'
          });
          guideTranslatorAvailability = response.ok
            ? response.availability
            : 'error';
        }
        translatorAvailable =
          guideTranslatorAvailability === 'available';
      }

      for (const block of blocks) {
        if (!block.isConnected) {
          continue;
        }

        let record = guideBlockRecords.get(block);
        if (
          record &&
          record.renderedText !== null &&
          block.textContent !== record.renderedText
        ) {
          guideBlockRecords.delete(block);
          record = null;
        }
        if (!record) {
          record = prepareGuideBlock(block, regexTable);
          if (!record) {
            continue;
          }
          record.attempts = 0;
          guideBlockRecords.set(block, record);
        }

        if (record.status === 'translated') {
          continue;
        }
        if (
          record.status === 'fallback' &&
          record.attempts >= GUIDE_TRANSLATION_MAX_ATTEMPTS
        ) {
          continue;
        }
        if (
          record.status === 'dictionary' &&
          !translatorAvailable
        ) {
          continue;
        }

        let output = record.source;
        let nextStatus = 'dictionary';
        const hasEnglishText = /[A-Za-z]{2}/.test(
          record.source.replace(GUIDE_TOKEN_PATTERN, '')
        );
        if (D4DEBUG_DISPLAY) {
          console.log('[D4T] Guide block prepared', {
            source: record.source,
            translatorAvailable,
            guideTranslationEnabled,
            hasEnglishText
          });
        }

        if (
          translatorAvailable &&
          guideTranslationEnabled &&
          hasEnglishText
        ) {
          record.attempts++;
          const response = await sendBackgroundMessage({
            action: 'translateText',
            text: prepareGuideTranslationInput(record.source)
          });
          if (response.ok) {
            response.text = normalizeGuideTranslationTokens(
              response.text
            );
          }
          if (
            response.ok &&
            record.tokens.size > 0 &&
            !validateGuideTranslation(response.text, record.tokens)
          ) {
            const translatedInPlace =
              await translateGuideTextNodesInPlace(block, regexTable);
            if (translatedInPlace) {
              record.status = 'translated';
              record.renderedText = block.textContent;
              continue;
            }
          }
          if (
            response.ok &&
            validateGuideTranslation(response.text, record.tokens)
          ) {
            output = response.text;
            nextStatus = 'translated';
          } else if (response.ok) {
            // 保護トークンが欠落・重複・破損した場合は、DOMを壊さず
            // 辞書変換だけを表示し、上限回数まで再評価する。
            nextStatus = 'fallback';
          } else {
            translatorAvailable = false;
            guideTranslatorAvailability = null;
            nextStatus = 'fallback';
          }
        }

        output = applyGuideDictionary(output, regexTable);

        if (
          block.isConnected &&
          renderGuideBlock(block, output, record.tokens)
        ) {
          record.status = nextStatus;
          record.renderedText = block.textContent;
        }
      }
    }

    function queueMaxrollGuideTranslation(root, regexTable) {
      if (!root || (root.nodeType !== 9 && !root.isConnected)) {
        return;
      }
      const element = root.nodeType === 3 ? root.parentElement : root;
      const queueRoot =
        element?.closest?.(MAXROLL_GUIDE_BLOCK_SELECTOR) || root;

      // オンデバイス翻訳の待機中もReactはガイド断片を頻繁に置き換える。
      // 切断済みの部分木をこのキューから強参照し続けないようにする。
      pendingGuideRoots.forEach(pendingRoot => {
        if (pendingRoot.nodeType !== 9 && !pendingRoot.isConnected) {
          pendingGuideRoots.delete(pendingRoot);
        }
      });
      pendingGuideRoots.add(queueRoot);
      while (pendingGuideRoots.size > MAX_PENDING_GUIDE_ROOTS) {
        pendingGuideRoots.delete(pendingGuideRoots.values().next().value);
      }
      if (guideTranslationQueued) {
        return;
      }

      guideTranslationQueued = true;
      guideTranslationQueue = guideTranslationQueue
        .then(async () => {
          while (pendingGuideRoots.size > 0) {
            const roots = Array.from(pendingGuideRoots);
            pendingGuideRoots.clear();
            for (const pendingRoot of roots) {
              await processMaxrollGuideRoot(
                pendingRoot,
                regexTable
              );
            }
          }
        })
        .catch(error => {
          console.error('[D4T] Maxroll guide translation failed:', error);
        })
        .finally(() => {
          guideTranslationQueued = false;
          if (pendingGuideRoots.size > 0) {
            queueMaxrollGuideTranslation(
              pendingGuideRoots.values().next().value,
              regexTable
            );
          }
        });
    }

    function observeMaxrollGuideBlocks(root, regexTable) {
      const guideBlocks = collectGuideBlocks(root, false);

      // ゲーム用語は辞書だけで確定できるため、解説文全体の機械翻訳を待たず
      // 検出した全ブロックへ即時反映する。
      guideBlocks.forEach(block => {
        translateGuideSemanticElements(block, regexTable);
      });

      if (!guideTranslationEnabled || !('IntersectionObserver' in window)) {
        queueMaxrollGuideTranslation(root, regexTable);
        return;
      }

      function queueBlockIfNearViewport(block) {
        if (!block.isConnected) {
          pendingGuideViewportBlocks.delete(block);
          guideIntersectionObserver?.unobserve(block);
          return true;
        }
        const record = guideBlockRecords.get(block);
        if (
          record?.status === 'translated' ||
          (
            record?.status === 'fallback' &&
            record.attempts >= GUIDE_TRANSLATION_MAX_ATTEMPTS
          )
        ) {
          pendingGuideViewportBlocks.delete(block);
          guideIntersectionObserver?.unobserve(block);
          return true;
        }

        const bounds = block.getBoundingClientRect();
        const nearViewport =
          isVisibleGuideBlock(block) &&
          bounds.bottom >= -1200 &&
          bounds.top <= window.innerHeight + 1200;
        if (!nearViewport) {
          return false;
        }

        pendingGuideViewportBlocks.delete(block);
        guideIntersectionObserver?.unobserve(block);
        queueMaxrollGuideTranslation(block, regexTable);
        return true;
      }

      if (!guideIntersectionObserver) {
        guideIntersectionObserver = new IntersectionObserver(entries => {
          entries.forEach(entry => {
            if (!entry.isIntersecting) {
              return;
            }
            pendingGuideViewportBlocks.delete(entry.target);
            guideIntersectionObserver.unobserve(entry.target);
            queueMaxrollGuideTranslation(entry.target, regexTable);
          });
        }, {
          rootMargin: '1200px 0px'
        });
      }

      if (!guideScrollListenerStarted) {
        guideScrollListenerStarted = true;
        window.addEventListener('scroll', () => {
          if (guideScrollTimer) {
            clearTimeout(guideScrollTimer);
          }
          guideScrollTimer = setTimeout(() => {
            guideScrollTimer = null;
            pendingGuideViewportBlocks.forEach(queueBlockIfNearViewport);
          }, 150);
        }, {passive: true});
      }

      guideBlocks.forEach(block => {
        if (queueBlockIfNearViewport(block)) {
          return;
        }
        pendingGuideViewportBlocks.add(block);
        guideIntersectionObserver.observe(block);
      });

      pendingGuideViewportBlocks.forEach(block => {
        if (!block.isConnected) {
          pendingGuideViewportBlocks.delete(block);
          guideIntersectionObserver.unobserve(block);
        }
      });
    }

    function replaceTextNodeRun(
      textNodes,
      regexTable,
      stats,
      supplementaryRangeNodes = [],
      containerNode = null,
      runTopLevelNodes = [],
      trailingPunctuationNode = null
    ) {
      const originalText = textNodes.map(textNode => textNode.nodeValue).join('') +
        (trailingPunctuationNode?.nodeValue || '');
      function finishReplacement() {
        if (trailingPunctuationNode) trailingPunctuationNode.nodeValue = '';
        return true;
      }
      stats.nodes += textNodes.length;
      stats.chars += originalText.length;

      const tooltipContainer =
        containerNode?.nodeType === 1
          ? containerNode.closest(LONG_TEXT_TOOLTIP_SELECTOR)
          : textNodes[0]?.parentElement?.closest(LONG_TEXT_TOOLTIP_SELECTOR);
      const matchInfo = {
        wholeSentence: false,
        stopAfterWholeSentence: Boolean(
          tooltipContainer?.matches(SKILL_TOOLTIP_SELECTOR)
        )
      };
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
            element.classList.contains('d4-color-important') ||
            element.classList.contains('d4-color-label')
          ) {
            return true;
          }
          element = element.parentElement;
        }
        return false;
      }

      // Maxrollの能力値要件は、現在値だけを緑・赤のspanにして
      // 「+現在値 / 必要値 Attribute」と描画する。現在値はそのspanに残し、
      // 「/ 能力値+必要値」を後続の通常色Textノードへ書く。
      const isParagonAttributeRequirement =
        Boolean(tooltipContainer) &&
        PARAGON_ATTRIBUTE_REQUIREMENT_TEXT.test(originalText);
      const requirementParts = isParagonAttributeRequirement
        ? newText.match(
            /^\s*([+-]?\d[\d,.]*(?:%|x|\+)?)([\s\S]*)$/
          )
        : null;
      if (requirementParts) {
        const currentValueNodeIndex = textNodes.findIndex(
          textNode => DYNAMIC_VALUE_TEXT.test(textNode.nodeValue)
        );
        const plainTextNodeIndex = textNodes.findIndex(
          (textNode, index) =>
            index > currentValueNodeIndex &&
            !DYNAMIC_VALUE_TEXT.test(textNode.nodeValue) &&
            !isStyledTextNode(textNode)
        );
        if (currentValueNodeIndex >= 0 && plainTextNodeIndex >= 0) {
          textNodes.forEach(textNode => {
            textNode.nodeValue = '';
          });
          textNodes[currentValueNodeIndex].nodeValue = requirementParts[1];
          textNodes[plainTextNodeIndex].nodeValue = requirementParts[2];
          supplementaryRangeNodes.forEach(textNode => {
            textNode.nodeValue = '';
          });
          return true;
        }
      }

      // 条件付きボーナス文は複数spanをまたぐため、通常色のTextノードへ
      // 変換済みの一文を集約する。数値spanを選ぶと色が行全体へ溢れるので、
      // 動的数値ではないノードだけを出力先にする。
      const isParagonConditionalBonus =
        Boolean(tooltipContainer) &&
        PARAGON_CONDITIONAL_BONUS_TEXT.test(originalText);
      if (isParagonConditionalBonus) {
        const plainTextNodeIndex = textNodes.findIndex(
          textNode =>
            !DYNAMIC_VALUE_TEXT.test(textNode.nodeValue) &&
            !isStyledTextNode(textNode)
        );
        const outputNodeIndex =
          plainTextNodeIndex >= 0 ? plainTextNodeIndex : 0;
        textNodes.forEach((textNode, index) => {
          textNode.nodeValue = index === outputNodeIndex ? newText : '';
        });
        supplementaryRangeNodes.forEach(textNode => {
          textNode.nodeValue = '';
        });
        return true;
      }

      textNodes.forEach((textNode, nodeIndex) => {
        const dynamicMatch = textNode.nodeValue.match(DYNAMIC_VALUE_TEXT);
        const ordinalMatch = textNode.nodeValue.match(DYNAMIC_ORDINAL_TEXT);
        let value = dynamicMatch?.[1] || ordinalMatch?.[1] || null;

        if (!value && isTooltipSentence && isStyledTextNode(textNode)) {
          const originalStyledText = textNode.nodeValue.trim();
          const translatedStyledText = applyRegexTransformations(
            textNode.nodeValue,
            regexTable
          ).trim();
          const possessiveMatch = originalStyledText.match(
            /^([\s\S]+?)['’]s$/i
          );
          const translatedPossessiveBase = possessiveMatch
            ? applyRegexTransformations(
                possessiveMatch[1],
                regexTable
              ).trim()
            : '';
          value =
            translatedPossessiveBase &&
            newText.includes(translatedPossessiveBase)
              ? translatedPossessiveBase
              : translatedStyledText;
          if (
            textNode.parentElement?.closest('.d4-color-label') &&
            originalStyledText.endsWith(':') &&
            !newText.includes(value)
          ) {
            const translatedLabelEnd = newText.indexOf(':');
            if (translatedLabelEnd >= 0) {
              value = newText.slice(0, translatedLabelEnd + 1).trim();
            }
          }
          if (value && !newText.includes(value)) {
            const inflectedBase =
              !possessiveMatch && /s$/i.test(originalStyledText)
                ? originalStyledText.slice(0, -1)
                : '';
            const translatedInflectedBase = inflectedBase
              ? applyRegexTransformations(
                  inflectedBase,
                  regexTable
                ).trim()
              : '';
            value =
              translatedInflectedBase &&
              newText.includes(translatedInflectedBase)
                ? translatedInflectedBase
                : null;
          }
        }

        if (!value) {
          return;
        }
        requiredAnchorCount++;
        let valuePosition = newText.indexOf(value);
        // Maxrollの条件値は色付きspan内で「+69」だが、ゲーム内日本語の
        // 現在値は「69」と表示する。先頭+を除いた値でも同じspanをアンカーにする。
        if (valuePosition < 0 && value.startsWith('+')) {
          const unsignedValue = value.slice(1);
          const unsignedPosition = newText.indexOf(unsignedValue);
          if (unsignedPosition >= 0) {
            value = unsignedValue;
            valuePosition = unsignedPosition;
          }
        }
        if (valuePosition < 0 && /['’]s$/i.test(value)) {
          const valueWithoutPossessive = value.replace(/['’]s$/i, '');
          const possessivePosition = newText.indexOf(valueWithoutPossessive);
          if (possessivePosition >= 0) {
            value = valueWithoutPossessive;
            valuePosition = possessivePosition;
          }
        }
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
        anchors.push({
          nodeIndex,
          value,
          valuePosition,
          wrapped: /^\s*[\(（]/.test(textNode.nodeValue)
        });
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

      function writeAnchorValue(anchor) {
        const anchorNode = textNodes[anchor.nodeIndex];
        anchorNode.nodeValue = anchor.value;
        if (!anchor.wrapped) {
          return;
        }
        textNodes.forEach((textNode, index) => {
          if (
            index !== anchor.nodeIndex &&
            textNode.parentElement === anchorNode.parentElement &&
            /^\s*[\)）]\s*$/.test(textNode.nodeValue)
          ) {
            textNode.nodeValue = '';
          }
        });
      }

      function removeDuplicatedPercentSuffixes() {
        anchors.forEach(anchor => {
          if (!anchor.value.endsWith('%')) {
            return;
          }
          for (
            let index = anchor.nodeIndex + 1;
            index < textNodes.length;
            index++
          ) {
            if (!textNodes[index].nodeValue) {
              continue;
            }
            if (textNodes[index].nodeValue.startsWith('%')) {
              textNodes[index].nodeValue =
                textNodes[index].nodeValue.slice(1);
            }
            break;
          }
        });
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
          writeAnchorValue(anchor);
          nodePosition = anchor.nodeIndex + 1;
          textPosition = anchor.valuePosition + anchor.value.length;
        });
        writeSegment(nodePosition, textNodes.length, newText.slice(textPosition));
        removeDuplicatedPercentSuffixes();
        return finishReplacement();
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
            root &&
            roots.indexOf(root) === index &&
            !anchorRoots.includes(root)
           );
        const movableRoots = new Set([...anchorRoots, ...supplementaryRoots]);
        const rangeRoots = runTopLevelNodes.length
          ? runTopLevelNodes
          : Array.from(containerNode.childNodes);
        const canReorder =
          anchorRoots.every(Boolean) &&
          new Set(anchorRoots).size === anchorRoots.length &&
          rangeRoots.length > 0 &&
          rangeRoots.every(child =>
            child.parentNode === containerNode &&
            (
            child.nodeType === 3 ||
            movableRoots.has(child) ||
            (child.nodeType === 1 && child.textContent.trim() === '')
            )
          );

        if (canReorder) {
          const emptyElements = rangeRoots.filter(
            child => child.textContent.trim() === '' && !movableRoots.has(child)
          );
          const insertionPoint = rangeRoots[rangeRoots.length - 1].nextSibling;
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
            writeAnchorValue(anchor);
            fragment.appendChild(anchorRoots[index]);
            outputPosition = anchor.valuePosition + anchor.value.length;
          });
          const trailingText = newText.slice(outputPosition);
          if (trailingText) {
            fragment.appendChild(document.createTextNode(trailingText));
          }
          supplementaryRoots.forEach(root => fragment.appendChild(root));
          rangeRoots.forEach(root => {
            if (root.parentNode === containerNode) {
              root.remove();
            }
          });
          containerNode.insertBefore(fragment, insertionPoint);
          return finishReplacement();
        }
      }

      if (isTooltipSentence && requiredAnchorCount > 0) {
        return false;
      }

      // 通常テキストは従来どおり、先頭ノードへ変換結果を格納する。
      textNodes.forEach((textNode, index) => {
        textNode.nodeValue = index === 0 ? newText : '';
      });
      return finishReplacement();
    }

    function collectInlineTextNodes(
      node,
      textNodes,
      supplementaryRangeNodes = []
    ) {
      Array.from(node.childNodes).forEach(child => {
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
        if (isMaxrollGuideNode(child)) {
          return;
        }
        // Equipment の実アイテムTooltipでは、現在値の直後に
        // <span class="d4-color-inactive">[最小値 - 最大値]</span> が追加される。
        // これは原文データには存在しない補足表示なので、効果文の照合から外す。
        // span 自体はDOMに残るため、Maxrollの色・配置・数値表示は維持される。
        if (isSupplementaryValueElement(child)) {
          collectInlineTextNodes(child, supplementaryRangeNodes);
          return;
        }
        collectInlineTextNodes(child, textNodes, supplementaryRangeNodes);
      });
    }

    function isSupplementaryValueElement(element) {
      // [+]・[x]などの演算種別マーカーはMaxrollの版によって色クラスが異なる。
      // クラスに依存せず文字列で除外し、表示用DOM自体はそのまま保持する。
      if (SUPPLEMENTARY_VALUE_MARKER_TEXT.test(element.textContent)) {
        return true;
      }
      if (
        element.classList.contains('d4-color-lightgray') &&
        MAXROLL_DAMAGE_ANNOTATION_TEXT.test(element.textContent)
      ) {
        return true;
      }
      return (
        element.classList.contains('d4-color-inactive') &&
        DYNAMIC_VALUE_TEXT.test(element.textContent)
      );
    }

    function hasBlockBoundaryChild(node) {
      return (
        Array.from(node.children).some(child =>
          BLOCK_BOUNDARY_TAGS.has(child.tagName)
        ) ||
        Boolean(node.querySelector('br'))
      );
    }

    function normalizeDuplicatedDynamicSuffixes(node) {
      node.querySelectorAll(
        '.d4-color-resource, .d4-color-number'
      ).forEach(element => {
        const sibling = element.nextSibling;
        if (
          element.textContent.trim().endsWith('%') &&
          sibling?.nodeType === 3 &&
          sibling.nodeValue.startsWith('%')
        ) {
          sibling.nodeValue = sibling.nodeValue.slice(1);
        }
      });
    }

    function replaceInlineRunsBetweenBlockBoundaries(
      node,
      regexTable,
      stats
    ) {
      let textNodes = [];
      let supplementaryRangeNodes = [];
      let runTopLevelNodes = [];

      function flushRun() {
        if (textNodes.length) {
          replaceTextNodeRun(
            textNodes,
            regexTable,
            stats,
            supplementaryRangeNodes,
            node,
            runTopLevelNodes
          );
        }
        textNodes = [];
        supplementaryRangeNodes = [];
        runTopLevelNodes = [];
      }

      function addRunRoot(root) {
        if (root && !runTopLevelNodes.includes(root)) {
          runTopLevelNodes.push(root);
        }
      }

      function visitInlineRunNode(child, topLevelRoot) {
        if (child.nodeType === 3) {
          addRunRoot(topLevelRoot);
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
        if (isMaxrollGuideNode(child)) {
          flushRun();
          return;
        }
        if (BLOCK_BOUNDARY_TAGS.has(child.tagName)) {
          // Maxrollは改行を装飾spanの内側へ置くことがあるため、
          // 直下だけでなく子孫のBRでも文章を分割する。
          // ブロック要素の内容はreplaceTextの通常再帰へ任せる。
          flushRun();
          return;
        }
        if (isSupplementaryValueElement(child)) {
          addRunRoot(topLevelRoot);
          collectInlineTextNodes(child, supplementaryRangeNodes);
          return;
        }
        Array.from(child.childNodes).forEach(grandchild =>
          visitInlineRunNode(grandchild, topLevelRoot)
        );
      }

      Array.from(node.childNodes).forEach(child =>
        visitInlineRunNode(child, child)
      );
      flushRun();
      normalizeDuplicatedDynamicSuffixes(node);
    }

    function normalizeParagonGlyphRequirement(element) {
      if (
        element.nodeType !== 1 ||
        !element.closest(LONG_TEXT_TOOLTIP_SELECTOR)
      ) {
        return false;
      }

      // グリフソケットではMaxrollが現在値を別DOM枝の末尾へ置くため、
      // 個別置換後に「/ 知力+25+69」の形になる。末尾の色付き現在値spanを
      // 行頭へ移動し、ゲーム内と同じ「69 / 知力+25」へ正規化する。
      const match = element.textContent.trim().match(
        /^(?:[◆♦•·]\s*)?\/\s*(筋力|知力|意志力|敏捷性)\s*\+?([\d,.]+)\s*\+([\d,.]+)$/
      );
      if (!match) {
        return false;
      }

      const [, attribute, requiredValue, currentValue] = match;
      const textNodes = [];
      collectInlineTextNodes(element, textNodes);
      const currentValueNode = [...textNodes].reverse().find(
        textNode =>
          textNode.nodeValue.trim() === `+${currentValue}` ||
          textNode.nodeValue.trim() === currentValue
      );
      if (!currentValueNode) {
        return false;
      }

      function topLevelChild(textNode) {
        let child = textNode;
        while (child.parentNode && child.parentNode !== element) {
          child = child.parentNode;
        }
        return child.parentNode === element ? child : null;
      }

      const currentValueRoot = topLevelChild(currentValueNode);
      const firstTextRoot = textNodes.length
        ? topLevelChild(textNodes[0])
        : null;
      if (!currentValueRoot || !firstTextRoot) {
        return false;
      }

      textNodes.forEach(textNode => {
        textNode.nodeValue = '';
      });
      currentValueNode.nodeValue = currentValue;
      if (currentValueRoot !== firstTextRoot) {
        element.insertBefore(currentValueRoot, firstTextRoot);
      }
      currentValueRoot.after(
        document.createTextNode(` / ${attribute}+${requiredValue}`)
      );
      return true;
    }

    function replaceText(node, regexTable, stats = {nodes: 0, attempts: 0, replacements: 0, chars: 0}) {
      // Maxroll解説本文は段落単位の専用処理で扱う。
      // 通常処理で複数spanを結合すると、色付き語句やTooltip要素の文字が
      // 先頭Textノードへ集約されてしまうため、ここでは触らない。
      if (isMaxrollGuideNode(node)) {
        return stats;
      }
      if (node.nodeType === 1 && isSupplementaryValueElement(node)) {
        return stats;
      }
      if (node.nodeType === 3) {
        replaceTextNodeRun([node], regexTable, stats);
      } else if (
        node.nodeType === 1 &&
        !IGNORED_TEXT_TAGS.has(node.tagName) &&
        !node.hidden &&
        !node.isContentEditable
      ) {
        if (
          node.matches(DROP_SOURCE_ITEM_SELECTOR) &&
          replaceDropSourceText(node, stats)
        ) {
          return stats;
        }
        // Maxroll の効果文は数値や強調語ごとに span へ分割される。
        // ブロック境界を含まない要素では子孫テキストを一続きの文章として照合し、
        // 要素を作り直さず既存 Text ノードだけを書き換える。
        const hasBlockBoundary = hasBlockBoundaryChild(node);
        // 装着効果は色付きspanの外に句点がある。span内を再配置の単位に
        // すれば数値・下線・親の色を保持できる。句点は成功した時だけ消費する。
        const punctuationNode = node.nextSibling;
        if (
          !hasBlockBoundary &&
          node.matches('.d4-color-unique') &&
          node.closest(LONG_TEXT_TOOLTIP_SELECTOR) &&
          punctuationNode?.nodeType === 3 &&
          /^[.!?]$/.test(punctuationNode.nodeValue)
        ) {
          const sentenceNodes = [];
          const supplementaryNodes = [];
          collectInlineTextNodes(node, sentenceNodes, supplementaryNodes);
          if (sentenceNodes.length && replaceTextNodeRun(
            sentenceNodes, regexTable, stats, supplementaryNodes,
            node, [], punctuationNode
          )) return stats;
        }
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
              normalizeParagonGlyphRequirement(node);
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
        normalizeParagonGlyphRequirement(node);
      }
      return stats;
    }

    function replaceDropSourceText(element, stats) {
      // Maxrollは複数のドロップ元をカンマ区切りで1つの<li>に描画する。
      // 組み合わせ全文を列挙せず、各ボス名をtrimして個別に辞書照合する。
      if (
        element.children.length > 0 ||
        element.childNodes.length !== 1 ||
        element.firstChild.nodeType !== 3
      ) {
        return false;
      }
      const textNode = element.firstChild;
      const originalText = textNode.nodeValue;
      let replacementCount = 0;
      const translatedParts = originalText.split(',').map(part => {
        const bossName = part.trim();
        const translated = dropSourceTranslations.get(
          bossName.toLocaleLowerCase('en-US')
        );
        if (translated) {
          replacementCount++;
          return translated;
        }
        return bossName;
      });
      if (!replacementCount) {
        return false;
      }

      textNode.nodeValue = translatedParts.join(', ');
      stats.nodes++;
      stats.chars += originalText.length;
      stats.replacements += replacementCount;
      return true;
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
    let tooltipTranslationTimer;

    function observeDOM(regexTable) {
      if (domObserverStarted) {
        return;
      }
      domObserverStarted = true;
      const pendingRoots = new Set();
      const pendingTooltipRoots = new Set();

      function compactConnectedRoots(roots) {
        const connectedRoots = new Set(
          Array.from(roots).filter(candidate =>
            candidate && candidate.isConnected
          )
        );
        return Array.from(connectedRoots).filter(candidate => {
          let ancestor = candidate.parentElement;
          while (ancestor) {
            if (connectedRoots.has(ancestor)) {
              return false;
            }
            ancestor = ancestor.parentElement;
          }
          return true;
        });
      }

      // Tooltipは表示時間が短いため、Equipment全体の再翻訳を待たずに
      // 専用キューで追加されたTooltipだけを即時翻訳する。
      function scheduleTooltipTranslation(root) {
        const element = root?.nodeType === 3 ? root.parentElement : root;
        if (!element || element.nodeType !== 1) {
          return false;
        }

        const closestTooltip = element.closest(LONG_TEXT_TOOLTIP_SELECTOR);
        if (closestTooltip) {
          pendingTooltipRoots.add(closestTooltip);
        }
        element.querySelectorAll?.(LONG_TEXT_TOOLTIP_SELECTOR).forEach(tooltip => {
          pendingTooltipRoots.add(tooltip);
        });
        if (!pendingTooltipRoots.size) {
          return false;
        }

        // 連続したDOM更新で待機時間が延びないよう、既存タイマーはリセットしない。
        if (!tooltipTranslationTimer) {
          tooltipTranslationTimer = setTimeout(() => {
            tooltipTranslationTimer = null;
            if (!extensionEnabled) {
              pendingTooltipRoots.clear();
              return;
            }

            const tooltipRoots = compactConnectedRoots(pendingTooltipRoots);
            pendingTooltipRoots.clear();
            tooltipRoots.forEach(tooltipRoot => {
              replaceText(tooltipRoot, regexTable);
              replaceTitleAttributes(regexTable, undefined, tooltipRoot);
            });
            observer.takeRecords();
          }, 0);
        }
        return Boolean(closestTooltip);
      }

      function scheduleTranslation(root) {
        if (!root || !root.isConnected) {
          return;
        }
        const element = root.nodeType === 3 ? root.parentElement : root;
        // Maxrollは非選択中の全ビルド派生もhiddenでDOMに保持する。
        // 表示された時点の属性変更で処理すればよいので、非表示中は走査しない。
        if (element?.closest?.('[hidden]')) {
          return;
        }
        const rootIsInsideTooltip = scheduleTooltipTranslation(root);
        if (rootIsInsideTooltip) {
          return;
        }
        pendingRoots.add(root.nodeType === 3 ? root.parentElement : root);

        // デバウンスをリセットし続けると状態切替中の翻訳が始まらないため、
        // 最初の変更から一定時間後に必ず処理するスロットルとして扱う。
        if (observeDOMTimer) {
          return;
        }
        observeDOMTimer = setTimeout(() => {
          observeDOMTimer = null;
          if (!extensionEnabled) {
            pendingRoots.clear();
            return;
          }

          const roots = compactConnectedRoots(pendingRoots);
          pendingRoots.clear();

          roots.forEach(root => {
            replaceText(root, regexTable);
            replaceTitleAttributes(regexTable, undefined, root);
            observeMaxrollGuideBlocks(root, regexTable);
          });
          // 自身の同期的なDOM書き換えで発生したMutationRecordを破棄する。
          observer.takeRecords();
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
        // Maxrollはホバー、アニメーション、パラゴン盤面でclassを常時変更する。
        // 追加ノードと表示状態を表す属性の監視だけで十分であり、すべてのclass
        // 変更を監視すると、長時間開いたタブで再走査の負荷が増え続ける。
        attributeFilter: ['hidden', 'aria-selected', 'data-state', 'title']
      });
      if (D4DEBUG_DISPLAY) console.log('[D4T] MutationObserver started'); // デバッグ用ログ
    }

    function applyTranslations() {
      if (!extensionEnabled) {
        return;
      }
      if (activeRegexTable || translationsLoadPromise) {
        return translationsLoadPromise || Promise.resolve();
      }
      if (D4DEBUG_DISPLAY) console.log('[D4T] applyTranslations started'); // デバッグ用ログ
      const startTime = performance.now();
      translationsLoadPromise = loadTranslations().then(regexTable => {
        if (!extensionEnabled) {
          return;
        }
        if (D4DEBUG_DISPLAY) console.log('[D4T] Loaded regexTable:', regexTable); // デバッグ用ログ
        activeRegexTable = regexTable;
        const replaceStartTime = performance.now();
        const textStats = replaceText(document.body, regexTable);
        const replaceEndTime = performance.now();
        const titleStats = replaceTitleAttributes(regexTable);
        const totalEndTime = performance.now();
        const patternsCount =
          compiledPatterns.length + compiledWholeSentencePatterns.length;
        // console.log(`[D4T] Translation completed: Total ${(totalEndTime - startTime).toFixed(2)}ms, Text replacement ${(replaceEndTime - replaceStartTime).toFixed(2)}ms (${patternsCount} patterns × ${textStats.nodes} nodes = ${textStats.attempts} attempts, ${textStats.replacements} replacements, ${textStats.chars} chars), Title replacement ${(totalEndTime - replaceEndTime).toFixed(2)}ms (${titleStats.elements} elements, ${titleStats.replaced} replaced)`);
        observeDOM(regexTable);
        observeMaxrollGuideBlocks(document, regexTable);


        if (D4DEBUG_DISPLAY) console.log('[D4T] Translations applied on page load'); // デバッグ用ログ
      }).catch(error => {
        console.error('[D4T] Error loading translations:', error);
      }).finally(() => {
        translationsLoadPromise = null;
      });
      return translationsLoadPromise;
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
        guideTranslationSuspended = false;
        guideTranslatorAvailability = null;
        if (activeRegexTable) {
          replaceText(document.body, activeRegexTable);
          replaceTitleAttributes(activeRegexTable);
          observeMaxrollGuideBlocks(document, activeRegexTable);
        } else {
          applyTranslations();
        }
      } else if (
        message.action === 'translationModelReady' &&
        extensionEnabled &&
        activeRegexTable
      ) {
        guideTranslationSuspended = false;
        guideTranslatorAvailability = null;
        observeMaxrollGuideBlocks(document, activeRegexTable);
      }
    });

  } else {
    if (D4DEBUG_DISPLAY) console.log('[D4T] Extension is disabled');
  }
  }
);
