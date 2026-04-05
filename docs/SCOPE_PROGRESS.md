# 格闘技試合予測ツール「FIGHT PREDICT」開発進捗状況

## 1. 基本情報

- **ステータス**: v3完成＋本番デプロイ完了＋コールドスタート対策済み（スマホ公開中）
- **進捗率**: 100%（v3）
- **最終更新日**: 2026-04-05
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

- [ ] 予測精度の向上（機械学習モデル導入）
- [ ] 過去の予測的中率トラッキング
- [ ] 大会の全試合一括予測
- [ ] SNS共有機能（X投稿用画像生成）
- [x] ~~Vercel/Renderへのデプロイ~~（2026-04-05完了）
- [x] ~~コールドスタート対策~~（2026-04-05完了：GitHub Actions定期ping + フロント側リトライ）
- [ ] Render Starterプラン（$7/月）でスリープ回避（Actions pingで事足りれば不要）
- [ ] 選手情報の正確性確認・修正（一部の選手で情報が違う報告あり、具体例待ち）
- [ ] カスタムドメイン割当
- [ ] 有料プラン（詳細分析・通知機能）
