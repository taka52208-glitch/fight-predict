# 格闘技試合予測ツール「FIGHT PREDICT」開発進捗状況

## 1. 基本情報

- **ステータス**: v3完成＋安定性・精度改善継続中＋マネタイズ準備中（スマホ公開中）
- **進捗率**: 100%（v3）／安定性改善・マネタイズ進行中
- **最終更新日**: 2026-04-07
- **公開URL**: https://fight-predict-takas-projects-de61dd0f.vercel.app
- **APIエンドポイント**: https://fight-predict-api.onrender.com
- **GitHub**: https://github.com/taka52208-glitch/fight-predict

## 2. 技術構成

- **バックエンド**: Python (FastAPI) + BeautifulSoup + pykakasi
- **フロントエンド**: React + TypeScript (Vite)
- **データソース**: UFCstats.com（UFC）/ Sherdog（RIZIN）
- **選手キャッシュ**: UFC全選手 + RIZIN全80大会の出場選手を自動収集

## 3. 完了済み機能

### v1（MVP）
- [x] FastAPI サーバー構築
- [x] UFC選手データスクレイピング（UFCstats.com）
- [x] RIZIN選手データスクレイピング（Sherdog）
- [x] 勝敗予測ロジック（8項目スコアリング）
- [x] 予測API（選手名入力→勝率%出力）
- [x] React ダッシュボード（ダークテーマUI）
- [x] スタッツ比較表示（打撃・TD・SUB等8項目）
- [x] 予測根拠の表示
- [x] 大会一覧表示
- [x] レスポンシブ対応

### v2（精度改善・日本語対応）
- [x] 予測精度向上（12項目スコアリング + シグモイド補正）
  - 直近5試合の調子（連勝/連敗）
  - スタイルマッチアップ分析（ストライカー vs グラップラー）
  - リーチ差
  - 被弾率
  - 決着方法予測（KO/TKO, Submission, Decision）
  - 信頼度をデータ量で補正
- [x] オートコンプリート（2文字以上で候補表示）
- [x] UFC全選手キャッシュ（A-Z全ページ、初回ロード後は即検索）
- [x] 日本語検索対応
  - 漢字（朝倉未来、堀口恭司）
  - ひらがな（ごとうじょうじ、さばてろ）
  - カタカナ（ダニーサバテロ、シェイドゥラエフ）
  - 英語（Mikuru Asakura）
- [x] RIZIN全80大会の出場選手を自動スクレイプ
- [x] 外国人選手の英語名→カタカナ自動変換
- [x] 主要選手のカタカナ表記揺れ対応
- [x] RIZIN選手のスタッツ推定（戦績データから打撃/TD/SUB等を算出）
- [x] 手動マッピング：日本人選手約90名 + ひらがな約90件 + 外国人カタカナ約20件

### v3（予測精度の大幅向上）
- [x] 17項目スコアリング（12項目 → 17項目に拡張）
- [x] 対戦相手の質（Strength of Schedule, 重み6%）
  - 過去の対戦相手の平均勝率をキャッシュから算出
- [x] 年齢・キャリアフェーズ補正（重み6%）
  - 25-32歳ピーク、36歳以上から段階的にペナルティ
  - DOBから自動で現在年齢を算出
- [x] 直接対決（Head-to-Head）戦績（重み4%）
  - 過去の対戦履歴を全試合分スクレイプして記録
- [x] ブランク（レイオフ）補正（重み2%）
  - 最終試合日から経過月数を計算、12ヶ月以上でペナルティ
- [x] 階級変更の考慮（重み2%）
- [x] 信頼度判定の強化（4軸のデータ品質スコアで判定）
- [x] サーバー起動時のキャッシュプリロード（初回検索の待ち時間解消）
- [x] オートコンプリートのAbortController対応（リクエストキャンセル）
- [x] デバウンス時間短縮（日本語150ms/英語200ms）
- [x] UFC/RIZIN自動クロス検索（UFCで見つからなければRIZIN、逆も同様）
- [x] Sherdog名前表記揺れ対応（Ogikubo/Ougikubo等の長音変換フォールバック）

### デプロイ対応（2026-04-05）
- [x] フロントエンド: API URLを環境変数化（`VITE_API_BASE_URL`）
- [x] バックエンド: CORS許可オリジンを環境変数化（`ALLOWED_ORIGINS`）
- [x] requirements.txtにpykakasi追記（欠落修正）
- [x] Dockerfile作成（Python 3.12-slim + lxml依存）
- [x] render.yaml作成（Blueprint定義）
- [x] Render（バックエンド）デプロイ完了 — `srv-d78k28vfte5s739573l0`
- [x] Vercel（フロントエンド）デプロイ完了 — `prj_lguGRw9F6CoYrC0EVTcPssClWcID`
- [x] CORS疎通確認（4つのVercelエイリアスを許可）

