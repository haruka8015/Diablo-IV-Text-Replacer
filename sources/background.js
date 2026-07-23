chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(['enabled'], function(result) {
    // 初回インストール時だけ有効化する。更新・再読み込み時はユーザー設定を維持する。
    if (typeof result.enabled === 'undefined') {
      chrome.storage.sync.set({ enabled: true });
      console.log('[D4T] Extension installed and enabled');
    }
  });
});
