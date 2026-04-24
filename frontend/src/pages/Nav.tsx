import { navigate } from "../router";

export function Nav({ current }: { current: string }) {
  const items = [
    { to: "/", label: "予測ツール" },
    { to: "/how-it-works", label: "仕組み" },
    { to: "/articles", label: "記事" },
    { to: "/faq", label: "FAQ" },
  ];
  return (
    <nav className="site-nav" aria-label="サイト内メニュー">
      <div
        className="site-nav-brand"
        onClick={() => navigate("/")}
        role="link"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter") navigate("/");
        }}
      >
        FIGHT PREDICT
      </div>
      <ul className="site-nav-links">
        {items.map((it) => (
          <li key={it.to}>
            <a
              href={it.to}
              className={current === it.to ? "active" : ""}
              onClick={(e) => {
                e.preventDefault();
                navigate(it.to);
              }}
            >
              {it.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function PageFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-links">
          <a href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>予測ツール</a>
          <a href="/how-it-works" onClick={(e) => { e.preventDefault(); navigate("/how-it-works"); }}>仕組み</a>
          <a href="/articles" onClick={(e) => { e.preventDefault(); navigate("/articles"); }}>記事</a>
          <a href="/faq" onClick={(e) => { e.preventDefault(); navigate("/faq"); }}>FAQ</a>
          <a href="https://x.com/fight_predict_" target="_blank" rel="noopener noreferrer">X (@fight_predict_)</a>
          <a href="https://note.com" target="_blank" rel="noopener noreferrer">note</a>
        </div>
        <p className="site-footer-copy">
          © FIGHT PREDICT — UFC・RIZIN 勝敗予測AI。本サイトの予測は参考情報であり、試合結果を保証するものではありません。
        </p>
      </div>
    </footer>
  );
}