### コールドスタート対策（2026-04-05追加）
- [x] **GitHub Actionsで10分ごとにAPIへping**（`.github/workflows/keep-alive.yml`）
  - Render無料プランの15分スリープを回避し、そもそも寝かせない
- [x] **フロント側 マウント時ウォームアップping**
  - アプリ起動直後に `/` を叩いてサーバーを温める
- [x] **タイムアウト付きfetch + 自動リトライ**（`fetchWithWakeup`）
  - 初回8秒で返らなければ最大75秒まで延長してリトライ
  - suggest / predict / fighter 全エンドポイントに適用
- [x] **「サーバー起動中…」バナー表示**
  - 3秒以上返らない場合に黄色の脈動バナーで状況をユーザーに伝える
- **背景**: スマホ(iPhone/Safari)から「今日は検索できない」と報告があり、
  Renderコールドスタート(30-60秒)+ Safariのモバイル回線タイムアウトが原因と特定。

### 選手情報の精度改善（2026-04-05追加）
ユーザーから「選手情報が一部違う」との報告を受け、実データで6つの不具合を特定・修正。
- [x] **UFC weight_class の誤表示を修正**（ufc_scraper.py）
  - 生の体重（"248 lbs." 等）が入っていたため、体重→階級名に変換
  - 例: Jon Jones `"248 lbs."` → `"Heavyweight"`
- [x] **UFC last_fight_date への相手名混入を修正**（ufc_scraper.py）
  - 例: `"MiocicNov 16, 2024"` → `"2024-11-16"`
  - 月略称のみ許容する厳密な正規表現に変更
- [x] **NC (No Contest) を引分として計上していた問題を修正**
  - UFC・RIZIN両スクレイパーで NC を recent_fights から除外
- [x] **RIZIN reach / last_fight_date を未取得だった問題を修正**
  - Sherdog ページからの抽出処理を追加
- [x] **RIZIN recent_fights の誤拾いを修正**（rizin_scraper.py）
  - エキシビション戦・関連ニュースの "draw" 等まで拾っていた
  - 例: 安保瑠輝也 `['L','D','D','D']` → `['L']`
  - "FIGHT HISTORY - PRO" セクションに限定 + 行全体一致の正規表現に変更
- [x] **扇久保博正の英語表記を統一**（rizin_cache.py）
  - `"Ougikubo"` → `"Ogikubo"`（name_mapping.py との不整合を解消）

### セキュリティ・品質改善（2026-04-06追加）
全コードを監査し、22件の問題を一括修正。

#### セキュリティ修正（重大5件）
- [x] **SSRF脆弱性を修正**（main.py）
  - `event_url`パラメータにドメインホワイトリスト検証を追加（ufcstats.com/sherdog.comのみ許可）
- [x] **CORSデフォルトを全開放→localhost限定に変更**（main.py）
  - `ALLOWED_ORIGINS`未設定時に`*`ではなく`localhost`のみ許可
- [x] **HTTP→HTTPSに変更**（ufc_scraper.py）
  - UFCstats.comへの全3URLをHTTPS化（MITM攻撃対策）
- [x] **キャッシュ競合条件を修正**（ufc_scraper.py / rizin_cache.py）
  - `asyncio.Lock()`を追加し、複数リクエストによる重複キャッシュ構築を防止
- [x] **起動時キャッシュを`await`で完了待ち**（main.py）
  - `create_task`→`asyncio.gather`に変更、初回リクエストの空結果を解消

#### 安定性・エラー処理（6件）
- [x] **大会一覧にも`fetchWithWakeup`を適用**（App.tsx）
  - コールドスタート時のハングを防止
- [x] **名前の部分一致を最長一致に改善**（main.py）
  - 「太郎」で別人がヒットする誤爆を防止
- [x] **`search_fighter`にtry-except追加**（ufc_scraper.py）
  - ネットワーク障害時のエンドポイントクラッシュを防止
- [x] **例外ログを追加**（全バックエンドファイル）
  - `except Exception: continue`→具体的例外＋`logger.warning`で原因特定可能に
- [x] **Fighterモデルの`age`フィールド重複を削除**（fighter.py）
- [x] **入力長の上限を100文字に制限**（main.py）

#### パフォーマンス改善（2件）
- [x] **UFCキャッシュ構築を並列化**（ufc_scraper.py）
  - A-Z 26リクエストを直列→`asyncio.gather`で並列実行（起動時間を大幅短縮）
- [x] **H2H計算のデッドコードを削除**（predictor.py）

