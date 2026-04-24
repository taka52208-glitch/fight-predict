import { useEffect, useState } from "react";
import { Nav, PageFooter } from "./Nav";
import { mdToHtml } from "../markdown";
import { navigate } from "../router";
import { AdSlot } from "../components/AdSlot";
import articleMd from "../articles/ufc-fight-night-274.md?raw";

export function ArticleUfcFn274() {
  const [html, setHtml] = useState("");
  useEffect(() => {
    setHtml(mdToHtml(articleMd));
  }, []);

  return (
    <div className="app site-page">
      <Nav current="/articles" />
      <article className="article-body">
        <div className="article-meta">
          <span>AI予測レポート</span>
          <span>2026-04-22 公開</span>
          <span>読了目安 10分</span>
        </div>

        <AdSlot placement="article-top" />

        <div dangerouslySetInnerHTML={{ __html: html }} />

        <div className="article-cta">
          <h3>他の選手・他の大会も予測したい方へ</h3>
          <p>
            FIGHT PREDICTは選手名を入力するだけで、任意の対戦カードをAIが予測する無料ツールです。
            UFC・RIZINのどちらにも対応しており、大会一覧から全試合の一括予測もできます。
          </p>
          <button
            className="article-cta-btn"
            onClick={() => navigate("/")}
          >
            予測ツールを試す
          </button>
          <button
            className="article-cta-btn secondary"
            onClick={() => navigate("/how-it-works")}
          >
            予測ロジックを確認する
          </button>
        </div>

        <AdSlot placement="article-bottom" />

        <div className="article-related">
          <h4>関連ページ</h4>
          <ul>
            <li>
              <a
                href="/how-it-works"
                onClick={(e) => { e.preventDefault(); navigate("/how-it-works"); }}
              >
                予測ロジックの仕組み（17項目スコアリング＋機械学習の詳細）
              </a>
            </li>
            <li>
              <a
                href="/faq"
                onClick={(e) => { e.preventDefault(); navigate("/faq"); }}
              >
                よくある質問（予測精度・データソース・使い方）
              </a>
            </li>
            <li>
              <a
                href="/articles"
                onClick={(e) => { e.preventDefault(); navigate("/articles"); }}
              >
                他の大会予測記事一覧
              </a>
            </li>
          </ul>
        </div>
      </article>
      <PageFooter />
    </div>
  );
}
