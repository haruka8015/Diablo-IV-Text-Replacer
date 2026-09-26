# テスト入力の取り扱い

第三者のCSV抜粋、ゲーム原文データ、取得したサイトHTML・DOMはGitに追加しません。
調査用の入力はGit管理対象外の `tmp/local-fixtures/` に置きます。
このディレクトリに追加できるのは自作の最小テストデータのみです。

通常のPythonテストは外部資料を必要としません。実データ依存の検証は明示的にスキップします。
手元に入力がある場合のみ `D4T_LOCAL_FIXTURES=1` を設定するとローカル検証も実行します。

ブラウザの自作DOMテストは `tools/test_content_tooltip_dom.html`、取得DOMを使う任意の
ローカル検証は `tools/test_content_local_tooltip_dom.html` です。
ローカル検証の成功を通常テストの件数と混同しないでください。