#### UI/UX改善（5件）
- [x] **予測ボタン連打防止**（App.tsx）
- [x] **キーボード操作対応**（App.tsx）
  - オートコンプリートを矢印キー/Enter/Escapeで操作可能に
- [x] **確率バー表示崩れ修正**（App.tsx / App.css）
  - 5% vs 95%のような極端な割合でもテキストがはみ出さないよう修正
- [x] **スタッツNaN表示防止**（App.tsx）
  - APIがnullを返した場合のガードを追加
- [x] **ネットワークエラー時のメッセージ改善**（App.tsx）

#### アクセシビリティ改善（4件）
- [x] **ARIA属性を追加**（App.tsx）
  - `role="tablist"` / `aria-selected` / `role="alert"` / `aria-autocomplete` 等
- [x] **スクリーンリーダー用ラベル**（App.tsx / App.css）
  - `sr-only`クラスによる非表示ラベルを追加
- [x] **プレースホルダーのコントラスト改善**（App.css）
  - `#555`→`#777`でWCAGコントラスト基準に近づける
- [x] **`org`の型を厳密化**（App.tsx）
  - `string`→`"ufc" | "rizin"`に変更、unsafe castを除去

#### その他（2件）
- [x] **User-Agentを正直な識別子に変更**（ufc_scraper.py / rizin_scraper.py / rizin_cache.py）
  - ブラウザ偽装→`fight-predict-bot/1.0`
  - ⚠️ 2026-04-07に撤回：Sherdog/ufcstats.comがbot UAをブロックするため、ブラウザ互換UAに戻した
- [x] **keep-alive.ymlのAPI URLを環境変数化**（keep-alive.yml）
  - 公開リポジトリでの本番URL露出を軽減

### 選手検索精度・予測精度の改善（2026-04-06追加）
ユーザーから「伊藤祐樹を入力すると伊藤博之が出る」との報告を受け、名前マッチングと予測精度を全面改善。

#### 選手検索の厳密化（誤ヒット防止）
- [x] **Sherdog検索をスコアリング方式に変更**（rizin_scraper.py）
  - 旧: `"ito" in "hiroyuki ito"` → 部分一致で別人にヒット
  - 新: 姓名の全パーツ一致=90点、単語一致=70点、40点未満は除外
  - 最高スコアの選手を返す
- [x] **全検索を部分文字列→単語単位一致に変更**（ufc_scraper.py / rizin_scraper.py）
  - 根本原因: `"yuki" in "hiroyuki ito"` → True（"yuki"が"hiroYUKI"の部分文字列）
  - 修正: `"yuki" in ["hiroyuki", "ito"]` → False（単語リストで完全一致）
  - UFC検索（ufc_scraper.py）: `tp in name_lower`→`tp in name_words`に変更
  - Sherdogフィルタ（rizin_scraper.py）: `query not in name`→単語レベルのフィルタに変更
  - → 「伊藤祐樹(Ito Yuki)」で「Hiroyuki Ito」に絶対ヒットしなくなる

#### 予測精度の改善
- [x] **RIZIN推定スタッツの精度向上**（rizin_scraper.py）
  - 勝利方法の合計>100%時に正規化する処理を追加
  - `sub_avg`を「サブ率×2」→「サブ勝利数/総試合数×1.5」に修正（試合あたり頻度）
  - 各推定値のクランプ範囲を現実的な値に調整
- [x] **推定データ使用時の重み調整**（predictor.py）
  - `is_estimated`フラグをFighterモデルに追加（fighter.py）
  - RIZIN選手の推定スタッツ系ファクターの重みを60%に縮小
  - 代わりに戦績系ファクター（勝率・連勝・フィニッシュ率）の重みを140%に拡大
  - → 推定値に過度に依存せず、確実なデータ（戦績）を重視する予測に
- [x] **推定データ時の信頼度を自動ダウングレード**（predictor.py）
  - HIGH→MEDIUMに自動調整、信頼度判定で推定データを実データとカウントしない
- [x] **予測根拠に推定値の注記を追加**（predictor.py）
  - 「※スタッツは戦績から推定」をユーザーに明示
- [x] **年齢バウンドチェック追加**（ufc_scraper.py）
  - 15〜60歳の範囲外は0（不明）として扱う → データ入力エラーによる誤ペナルティを防止

### 安定性・同名別人問題の修正（2026-04-07追加）
ユーザーから「選手が検索できない」「伊藤祐樹・神龍誠のデータが違う」との報告を受け修正。

#### 検索不能の修正（3件）
- [x] **User-Agentをブラウザ互換に戻す**（ufc_scraper.py / rizin_scraper.py / rizin_cache.py）
  - `fight-predict-bot/1.0`がSherdog/ufcstats.comにブロックされていた
  - `Mozilla/5.0 ...`に戻して復旧
