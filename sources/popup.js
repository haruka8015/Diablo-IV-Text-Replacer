document.addEventListener('DOMContentLoaded', () => {
  const toggleSwitch = document.getElementById('toggleSwitch');
  const convertButton = document.getElementById('convertButton');

  // ストレージから現在の状態を取得してスイッチの状態を設定
  chrome.storage.sync.get(['enabled'], function(result) {
    toggleSwitch.checked = !!result.enabled;
  });

  // スイッチがクリックされたときの動作
  toggleSwitch.addEventListener('change', () => {
    const newValue = toggleSwitch.checked;
    chrome.storage.sync.set({ enabled: newValue }, function() {
      console.log('[D4T] Extension state set to', newValue ? 'enabled' : 'disabled');
      // アクティブなタブをリロード
      chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
        if (tabs.length > 0) {
          chrome.tabs.reload(tabs[0].id);
        }
      });
    });
  });

  // 手動変換ボタンがクリックされたときの動作
  convertButton.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      if (tabs.length > 0) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'convert' });
      }
    });
  });
});
