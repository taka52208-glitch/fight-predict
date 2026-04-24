import { useEffect, useState } from "react";
import App from "./App";
import { HowItWorks } from "./pages/HowItWorks";
import { Faq } from "./pages/Faq";
import { Articles } from "./pages/Articles";
import { ArticleUfcFn274 } from "./pages/ArticleUfcFn274";

export function navigate(to: string) {
  if (window.location.pathname === to) return;
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

const TITLES: Record<string, string> = {
  "/": "FIGHT PREDICT | UFC・RIZIN勝敗予測AI 無料ツール（機械学習＋17項目分析）",
  "/how-it-works": "予測ロジックの仕組み | FIGHT PREDICT",
  "/articles": "記事一覧 | FIGHT PREDICT",
  "/articles/ufc-fight-night-274":
    "UFC Fight Night 274 全11試合 AI勝敗予測レポート | FIGHT PREDICT",
  "/faq": "よくある質問 | FIGHT PREDICT",
};

const DESCRIPTIONS: Record<string, string> = {
  "/": "UFC・RIZINの試合結果をAIが無料で予測。機械学習＋17項目スコアリングで勝率・決着方法・根拠まで表示。",
  "/how-it-works":
    "FIGHT PREDICTの予測ロジックを詳しく解説。17項目スコアリング、機械学習モデル、データソース、信頼度判定の仕組み。",
  "/articles":
    "UFC・RIZINの大会別AI予測記事一覧。全試合の勝敗予測・スタッツ比較・分析ポイントを無料で公開。",
  "/articles/ufc-fight-night-274":
    "UFC Fight Night 274 - Sterling vs. Zalal の全11試合をAIが予測。スタッツ比較・決着方法・信頼度まで完全無料公開。",
  "/faq": "FIGHT PREDICTのよくある質問。予測精度、データソース、使い方、アフィリエイトについて。",
};

function updateMeta(path: string) {
  const title = TITLES[path] || TITLES["/"];
  const desc = DESCRIPTIONS[path] || DESCRIPTIONS["/"];
  document.title = title;

  const setMeta = (selector: string, attr: string, value: string) => {
    const el = document.querySelector(selector);
    if (el) el.setAttribute(attr, value);
  };
  setMeta('meta[name="description"]', "content", desc);
  setMeta('meta[property="og:title"]', "content", title);
  setMeta('meta[property="og:description"]', "content", desc);
  setMeta('meta[name="twitter:title"]', "content", title);
  setMeta('meta[name="twitter:description"]', "content", desc);

  const origin = window.location.origin;
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) canonical.setAttribute("href", origin + path);
  const ogUrl = document.querySelector('meta[property="og:url"]');
  if (ogUrl) ogUrl.setAttribute("content", origin + path);
}

export function Router() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    updateMeta(path);
    window.scrollTo(0, 0);
  }, [path]);

  if (path === "/how-it-works") return <HowItWorks />;
  if (path === "/faq") return <Faq />;
  if (path === "/articles") return <Articles />;
  if (path.startsWith("/articles/ufc-fight-night-274"))
    return <ArticleUfcFn274 />;
  return <App currentPath={path} />;
}
