# 解説の検証手順（検証役用）

誤情報が最悪の結果。削ることは常に許される。書き手のルールは tools/EXPLANATION_GUIDE.md。

## 入出力
- 入力: `private/drafts/<B>.json`（下書き）、`private/batches/<B>.json`（問題と公式正答。番号は1始まり）
- 出力: `private/explanations/<B>.json`（同じ形式。検証を通った内容だけ。evidence も残す）

## 手順
1. `python3 tools/check_answers.py private/drafts/<B>.json`（選択肢説明と公式正答の食い違い）と `python3 tools/check_evidence.py private/drafts/<B>.json` を実行。evidence の引用が出典本文に実在するかを機械照合する（出典は共有キャッシュ private/sources/ から読むので速い）。
2. 1問ずつ:
   - 解説が公式正答と一致しているか。
   - summary／choices の各項目／point／lesson の各段落が、`for` で対応づけられた evidence の引用によって**実際に支えられているか**（言い過ぎ・拡大解釈・「のみ」「必ず」「多い」などの付け足しがないか、引用符「」の中が原文どおりか、人の医療の資料に基づく内容にその旨の表示があるか、統計に年があるか）。
   - NOTFOUND の引用や、引用だけでは判断できない箇所に限り、`python3 tools/fetch.py URL --grep 語...` で原典の該当箇所を確認する。**全文の表示や WebFetch はしない。**
3. 修正:
   - 支えられていない文は、引用が支える範囲に言い換えるか削除。
   - lesson の段落は、一部でも支えがなければ段落ごと削除。
   - choices の項目に支えがなければ「正答ではありません。」に縮める。
   - summary 自体が支えられなければ、その問題を `{"skip": "検証で裏付けが取れず"}` にする。
   - 新しい主張は足さない。refs と evidence は残った主張に合わせて整理する。
   - "checked" は 2026-10-03。
   - choices の各項目は「正答。」（公式正答の番号）か「正答ではありません。」で始まる形にそろえる（既存の「正しい。」「誤り（正答）。」等は置き換える）。
4. 出力ファイルは2〜3問ごとに保存。最後に `python3 tools/check_evidence.py private/explanations/<B>.json` で NOTFOUND ゼロ、`python3 tools/check_answers.py private/explanations/<B>.json` で problems: 0 を確認。**各選択肢の説明が、公式正答の番号と一致した選択肢について書かれているか（順番の入れ替わりがないか）を必ず目で確認する。**
5. 他のプロジェクトファイルは変更しない。

## 報告
そのまま合格した数／修正した数（主な修正内容）／skip にした数／見つかった重大な誤り。
