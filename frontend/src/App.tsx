import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Renderコールドスタート対策: タイムアウト付きfetch + 1回リトライ
async function fetchWithWakeup(
  url: string,
  opts: RequestInit = {},
  onWaking?: (waking: boolean) => void
): Promise<Response> {
  const attempt = async (timeoutMs: number): Promise<Response> => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      // 呼び出し元のsignalも尊重する
      const signal = opts.signal
        ? composeSignals(opts.signal, ctrl.signal)
        : ctrl.signal;
      return await fetch(url, { ...opts, signal });
    } finally {
      clearTimeout(timer);
    }
  };
  try {
    return await attempt(8000);
  } catch (e) {
    // 呼び出し元がabortしたなら伝播
    if (opts.signal?.aborted) throw e;
    // 初回失敗 = コールドスタートの可能性 → 起動中メッセージ出してリトライ
    onWaking?.(true);
    try {
      return await attempt(75000);
    } finally {
      onWaking?.(false);
    }
  }
}

function composeSignals(a: AbortSignal, b: AbortSignal): AbortSignal {
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort();
  if (a.aborted || b.aborted) ctrl.abort();
  else {
    a.addEventListener("abort", onAbort, { once: true });
    b.addEventListener("abort", onAbort, { once: true });
  }
  return ctrl.signal;
}

type Fighter = {
  name: string;
  nickname: string;
  record: string;
  wins: number;
  losses: number;
  draws: number;
  ko_wins: number;
  sub_wins: number;
  dec_wins: number;
  height: string;
  reach: string;
  weight_class: string;
  stance: string;
  organization: string;
  sig_strikes_landed_per_min: number;
  sig_strike_accuracy: number;
  sig_strikes_absorbed_per_min: number;
  sig_strike_defense: number;
  takedown_avg: number;
  takedown_accuracy: number;
  takedown_defense: number;
  submission_avg: number;
};

type Suggestion = {
  name: string;
  nickname: string;
  record: string;
  weight_class: string;
};

type Prediction = {
  fighter_a_name: string;
  fighter_b_name: string;
  fighter_a_win_prob: number;
  fighter_b_win_prob: number;
  confidence: string;
  factors: string[];
  method_prediction: string;
};

type UpcomingEvent = {
  name: string;
  date: string;
  url: string;
  organization: string;
};

