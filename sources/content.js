chrome.storage.sync.get(['enabled'], function(result) {
  if (result.enabled) {
    console.log('Content script loaded'); // デバッグ用ログ

    let translationTable = {};

    function loadTranslations() {
      console.log('Loading translations...'); // デバッグ用ログ
      const url = chrome.runtime.getURL('translations.json');
      return fetch(url)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to load translations.json, status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          translationTable = data;
          const regexTable = [];
          for (let [pattern, replacement] of Object.entries(translationTable)) {
            regexTable.push([new RegExp(pattern, 'g'), replacement]);
          }
          return regexTable;
        });
    }

    function replaceText(node, regexTable) {
      if (node.nodeType === 3) { // テキストノード
        let text = node.nodeValue;
        for (let [regex, replacement] of regexTable) {
          text = text.replace(regex, replacement);
        }
        node.nodeValue = text;
      } else if (node.nodeType === 1) { // 要素ノード
        for (let child of node.childNodes) {
          replaceText(child, regexTable);
        }
      }
    }

    function replaceTitleAttributes(regexTable) {
      const elements = document.querySelectorAll('[title]');
      elements.forEach(el => {
        let title = el.getAttribute('title');
        for (let [regex, replacement] of regexTable) {
          title = title.replace(regex, replacement);
        }
        el.setAttribute('title', title);
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
    }

    window.addEventListener('load', () => {
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
      }).catch(error => {
        console.error('Error loading translations:', error);
      });
    });
  } else {
    console.log('Extension is disabled');
  }
});
