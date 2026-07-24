document.addEventListener('DOMContentLoaded', () => {
  const toggleSwitch = document.getElementById('toggleSwitch');
  const translationToggle = document.getElementById('translationToggle');
  const downloadModelButton =
    document.getElementById('downloadModelButton');
  const translatorStatus = document.getElementById('translatorStatus');
  const convertButton = document.getElementById('convertButton');
  const versionElement = document.getElementById('version');
  const translatorOptions = {
    sourceLanguage: 'en',
    targetLanguage: 'ja'
  };

  function updateControls(enabled, guideTranslationEnabled) {
    toggleSwitch.checked = enabled;
    translationToggle.checked = guideTranslationEnabled;
    translationToggle.disabled = !enabled;
    convertButton.disabled = !enabled;
  }

  // 状態の読み込みが終わるまでは手動変換を無効にする
  convertButton.disabled = true;
  translationToggle.disabled = true;

  // ストレージから現在の状態を取得してスイッチの状態を設定
  chrome.storage.sync.get(
    ['enabled', 'guideTranslationEnabled'],
    function(result) {
      updateControls(
        result.enabled === true,
        result.guideTranslationEnabled !== false
      );
    }
  );

  // バージョン情報を表示
  const manifestData = chrome.runtime.getManifest();
  versionElement.textContent = 'ver ' + manifestData.version;

  // スイッチがクリックされたときの動作
  toggleSwitch.addEventListener('change', () => {
    const newValue = toggleSwitch.checked;
    updateControls(newValue, translationToggle.checked);
    chrome.storage.sync.set({enabled: newValue}, function() {
      console.log(
        '[D4T] Extension state set to',
        newValue ? 'enabled' : 'disabled'
      );
    });
  });

  translationToggle.addEventListener('change', () => {
    chrome.storage.sync.set({
      guideTranslationEnabled: translationToggle.checked
    });
  });

  function setTranslatorStatus(message, availability = null) {
    translatorStatus.textContent = message;
    downloadModelButton.disabled =
      availability === 'available' ||
      availability === 'downloading' ||
      availability === 'unsupported' ||
      availability === 'unavailable';
    downloadModelButton.textContent = availability === 'available'
      ? '英→日 翻訳モデルはダウンロード済み'
      : '英→日 翻訳モデルをダウンロード';
  }

  async function refreshTranslatorStatus() {
    if (!('Translator' in self)) {
      setTranslatorStatus(
        'Chrome Translator APIを利用できません（Chrome 138以降が必要です）。',
        'unsupported'
      );
      return;
    }

    try {
      const availability =
        await Translator.availability(translatorOptions);
      const messages = {
        available: '翻訳モデルは利用できます。',
        downloadable: '翻訳モデルのダウンロードが必要です。',
        downloading: '翻訳モデルをダウンロードしています…',
        unavailable: 'この環境では英→日翻訳を利用できません。'
      };
      setTranslatorStatus(
        messages[availability] || `翻訳モデル: ${availability}`,
        availability
      );
    } catch (error) {
      setTranslatorStatus(`状態確認に失敗しました: ${error.message}`);
    }
  }

  downloadModelButton.addEventListener('click', async () => {
    if (!('Translator' in self)) {
      await refreshTranslatorStatus();
      return;
    }

    setTranslatorStatus('翻訳モデルの準備を開始します…', 'downloading');

    try {
      // create() はダウンロード開始時にユーザー操作を必要とするため、
      // click ハンドラ内で最初の await より前に呼び出す。
      const createPromise = Translator.create({
        ...translatorOptions,
        monitor(monitor) {
          monitor.addEventListener('downloadprogress', event => {
            const percent = Math.round(event.loaded * 100);
            translatorStatus.textContent =
              `翻訳モデルをダウンロードしています… ${percent}%`;
          });
        }
      });
      const translator = await createPromise;
      translator.destroy();
      setTranslatorStatus('翻訳モデルは利用できます。', 'available');
      chrome.tabs.query(
        {active: true, currentWindow: true},
        tabs => {
          if (tabs.length > 0) {
            chrome.tabs.sendMessage(
              tabs[0].id,
              {action: 'translationModelReady'}
            );
          }
        }
      );
    } catch (error) {
      setTranslatorStatus(`ダウンロードに失敗しました: ${error.message}`);
      downloadModelButton.disabled = false;
    }
  });

  // 手動変換ボタンがクリックされたときの動作
  convertButton.addEventListener('click', () => {
    chrome.storage.sync.get(['enabled'], function(result) {
      if (result.enabled !== true) {
        updateControls(false, translationToggle.checked);
        return;
      }

      chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
        if (tabs.length > 0) {
          chrome.tabs.sendMessage(tabs[0].id, { action: 'convert' });
        }
      });
    });
  });

  refreshTranslatorStatus();
});
