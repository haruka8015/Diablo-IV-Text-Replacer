document.addEventListener('DOMContentLoaded', () => {
  const toggleSwitch = document.getElementById('toggleSwitch');

  // ストレージから現在の状態を取得してスイッチの状態を設定
  chrome.storage.sync.get(['enabled'], function(result) {
    if (result.enabled) {
      toggleSwitch.checked = true;
    } else {
      toggleSwitch.checked = false;
    }
  });

  // スイッチがクリックされたときの動作
  toggleSwitch.addEventListener('change', () => {
    const newValue = toggleSwitch.checked;
    chrome.storage.sync.set({ enabled: newValue }, function() {
      console.log('Extension state set to', newValue ? 'enabled' : 'disabled');
    });
  });
});