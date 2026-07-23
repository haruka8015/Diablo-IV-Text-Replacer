document.addEventListener('DOMContentLoaded', () => {
  const toggleSwitch = document.getElementById('toggleSwitch');
  const convertButton = document.getElementById('convertButton');
  const versionElement = document.getElementById('version');

  function updateControls(enabled) {
    toggleSwitch.checked = enabled;
    convertButton.disabled = !enabled;
  }

  // 状態の読み込みが終わるまでは手動変換を無効にする
  convertButton.disabled = true;

  // ストレージから現在の状態を取得してスイッチの状態を設定
  chrome.storage.sync.get(['enabled'], function(result) {
    updateControls(result.enabled === true);
  });

  // バージョン情報を表示
  const manifestData = chrome.runtime.getManifest();
  versionElement.textContent = 'ver ' + manifestData.version;

  // スイッチがクリックされたときの動作
  toggleSwitch.addEventListener('change', () => {
    const newValue = toggleSwitch.checked;
    updateControls(newValue);
    chrome.storage.sync.set({ enabled: newValue }, function() {
      console.log('[D4T] Extension state set to', newValue ? 'enabled' : 'disabled');
    });
  });

  // 手動変換ボタンがクリックされたときの動作
  convertButton.addEventListener('click', () => {
    chrome.storage.sync.get(['enabled'], function(result) {
      if (result.enabled !== true) {
        updateControls(false);
        return;
      }

      chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
        if (tabs.length > 0) {
          chrome.tabs.sendMessage(tabs[0].id, { action: 'convert' });
        }
      });
    });
  });
});
