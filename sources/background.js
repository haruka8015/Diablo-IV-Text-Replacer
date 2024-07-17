chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({ enabled: true });
  console.log('[D4T] Extension installed and enabled');
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && /^http/.test(tab.url)) {
    chrome.storage.sync.get(['enabled'], function(result) {
      if (result.enabled) {
        if (chrome.scripting && chrome.scripting.executeScript) {
          chrome.scripting.executeScript({
            target: { tabId: tabId },
            files: ['content.js']
          }, () => {
            if (chrome.runtime.lastError) {
              console.error('[D4T] ' + chrome.runtime.lastError.message);
            }
          });
        } else {
          console.error('[D4T] chrome.scripting or chrome.scripting.executeScript is not available.');
        }
      }
    });
  }
});