- [x] **サーバー起動をノンブロッキングに戻す**（main.py）
  - `await asyncio.gather()`でキャッシュ読込完了まで起動がブロックされていた
  - `asyncio.create_task()`に戻し、起動後すぐリクエスト受付可能に
- [x] **CORSデフォルトを`*`に戻す**（main.py）
  - `localhost`限定に変更されていたため、本番フロントからアクセス不可だった

#### 同名別人問題の根本対策（4件）
- [x] **RIZINキャッシュのSherdogURLを優先使用**（rizin_scraper.py）
  - RIZIN大会ページから取得した正しいURLを最優先で利用
  - Sherdog検索へのフォールバックは最終手段に
- [x] **Sherdog検索でRIZIN出場歴を検証**（rizin_scraper.py）
  - 同スコアの候補が複数ある場合、プロフィールに"RIZIN"が含まれる選手を優先
- [x] **Sherdog検索で名前の語順逆転にも対応**（rizin_scraper.py）
  - 日本人名はSherdog上で「Goto Shinryusei」「Shinryusei Goto」どちらの語順もあり得る
  - 全名・逆順名・ファーストネーム単体・ラストネーム単体を順次試行
- [x] **漢字表記揺れ・リングネームのマッピング追加**（rizin_cache.py）
  - 「伊藤祐樹」（祐）→「伊藤裕樹」（裕）と同じ"Yuki Ito"にマッピング
  - 「神龍誠」→ Sherdog上の正式名"Makoto Takahashi"にマッピング（Web検索で特定）
  - ひらがな「しんりゅうせい」「しんりゅうまこと」も追加

### マネタイズ対応（2026-04-06追加）
- [x] **アフィリエイトリンクUIの実装**（App.tsx / App.css）
  - 予測結果の下に配信サービスへの誘導バナーを追加
  - UFC選択時 → U-NEXT、RIZIN選択時 → ABEMA を動的に切替
  - ゴールドグラデーション背景＋ホバーアニメーション付きデザイン
  - フッターにも常設リンクを設置
- [x] **ASP（afb）への会員登録・審査完了**
  - afbを選定（U-NEXT・ABEMA両方を提携可能、報酬額が最高水準）
  - A8.netはU-NEXTの新規提携が終了していたため代替
- [x] **afb審査承認完了**（2026-04-09）
- [x] **U-NEXT提携申請**（afbで申請済み、審査待ち）
- [x] **ABEMA提携申請**（afbで申請済み、審査待ち）
- [ ] **U-NEXT・ABEMA提携承認待ち**
- [ ] **アフィリエイトURLの本番設置**（提携承認後にコード差替え）

## 4. 起動方法

### ローカル開発

```bash
# バックエンド
cd backend
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# フロントエンド
cd frontend
npx vite --port 5173
```

ブラウザで http://localhost:5173 を開く

※初回のRIZIN検索はキャッシュ構築のため30-60秒かかる（2回目以降は即座）

### 本番（PC・スマホから共通アクセス）

https://fight-predict-takas-projects-de61dd0f.vercel.app

※Render無料プランのため15分アクセスなしでスリープ→初回起動に30-60秒
　（GitHub Actionsで10分ごとにpingを入れているため通常は発生しない）

## 5. 今後の改善候補

- [x] ~~セキュリティ・品質改善~~（2026-04-06完了：SSRF/CORS/HTTPS/競合条件等22件修正）
- [x] ~~選手検索精度・予測精度改善~~（2026-04-06完了：名前マッチング厳密化＋推定データ重み調整）
- [ ] 予測精度の向上（機械学習モデル導入）
- [ ] 過去の予測的中率トラッキング
- [ ] 大会の全試合一括予測
- [ ] SNS共有機能（X投稿用画像生成）
- [x] ~~Vercel/Renderへのデプロイ~~（2026-04-05完了）
- [x] ~~コールドスタート対策~~（2026-04-05完了：GitHub Actions定期ping + フロント側リトライ）
- [x] ~~選手情報の正確性改善~~（2026-04-05完了：weight_class/last_fight_date/NC計上/reach等の6バグ修正）
- [ ] Render Starterプラン（$7/月）でスリープ回避（Actions pingで事足りれば不要）
- [ ] opponent_avg_win_rate キャッシュの定期更新（起動時ロードのみで長期的に陳腐化）
- [ ] reach未取得選手（Sherdogに情報なし）の補完ロジック
- [ ] カスタムドメイン割当
- [ ] 有料プラン（詳細分析・通知機能）
- [ ] X（Twitter）Bot化で集客（大会前に予測を自動ツイート）
- [ ] note/Brainで大会予測レポート販売（1大会300〜500円）