function FighterInput({
  value,
  onChange,
  onSelect,
  placeholder,
  label,
  org,
  onWaking,
}: {
  value: string;
  onChange: (v: string) => void;
  onSelect: (name: string) => void;
  placeholder: string;
  label: string;
  org: string;
  onWaking?: (waking: boolean) => void;
}) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchSuggestions = useCallback(
    async (q: string) => {
      if (abortRef.current) {
        abortRef.current.abort();
      }

      const isJapanese = /[\u3000-\u9fff\uff00-\uffef]/.test(q);
      if (q.length < (isJapanese ? 1 : 2)) {
        setSuggestions([]);
        setLoading(false);
        return;
      }

      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);

      try {
        const res = await fetchWithWakeup(
          `${API_BASE}/api/suggest?q=${encodeURIComponent(q)}&org=${org}`,
          { signal: controller.signal },
          onWaking
        );
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
          setActiveIndex(-1);
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setSuggestions([]);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    },
    [org, onWaking]
  );

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // Reset suggestions when org changes
  useEffect(() => {
    setSuggestions([]);
    setShowSuggestions(false);
  }, [org]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange(v);

    if (timerRef.current) clearTimeout(timerRef.current);

    if (!v.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      setLoading(false);
      if (abortRef.current) abortRef.current.abort();
      return;
    }

    const isJapanese = /[\u3000-\u9fff\uff00-\uffef]/.test(v);
    timerRef.current = setTimeout(() => fetchSuggestions(v), isJapanese ? 150 : 200);
  };

  const handleSelect = (name: string) => {
    onChange(name);
    onSelect(name);
    setShowSuggestions(false);
    setActiveIndex(-1);
  };

  // Keyboard navigation for suggestions
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIndex].name);
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
      setActiveIndex(-1);
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="fighter-input-wrapper" ref={wrapperRef}>
      <label className="sr-only">{label}</label>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        aria-expanded={showSuggestions}
        aria-autocomplete="list"
        aria-label={label}
      />
      {loading && <span className="input-spinner" aria-label="検索中" />}
      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions" role="listbox">
          {suggestions.map((s, i) => (
            <div
              key={`${s.name}-${i}`}
              className={`suggestion-item${i === activeIndex ? " active" : ""}`}
              role="option"
              aria-selected={i === activeIndex}
              onClick={() => handleSelect(s.name)}
            >
              <span className="suggestion-name">{s.name}</span>
              {s.nickname && (
                <span className="suggestion-nickname">"{s.nickname}"</span>
              )}
              <span className="suggestion-record">{s.record}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProbBar({
  nameA,
  nameB,
  probA,
  probB,
}: {
  nameA: string;
  nameB: string;
  probA: number;
  probB: number;
}) {
  const pctA = Math.round(probA * 100);
  const pctB = Math.round(probB * 100);
  return (
    <div className="prob-bar-wrapper">
      <div className="prob-labels">
        <span className="fighter-a-label">{nameA}</span>
        <span className="fighter-b-label">{nameB}</span>
      </div>
      <div className="prob-bar">
        <div
          className="prob-bar-a"
          style={{ width: `${Math.max(pctA, 8)}%` }}
        >
          {pctA}%
        </div>
        <div
          className="prob-bar-b"
          style={{ width: `${Math.max(pctB, 8)}%` }}
        >
          {pctB}%
        </div>
      </div>
    </div>
  );
}

function StatCompare({
  label,
  valA,
  valB,
  format = "number",
}: {
  label: string;
  valA: number;
  valB: number;
  format?: "number" | "percent";
}) {
  const safeA = valA ?? 0;
  const safeB = valB ?? 0;
  const displayA = format === "percent" ? `${Math.round(safeA * 100)}%` : safeA.toFixed(1);
  const displayB = format === "percent" ? `${Math.round(safeB * 100)}%` : safeB.toFixed(1);
  const betterA = safeA > safeB;
  const betterB = safeB > safeA;

  return (
    <div className="stat-row">
      <span className={`stat-val ${betterA ? "better" : ""}`}>{displayA}</span>
      <span className="stat-label">{label}</span>
      <span className={`stat-val ${betterB ? "better" : ""}`}>{displayB}</span>
    </div>
  );
}

function FighterCard({ fighter }: { fighter: Fighter }) {
  const winRate =
    fighter.wins + fighter.losses + fighter.draws > 0
      ? fighter.wins / (fighter.wins + fighter.losses + fighter.draws)
      : 0;

  return (
    <div className="fighter-card">
      <div className="fighter-name">{fighter.name}</div>
      {fighter.nickname && (
        <div className="fighter-nickname">"{fighter.nickname}"</div>
      )}
      <div className="fighter-record">{fighter.record}</div>
      <div className="fighter-org">{fighter.organization}</div>
      <div className="fighter-stats-mini">
        <div>勝率 {Math.round(winRate * 100)}%</div>
        <div>
          KO {fighter.ko_wins} | SUB {fighter.sub_wins} | DEC {fighter.dec_wins}
        </div>
        {fighter.height && <div>身長 {fighter.height}</div>}
        {fighter.reach && <div>リーチ {fighter.reach}</div>}
      </div>
    </div>
  );
}

// アフィリエイトリンク設定（実際のアフィリエイトURLに差し替えてください）
const AFFILIATE_LINKS = {
  ufc: {
    name: "U-NEXT",
    url: "https://www.video.unext.jp/?ref=fight-predict",
    description: "UFCの全試合をライブ配信中",
    cta: "U-NEXTで観る",
  },
  rizin: {
    name: "ABEMA",
    url: "https://abema.tv/video/genre/fighting?ref=fight-predict",
    description: "RIZINの試合をライブ配信中",
    cta: "ABEMAで観る",
  },
} as const;

function WatchBanner({ org }: { org: "ufc" | "rizin" }) {
  const link = AFFILIATE_LINKS[org];
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="watch-banner"
    >
      <span className="watch-banner-label">この試合を観るなら</span>
      <span className="watch-banner-service">{link.name}</span>
      <span className="watch-banner-desc">{link.description}</span>
      <span className="watch-banner-cta">{link.cta} &rarr;</span>
    </a>
  );
}

function App() {
  const [fighterAName, setFighterAName] = useState("");
  const [fighterBName, setFighterBName] = useState("");
  const [org, setOrg] = useState<"ufc" | "rizin">("ufc");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [fighterA, setFighterA] = useState<Fighter | null>(null);
  const [fighterB, setFighterB] = useState<Fighter | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"predict" | "events">("predict");
  const [wakingUp, setWakingUp] = useState(false);

  // マウント時にサーバーへウォームアップping (Renderコールドスタート対策)
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 90000);
    let waking = false;
    const slow = setTimeout(() => {
      waking = true;
      setWakingUp(true);
    }, 3000);
    fetch(`${API_BASE}/`, { signal: ctrl.signal })
      .catch(() => {})
      .finally(() => {
        clearTimeout(timer);
        clearTimeout(slow);
        if (waking) setWakingUp(false);
      });
    return () => {
      clearTimeout(timer);
      clearTimeout(slow);
      ctrl.abort();
    };
  }, []);

  const fetchPrediction = async () => {
    if (!fighterAName.trim() || !fighterBName.trim()) {
      setError("両方の選手名を入力してください");
      return;
    }

    if (loading) return; // 連打防止

    setLoading(true);
    setError("");
    setPrediction(null);
    setFighterA(null);
    setFighterB(null);

    try {
      const [predRes, faRes, fbRes] = await Promise.all([
        fetchWithWakeup(
          `${API_BASE}/api/predict?fighter_a=${encodeURIComponent(fighterAName)}&fighter_b=${encodeURIComponent(fighterBName)}&org=${org}`,
          {},
          setWakingUp
        ),
        fetchWithWakeup(
          `${API_BASE}/api/fighter/${encodeURIComponent(fighterAName)}?org=${org}`,
          {},
          setWakingUp
        ),
        fetchWithWakeup(
          `${API_BASE}/api/fighter/${encodeURIComponent(fighterBName)}?org=${org}`,
          {},
          setWakingUp
        ),
      ]);

      if (!predRes.ok) {
        const err = await predRes.json();
        throw new Error(err.detail || "予測に失敗しました");
      }

      const pred = await predRes.json();
      setPrediction(pred);

      if (faRes.ok) setFighterA(await faRes.json());
      if (fbRes.ok) setFighterB(await fbRes.json());
    } catch (e: unknown) {
      if (e instanceof TypeError) {
        setError("サーバーに接続できません。しばらく待ってから再度お試しください。");
      } else {
        setError(e instanceof Error ? e.message : "エラーが発生しました");
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchEvents = async () => {
    setEventsLoading(true);
    try {
      const res = await fetchWithWakeup(
        `${API_BASE}/api/events/upcoming?org=all`,
        {},
        setWakingUp
      );
      if (res.ok) {
        setEvents(await res.json());
      }
    } catch {
      setEvents([]);
    } finally {
      setEventsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>FIGHT PREDICT</h1>
        <p>格闘技試合予測ツール</p>
      </header>

      {wakingUp && (
        <div className="waking-banner" role="alert">
          サーバー起動中です…（初回アクセスは最大1分ほどかかります）
        </div>
      )}

      <nav className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "predict"}
          className={activeTab === "predict" ? "active" : ""}
          onClick={() => setActiveTab("predict")}
        >
          試合予測
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "events"}
          className={activeTab === "events" ? "active" : ""}
          onClick={() => {
            setActiveTab("events");
            if (events.length === 0) fetchEvents();
          }}
        >
          大会一覧
        </button>
      </nav>

      {activeTab === "predict" && (
        <main className="predict-section" role="tabpanel">
          <div className="input-area">
            <div className="org-select" role="group" aria-label="団体選択">
              <button
                className={org === "ufc" ? "active" : ""}
                onClick={() => setOrg("ufc")}
              >
                UFC
              </button>
              <button
                className={org === "rizin" ? "active" : ""}
                onClick={() => setOrg("rizin")}
              >
                RIZIN
              </button>
            </div>

            <div className="fighter-inputs">
              <FighterInput
                value={fighterAName}
                onChange={setFighterAName}
                onSelect={setFighterAName}
                placeholder="選手A（例: Conor）"
                label="選手A"
                org={org}
                onWaking={setWakingUp}
              />
              <span className="vs" aria-hidden="true">VS</span>
              <FighterInput
                value={fighterBName}
                onChange={setFighterBName}
                onSelect={setFighterBName}
                placeholder="選手B（例: Khabib）"
                label="選手B"
                org={org}
                onWaking={setWakingUp}
              />
            </div>

            <button
              className="predict-btn"
              onClick={fetchPrediction}
              disabled={loading}
            >
              {loading ? "分析中..." : "予測する"}
            </button>
          </div>

          {error && <div className="error" role="alert">{error}</div>}

          {prediction && (
            <div className="result">
              <div className="result-badges">
                <div
                  className="confidence-badge"
                  data-level={prediction.confidence}
                >
                  信頼度: {prediction.confidence}
                </div>
                {prediction.method_prediction && (
                  <div className="method-badge">
                    予想決着: {prediction.method_prediction}
                  </div>
                )}
              </div>

              <ProbBar
                nameA={prediction.fighter_a_name}
                nameB={prediction.fighter_b_name}
                probA={prediction.fighter_a_win_prob}
                probB={prediction.fighter_b_win_prob}
              />

              {fighterA && fighterB && (
                <>
                  <div className="fighter-cards">
                    <FighterCard fighter={fighterA} />
                    <FighterCard fighter={fighterB} />
                  </div>

                  <div className="stats-compare">
                    <h3>スタッツ比較</h3>
                    <div className="stats-header">
                      <span>{fighterA.name.split(" ").pop() || fighterA.name}</span>
                      <span></span>
                      <span>{fighterB.name.split(" ").pop() || fighterB.name}</span>
                    </div>
                    <StatCompare label="打撃/分" valA={fighterA.sig_strikes_landed_per_min} valB={fighterB.sig_strikes_landed_per_min} />
                    <StatCompare label="打撃精度" valA={fighterA.sig_strike_accuracy} valB={fighterB.sig_strike_accuracy} format="percent" />
                    <StatCompare label="被弾/分" valA={fighterA.sig_strikes_absorbed_per_min} valB={fighterB.sig_strikes_absorbed_per_min} />
                    <StatCompare label="打撃防御" valA={fighterA.sig_strike_defense} valB={fighterB.sig_strike_defense} format="percent" />
                    <StatCompare label="TD/試合" valA={fighterA.takedown_avg} valB={fighterB.takedown_avg} />
                    <StatCompare label="TD精度" valA={fighterA.takedown_accuracy} valB={fighterB.takedown_accuracy} format="percent" />
                    <StatCompare label="TD防御" valA={fighterA.takedown_defense} valB={fighterB.takedown_defense} format="percent" />
                    <StatCompare label="SUB/試合" valA={fighterA.submission_avg} valB={fighterB.submission_avg} />
                  </div>
                </>
              )}

              <div className="factors">
                <h3>予測根拠</h3>
                <ul>
                  {prediction.factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>

              <WatchBanner org={org} />
            </div>
          )}
        </main>
      )}

      {activeTab === "events" && (
        <main className="events-section" role="tabpanel">
          {eventsLoading ? (
            <p className="loading-text">読み込み中...</p>
          ) : events.length === 0 ? (
            <p className="loading-text">大会情報が見つかりません</p>
          ) : (
            <div className="events-list">
              {events.map((event, i) => (
                <div key={`${event.name}-${i}`} className="event-card">
                  <span className="event-org">{event.organization}</span>
                  <h3>{event.name}</h3>
                  <p>{event.date}</p>
                </div>
              ))}
            </div>
          )}
        </main>
      )}
      <footer className="app-footer">
        <div className="footer-links">
          <a href={AFFILIATE_LINKS.ufc.url} target="_blank" rel="noopener noreferrer">
            U-NEXTでUFCを観る
          </a>
          <span className="footer-sep">|</span>
          <a href={AFFILIATE_LINKS.rizin.url} target="_blank" rel="noopener noreferrer">
            ABEMAでRIZINを観る
          </a>
        </div>
        <p className="footer-copy">&copy; 2026 FIGHT PREDICT</p>
      </footer>
    </div>
  );
}

export default App;
