import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  org,
}: {
  value: string;
  onChange: (v: string) => void;
  onSelect: (name: string) => void;
  placeholder: string;
  org: string;
}) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const abortRef = useRef<AbortController | null>(null);

  const fetchSuggestions = useCallback(
    async (q: string) => {
      // Cancel any in-flight request
      if (abortRef.current) {
        abortRef.current.abort();
      }

      // Japanese characters are meaningful even at 1 char
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
        const res = await fetch(
          `${API_BASE}/api/suggest?q=${encodeURIComponent(q)}&org=${org}`,
          { signal: controller.signal }
        );
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
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
    [org]
  );

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

    // Shorter delay for Japanese input
    const isJapanese = /[\u3000-\u9fff\uff00-\uffef]/.test(v);
    timerRef.current = setTimeout(() => fetchSuggestions(v), isJapanese ? 150 : 200);
  };

  const handleSelect = (name: string) => {
    onChange(name);
    onSelect(name);
    setShowSuggestions(false);
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
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
      />
      {loading && <span className="input-spinner" />}
      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions">
          {suggestions.map((s, i) => (
            <div
              key={i}
              className="suggestion-item"
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
        <div className="prob-bar-a" style={{ width: `${pctA}%` }}>
          {pctA}%
        </div>
        <div className="prob-bar-b" style={{ width: `${pctB}%` }}>
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
  const displayA = format === "percent" ? `${Math.round(valA * 100)}%` : valA.toFixed(1);
  const displayB = format === "percent" ? `${Math.round(valB * 100)}%` : valB.toFixed(1);
  const betterA = valA > valB;
  const betterB = valB > valA;

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

function App() {
  const [fighterAName, setFighterAName] = useState("");
  const [fighterBName, setFighterBName] = useState("");
  const [org, setOrg] = useState("ufc");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [fighterA, setFighterA] = useState<Fighter | null>(null);
  const [fighterB, setFighterB] = useState<Fighter | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"predict" | "events">("predict");

  const fetchPrediction = async () => {
    if (!fighterAName.trim() || !fighterBName.trim()) {
      setError("両方の選手名を入力してください");
      return;
    }

    setLoading(true);
    setError("");
    setPrediction(null);
    setFighterA(null);
    setFighterB(null);

    try {
      const [predRes, faRes, fbRes] = await Promise.all([
        fetch(
          `${API_BASE}/api/predict?fighter_a=${encodeURIComponent(fighterAName)}&fighter_b=${encodeURIComponent(fighterBName)}&org=${org}`
        ),
        fetch(
          `${API_BASE}/api/fighter/${encodeURIComponent(fighterAName)}?org=${org}`
        ),
        fetch(
          `${API_BASE}/api/fighter/${encodeURIComponent(fighterBName)}?org=${org}`
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
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const fetchEvents = async () => {
    setEventsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/events/upcoming?org=all`);
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

      <nav className="tabs">
        <button
          className={activeTab === "predict" ? "active" : ""}
          onClick={() => setActiveTab("predict")}
        >
          試合予測
        </button>
        <button
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
        <main className="predict-section">
          <div className="input-area">
            <div className="org-select">
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
                org={org}
              />
              <span className="vs">VS</span>
              <FighterInput
                value={fighterBName}
                onChange={setFighterBName}
                onSelect={setFighterBName}
                placeholder="選手B（例: Khabib）"
                org={org}
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

          {error && <div className="error">{error}</div>}

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
                      <span>{fighterA.name.split(" ").pop()}</span>
                      <span></span>
                      <span>{fighterB.name.split(" ").pop()}</span>
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
            </div>
          )}
        </main>
      )}

      {activeTab === "events" && (
        <main className="events-section">
          {eventsLoading ? (
            <p className="loading-text">読み込み中...</p>
          ) : events.length === 0 ? (
            <p className="loading-text">大会情報が見つかりません</p>
          ) : (
            <div className="events-list">
              {events.map((event, i) => (
                <div key={i} className="event-card">
                  <span className="event-org">{event.organization}</span>
                  <h3>{event.name}</h3>
                  <p>{event.date}</p>
                </div>
              ))}
            </div>
          )}
        </main>
      )}
    </div>
  );
}

export default App;
