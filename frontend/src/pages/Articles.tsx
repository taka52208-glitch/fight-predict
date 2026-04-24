import { Nav, PageFooter } from "./Nav";
import { navigate } from "../router";

type ArticleCard = {
  slug: string;
  title: string;
  subtitle: string;
  date: string;
  readMinutes: number;
  summary: string;
};

const ARTICLES: ArticleCard[] = [
  {
    slug: "ufc-fight-night-274",
    title: "UFC Fight Night 274 - Sterling vs. Zalal 全11試合 AI勝敗予測",
    subtitle: "17項目スコアリング＋機械学習モデルによる完全予測",
    date: "2026-04-22",
    readMinutes: 10,
    summary:
      "メインのSterling vs Zalalを含む全11試合を、選手の戦績・打撃・グラップリング・年齢・直近の調子などから総合的にAI分析。各カードの予測勝者・確率・決着方法・信頼度を完全無料で公開しています。",
  },
];

export function Articles() {
  return (
    <div className="app site-page">
      <Nav current="/articles" />
      <main className="content-page">
        <header className="content-hero">
          <h1>大会別 AI予測レポート</h1>
          <p>
            UFC・RIZINの開催予定大会について、全試合の勝敗予測・スタッツ比較・分析ポイントをまとめた無料記事一覧です。
            FIGHT PREDICTの予測ロジック（17項目スコアリング＋機械学習モデル）をベースに、
            各カードを完全自動で分析しています。
          </p>
        </header>

        <section className="article-list">
          {ARTICLES.map((a) => (
            <article key={a.slug} className="article-card">
              <div className="article-card-meta">
                <span>{a.date}</span>
                <span>読了目安 {a.readMinutes}分</span>
              </div>
              <h2
                className="article-card-title"
                onClick={() => navigate(`/articles/${a.slug}`)}
              >
                {a.title}
              </h2>
              <p className="article-card-sub">{a.subtitle}</p>
              <p className="article-card-summary">{a.summary}</p>
              <button
                className="article-card-btn"
                onClick={() => navigate(`/articles/${a.slug}`)}
              >
                全文を読む →
              </button>
            </article>
          ))}
        </section>

        <section className="content-block">
          <h2>今後の公開予定</h2>
          <p>
            以下の大会についても同様のAI予測レポートを順次公開予定です。公開通知は
            <a
              href="https://x.com/fight_predict_"
              target="_blank"
              rel="noopener noreferrer"
            >
              {" "}@fight_predict_{" "}
            </a>
            にて行っています。
          </p>
          <ul>
            <li>UFC Fight Night 275（2026-05-02）</li>
            <li>UFC 328（2026-05-09）</li>
            <li>RIZIN 53（2026-05-10）</li>
            <li>Rizin Landmark 14（2026-06-06）</li>
          </ul>
        </section>

        <section className="content-block">
          <h2>このサイトについて</h2>
          <p>
            FIGHT PREDICTは、UFCstats.comとSherdog.comの公開データを元に、
            選手の打撃・グラップリング・戦績・年齢・連勝連敗・対戦相手の質などを機械的に集計し、
            17項目の独自スコアリングと機械学習モデル（ロジスティック回帰）を組み合わせて勝敗確率を算出する、
            格闘技ファン向けの無料AI予測ツールです。
          </p>
          <p>
            従来の感覚やスター選手のネームバリューに頼らず、データの積み重ねから「確率として」
            結果を見ようという試みです。信頼度（HIGH/MEDIUM/LOW）も同時に出力するため、
            予測が外れやすい接戦カードも事前に把握できます。
          </p>
        </section>
      </main>
      <PageFooter />
    </div>
  );
}
