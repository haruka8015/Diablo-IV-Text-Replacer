# シーズン更新手順

リポジトリルートで実行する。以下のS15→S16は例で、対象シーズンに読み替える。
TSVの取得・CSVへの変換は [README](README.md#シーズン更新の手順)、開発上の制約は
[AGENTS.md](../AGENTS.md) を参照する。

## 1. 入力と更新前の状態を残す

- 旧・新シーズンの英日CSVを `tmp/S15/`、`tmp/S16/` などに分けて保存する。
  同じシーズンの再エクスポートも区別し、調査中の入力を上書きしない。
- 更新前の `sources/translations.json`、`sources/content.js`、生成スクリプトを
  調査用フォルダーへ退避するか、その状態を再現できるコミットを記録する。
  未コミットの修正がある場合、HEADが更新前の実装とは限らない。
- 入力CSV、全件レポート、DOMキャプチャは `tmp/` に置く。
  再現に必要な少数のCSV行とテストは `tools/fixtures/` と `tools/test_*` に残す。
  フィクスチャには由来と再現する問題を書き、タグ・改行・Index差も保持する。

## 2. 件数を確認し、新カテゴリの漏れを調べる

```powershell
python tools/merge_csv_translations.py --list-categories
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv --previous-en tmp/S15/en.csv --previous-ja tmp/S15/ja.csv --overwrite-existing --dry-run --report tmp/S16/season-preview.json
```

比較は両シーズンに同じ生成処理・カテゴリを適用する。生成できない新カテゴリは
比較結果にも出ないため、件数を見るだけで完了としない。

1. CSVをCSVパーサーで読み、新しい `FileName` 系列・`Key` を旧シーズンと比較する。
   説明文は複数行を含むため、テキストの行数をレコード数にしない。
   ルーンは `Item_Rune_` に加えて `Item_S15_Rune_` のようなシーズン付き系列も対象。
   名前・効果だけでなく、供物・クールダウン・装着方法の共通UI行と連結名も確認する。
2. 新要素の代表例で、次の対応先がすべて選択されるか確認する。

   | 内容 | 主な確認先 |
   | --- | --- |
   | 正式名・分類 | items、skill-tags、runesなど |
   | 装備効果・スキル説明 | effects、attributes、skills、runesなど |
   | アイテムのフレーバー | flavors（引用・話者表記も含む） |
   | 基礎ステータス・使用条件・装着説明 | attributes、tooltip-labels、共通UI行など |

3. 対象外のNPC会話・クエスト・ストーリー本文まで増えていないか確認する。
4. 英日Index差、対応のない行、生成を拒否された行、同じ英文の訳の競合を確認する。
   Indexを除いた対応付けは両言語で一意な場合だけ利用する。
5. 公式の正式名と、サイト独自の短縮ラベル・別名を分ける。
   正式名の登録だけで独自ラベルまで対応したと判断しない。

### レポートの読み方

| 項目 | 意味 |
| --- | --- |
| `added_rules` | 現在の辞書に追加する規則 |
| `overwritten_rules` | 同一キーの訳の更新前後とカテゴリ |
| `existing_value_differences` | 現在の辞書と生成訳の差 |
| `season_comparison.new_rule_keys` | 旧シーズンの生成結果にない規則 |
| `new_rules_missing_from_dictionary` | 上記のうち現在の辞書にもない件数（season_comparison内） |
| `previous_rules_missing_from_dictionary` | 旧シーズンから生成できたが未登録だった件数（同上） |
| `season_comparison.changed_translations` | 同一キーで英日CSVから生成される訳が変わったもの |
| `season_comparison.removed_rule_keys` | 旧シーズンからのみ生成されたキー。削除推奨リストではない |

件数は重複排除後の正規表現ルール数で、新規アイテム数ではない。
英文変更・既存の取り込み漏れ・生成処理の改善を、新しいゲーム要素の追加と混同しない。
初回報告では追加と既存訳更新を分け、対象外・競合などの未反映分も示す。

## 3. 不具合を切り分ける

| 確認 | 調べること |
| --- | --- |
| CSVの英日原文 | 効果・数値参照・条件が対応しているか。公式データ側の誤りもあり得る |
| 生成結果 | 対象カテゴリか。色タグ、数値式、混在するplaceholder、単複数指定を変換できたか |
| 表示英文と正規表現 | 桁区切り、小数、範囲、`%[x]` / `%[+]`、アポストロフィ、空白差が一致するか |
| 実際のJS置換処理 | 索引で候補から落ちないか。全文より断片が先に置換されないか。再適用で崩れないか |
| ホバー後の実DOM | 分割ノード、装飾、可変値、Tooltipの適用範囲が原因か |

長い数値用正規表現でも、一致する表示文は「3 seconds.」だけの場合がある。
キーの文字数だけで全文優先を判断しない。汎用 `(.*?)` が別の節や翻訳済みの
日本語を取り込み、値を誤った位置へ移していないかも確認する。

回帰かを調べるときは同じ原文を更新前と更新後のコード・辞書に通す。
旧辞書を新コードに載せるだけでは、コード変更による回帰を判定できない。

MaxrollのDOM調査は利用可能なら `inspect-maxroll-dom` スキルに従う。
アクセスできない場合もローカルCSVと表示原文で辞書・JS処理を検証できるが、
実DOMを推測して変更しない。ライブのホバー確認ができなかった範囲を報告する。

CSV由来の問題は辞書の手修正だけで済ませず、生成スクリプトと再現テストに反映する。
入力CSVの誤りへの例外は確認済みの行・英日原文に限定し、原文が変更・訂正されたら
適用しないテストも用意する。共通の数値正規表現変更は大量のキー追加を起こし得るため、
変更範囲と生成差分を確認する。

## 4. 辞書を生成し、検証する

確認した入力・カテゴリ・上書き方針を維持し、dry-runだけを外す。

```powershell
python tools/merge_csv_translations.py --en tmp/S16/en.csv --ja tmp/S16/ja.csv --previous-en tmp/S15/en.csv --previous-ja tmp/S15/ja.csv --overwrite-existing --report tmp/S16/season-applied.json
python -m unittest discover -s tools -p "test_*.py"
node --check sources/content.js
node tools/test_content_wildcards.js
```

- `--overwrite-existing` は生成できた同一キーの訳を更新する。省略すると既存訳を保持する。
  どちらも完全同期ではなく、未選択・生成不可・サイト専用の規則は別途確認が必要。
- 更新前辞書との差を確認し、手動訳の意図しない上書きや削除がないことを確認する。
  現在の方針は旧ルールの削除保留。旧CSVにだけあることを根拠に削除しない。
- Pythonは生成処理、JSテストは実際の文字列置換を検証する。
  Node.jsがなければ代替検証と未実施の項目を記録する。
- 代表例について、正式名、効果、フレーバー、条件、ルーンの組み合わせ、
  数値の順序、繰り返し適用を確認する。実装の変更に対応したテストを追加する。
- DOMの変更時は拡張とページを再読み込みし、ホバー・再ホバー・動的更新を確認する。
  テキスト処理だけの成功を実サイト検証済みと報告しない。

## 5. 配布物を作る

`sources/manifest.json` のバージョンをAGENTS.mdの規則と公開履歴に照らして確認する。
必要なバージョン変更は対応テストにも反映してからビルドする。

```powershell
python tools/build_extension.py
```

- `temp/Diablo_Translate_<version>.zip` を作る。同じ名前のZIPは上書きされるため、
  過去の配布物を保持したい場合は別の出力フォルダーを引数に指定する。
- ZIPの破損チェックに加え、格納ファイルが現在の `sources/` とバイト単位で一致すること、
  manifestのバージョン、不要な調査資料が入っていないことを確認する。
- ZIP作成とストア公開を区別し、配布先リンク、バージョン、検証結果、未確認範囲を報告する。
