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

type PredictionRecord = {
  id: string;
  timestamp: string;
  fighter_a_name: string;
  fighter_b_name: string;
  fighter_a_win_prob: number;
  fighter_b_win_prob: number;
  predicted_winner: string;
  confidence: string;
  method_prediction: string;
  organization: string;
  actual_winner: string | null;
  is_correct: boolean | null;
};

type AccuracyStats = {
  total: number;
  correct: number;
  accuracy: number;
  by_confidence: Record<string, { total: number; correct: number; accuracy: number }>;
  recent: PredictionRecord[];
};

type EventPrediction = {
  fight: {
    event_name: string;
    event_date: string;
    fighter_a: string;
    fighter_b: string;
    weight_class: string;
    organization: string;
  };
  fighter_a_name: string;
  fighter_b_name: string;
  fighter_a_win_prob: number;
  fighter_b_win_prob: number;
  confidence: string;
  factors: string[];
  method_prediction: string;
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

const AFFILIATE_LINKS = {
  ufc: {
    name: "楽天市場",
    url: "https://hb.afl.rakuten.co.jp/ichiba/52d0c10b.15007868.52d0c10c.adcd60ec/?pc=https%3A%2F%2Fitem.rakuten.co.jp%2Fr-isamishop%2Fuo%2F&link_type=hybrid_url&ut=eyJwYWdlIjoiaXRlbSIsInR5cGUiOiJoeWJyaWRfdXJsIiwic2l6ZSI6IjI0MHgyNDAiLCJuYW0iOjEsIm5hbXAiOiJyaWdodCIsImNvbSI6MSwiY29tcCI6ImRvd24iLCJwcmljZSI6MSwiYm9yIjoxLCJjb2wiOjEsImJidG4iOjEsInByb2QiOjAsImFtcCI6ZmFsc2V9",
    description: "UFCファイター愛用の格闘技ギアを楽天市場でチェック",
    cta: "格闘技ギアを見る",
    label: "この試合に触発されたら",
    footerText: "楽天で格闘技ギアを探す",
  },
  rizin: {
    name: "ABEMA",
    url: "https://abema.tv/subscription/lp/183c3ec2-c6d8-409e-80b6-caf5a8012f8a?utm_medium=ads&utm_source=afb&_fsi=MFfhS4ax",
    description: "RIZINの試合をライブ配信中",
    cta: "ABEMAで観る",
    label: "この試合を観るなら",
    footerText: "ABEMAでRIZINを観る",
  },
} as const;

function generateShareImage(pred: Prediction): Promise<Blob> {
  return new Promise((resolve) => {
    const W = 1200, H = 630;
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d")!;

    // Background
    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, W, H);

    // Top accent line
    const grad = ctx.createLinearGradient(0, 0, W, 0);
    grad.addColorStop(0, "#e53e3e");
    grad.addColorStop(1, "#d69e2e");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, 6);

    // Title
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 36px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("FIGHT PREDICT", W / 2, 60);

    // Fighter names
    ctx.font = "bold 48px sans-serif";
    const nameA = pred.fighter_a_name;
    const nameB = pred.fighter_b_name;
    ctx.fillStyle = "#e53e3e";
    ctx.textAlign = "right";
    ctx.fillText(nameA, W / 2 - 40, 160);
    ctx.fillStyle = "#3182ce";
    ctx.textAlign = "left";
    ctx.fillText(nameB, W / 2 + 40, 160);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 32px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("VS", W / 2, 155);

    // Probability bar
    const barY = 200, barH = 60, barX = 100, barW = W - 200;
    const pctA = Math.round(pred.fighter_a_win_prob * 100);
    const pctB = Math.round(pred.fighter_b_win_prob * 100);
    const splitX = barX + barW * pred.fighter_a_win_prob;

    // Rounded bar background
    ctx.beginPath();
    ctx.roundRect(barX, barY, barW, barH, 10);
    ctx.clip();
    ctx.fillStyle = "#e53e3e";
    ctx.fillRect(barX, barY, splitX - barX, barH);
    ctx.fillStyle = "#3182ce";
    ctx.fillRect(splitX, barY, barX + barW - splitX, barH);
    ctx.restore();
    ctx.save();

    // Bar text
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 28px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${pctA}%`, barX + (splitX - barX) / 2, barY + 40);
    ctx.fillText(`${pctB}%`, splitX + (barX + barW - splitX) / 2, barY + 40);

    // Confidence & Method
    ctx.font = "24px sans-serif";
    ctx.fillStyle = "#d69e2e";
    ctx.textAlign = "center";
    ctx.fillText(`信頼度: ${pred.confidence}　|　予想決着: ${pred.method_prediction}`, W / 2, 320);

    // Factors (up to 4)
    ctx.font = "20px sans-serif";
    ctx.fillStyle = "#c8c8d0";
    ctx.textAlign = "left";
    const displayFactors = pred.factors.filter(f => !f.startsWith("※")).slice(0, 4);
    displayFactors.forEach((f, i) => {
      ctx.fillText(`• ${f}`, 120, 380 + i * 36);
    });

    // Footer
    ctx.fillStyle = "#555";
    ctx.font = "18px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("fight-predict.vercel.app", W / 2, H - 30);

    canvas.toBlob((blob) => resolve(blob!), "image/png");
  });
}

async function shareToX(pred: Prediction) {
  const pctA = Math.round(pred.fighter_a_win_prob * 100);
  const pctB = Math.round(pred.fighter_b_win_prob * 100);
  const winner = pctA >= pctB ? pred.fighter_a_name : pred.fighter_b_name;
  const text = `🥊 ${pred.fighter_a_name} vs ${pred.fighter_b_name}\n\n勝者予測: ${winner}\n${pred.fighter_a_name} ${pctA}% - ${pctB}% ${pred.fighter_b_name}\n信頼度: ${pred.confidence} | 決着: ${pred.method_prediction}\n\n#FightPredict #格闘技予測`;
  const url = "https://fight-predict-takas-projects-de61dd0f.vercel.app";

  // Try Web Share API with image (mobile)
  try {
    const blob = await generateShareImage(pred);
    const file = new File([blob], "fight-predict.png", { type: "image/png" });
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ text, url, files: [file] });
      return;
    }
  } catch {
    // fall through to X intent
  }

  // Fallback: X (Twitter) intent
  const tweetUrl = `https://x.com/intent/tweet?text=${encodeURIComponent(text + "\n" + url)}`;
  window.open(tweetUrl, "_blank", "noopener,noreferrer");
}

function ShareButton({ prediction }: { prediction: Prediction }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownloadImage = async () => {
    setDownloading(true);
    try {
      const blob = await generateShareImage(prediction);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fight-predict-${prediction.fighter_a_name}-vs-${prediction.fighter_b_name}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="share-buttons">
      <button className="share-btn share-x" onClick={() => shareToX(prediction)}>
        Xでシェア
      </button>
      <button className="share-btn share-download" onClick={handleDownloadImage} disabled={downloading}>
        {downloading ? "生成中..." : "画像を保存"}
      </button>
    </div>
  );
}

function WatchBanner({ org }: { org: "ufc" | "rizin" }) {
  const link = AFFILIATE_LINKS[org];
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="watch-banner"
    >
      <span className="watch-banner-label">{link.label}</span>
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
  const [activeTab, setActiveTab] = useState<"predict" | "events" | "accuracy">("predict");
  const [wakingUp, setWakingUp] = useState(false);
  const [eventPredictions, setEventPredictions] = useState<EventPrediction[]>([]);
  const [eventPredLoading, setEventPredLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<UpcomingEvent | null>(null);
  const [accuracyStats, setAccuracyStats] = useState<AccuracyStats | null>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(false);
  const [generatedNote, setGeneratedNote] = useState<{ title: string; free_section: string; paid_section: string; full: string } | null>(null);
  const [generatedXPosts, setGeneratedXPosts] = useState<{ text: string; type: string }[]>([]);
  const [genLoading, setGenLoading] = useState("");

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

  const fetchAccuracy = async () => {
    setAccuracyLoading(true);
    try {
      const res = await fetchWithWakeup(
        `${API_BASE}/api/predictions/accuracy`,
        {},
        setWakingUp
      );
      if (res.ok) {
        setAccuracyStats(await res.json());
      }
    } catch {
      setAccuracyStats(null);
    } finally {
      setAccuracyLoading(false);
    }
  };

  const recordResult = async (predictionId: string, winner: string) => {
    try {
      const res = await fetchWithWakeup(
        `${API_BASE}/api/predictions/${predictionId}/result?winner=${encodeURIComponent(winner)}`,
        { method: "POST" },
        setWakingUp
      );
      if (res.ok) {
        fetchAccuracy(); // refresh
      }
    } catch {
      // ignore
    }
  };

  const generateNote = async (event: UpcomingEvent) => {
    setGenLoading("note");
    try {
      const org = event.organization.toLowerCase();
      const res = await fetchWithWakeup(
        `${API_BASE}/api/generate/note?event_url=${encodeURIComponent(event.url)}&org=${org}`,
        {},
        setWakingUp
      );
      if (res.ok) {
        setGeneratedNote(await res.json());
      }
    } catch {
      setGeneratedNote(null);
    } finally {
      setGenLoading("");
    }
  };

  const generateXPosts = async (event: UpcomingEvent) => {
    setGenLoading("x");
    try {
      const org = event.organization.toLowerCase();
      const res = await fetchWithWakeup(
        `${API_BASE}/api/generate/x-posts?event_url=${encodeURIComponent(event.url)}&org=${org}`,
        {},
        setWakingUp
      );
      if (res.ok) {
        setGeneratedXPosts(await res.json());
      }
    } catch {
      setGeneratedXPosts([]);
    } finally {
      setGenLoading("");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const fetchEventPredictions = async (event: UpcomingEvent) => {
    if (eventPredLoading) return;
    setSelectedEvent(event);
    setEventPredictions([]);
    setEventPredLoading(true);
    try {
      const org = event.organization.toLowerCase();
      const res = await fetchWithWakeup(
        `${API_BASE}/api/predict/event?event_url=${encodeURIComponent(event.url)}&org=${org}`,
        {},
        setWakingUp
      );
      if (res.ok) {
        setEventPredictions(await res.json());
      }
    } catch {
      setEventPredictions([]);
    } finally {
      setEventPredLoading(false);
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
        <button
          role="tab"
          aria-selected={activeTab === "accuracy"}
          className={activeTab === "accuracy" ? "active" : ""}
          onClick={() => {
            setActiveTab("accuracy");
            fetchAccuracy();
          }}
        >
          的中率
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

              <ShareButton prediction={prediction} />
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
                <div key={`${event.name}-${i}`} className="event-card clickable" onClick={() => fetchEventPredictions(event)}>
                  <span className="event-org">{event.organization}</span>
                  <h3>{event.name}</h3>
                  <p>{event.date}</p>
                  <span className="event-predict-hint">クリックで全試合予測 →</span>
                </div>
              ))}
            </div>
          )}

          {selectedEvent && (
            <div className="event-predictions">
              <h2 className="event-pred-title">{selectedEvent.name} — 全試合予測</h2>
              {eventPredLoading ? (
                <p className="loading-text">全試合を分析中...</p>
              ) : eventPredictions.length === 0 ? (
                <p className="loading-text">対戦カードが見つかりません</p>
              ) : (
                <div className="event-pred-list">
                  {eventPredictions.map((ep, i) => {
                    const pctA = Math.round(ep.fighter_a_win_prob * 100);
                    const pctB = Math.round(ep.fighter_b_win_prob * 100);
                    const winner = pctA >= pctB ? ep.fighter_a_name : ep.fighter_b_name;
                    return (
                      <div key={i} className="event-pred-card">
                        <div className="ep-weight">{ep.fight.weight_class}</div>
                        <div className="ep-matchup">
                          <span className={`ep-fighter ${pctA >= pctB ? "ep-winner" : ""}`}>
                            {ep.fighter_a_name}
                          </span>
                          <span className="ep-vs">VS</span>
                          <span className={`ep-fighter ${pctB > pctA ? "ep-winner" : ""}`}>
                            {ep.fighter_b_name}
                          </span>
                        </div>
                        <div className="ep-bar">
                          <div className="ep-bar-a" style={{ width: `${Math.max(pctA, 8)}%` }}>{pctA}%</div>
                          <div className="ep-bar-b" style={{ width: `${Math.max(pctB, 8)}%` }}>{pctB}%</div>
                        </div>
                        <div className="ep-meta">
                          <span className="confidence-badge" data-level={ep.confidence}>{ep.confidence}</span>
                          <span className="method-badge">{ep.method_prediction}</span>
                          <span className="ep-pick">勝者予測: {winner}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="content-gen-section">
                <h3>コンテンツ生成</h3>
                <div className="gen-buttons">
                  <button
                    className="gen-btn gen-note"
                    onClick={() => generateNote(selectedEvent)}
                    disabled={genLoading !== ""}
                  >
                    {genLoading === "note" ? "生成中..." : "📝 note記事を生成"}
                  </button>
                  <button
                    className="gen-btn gen-x"
                    onClick={() => generateXPosts(selectedEvent)}
                    disabled={genLoading !== ""}
                  >
                    {genLoading === "x" ? "生成中..." : "𝕏 X投稿を生成"}
                  </button>
                </div>

                {generatedNote && (
                  <div className="gen-output">
                    <h4>note記事（無料部分）</h4>
                    <pre className="gen-text">{generatedNote.free_section}</pre>
                    <button className="copy-btn" onClick={() => copyToClipboard(generatedNote.free_section)}>コピー</button>
                    <h4>note記事（有料部分）</h4>
                    <pre className="gen-text">{generatedNote.paid_section}</pre>
                    <button className="copy-btn" onClick={() => copyToClipboard(generatedNote.paid_section)}>コピー</button>
                    <button className="copy-btn copy-all" onClick={() => copyToClipboard(generatedNote.full)}>全文コピー</button>
                  </div>
                )}

                {generatedXPosts.length > 0 && (
                  <div className="gen-output">
                    {generatedXPosts.map((post, i) => (
                      <div key={i} className="x-post-preview">
                        <div className="x-post-label">{post.type === "main" ? "メイン投稿" : `カード ${i}`}</div>
                        <pre className="gen-text">{post.text}</pre>
                        <div className="x-post-actions">
                          <button className="copy-btn" onClick={() => copyToClipboard(post.text)}>コピー</button>
                          <a
                            className="copy-btn post-x-btn"
                            href={`https://x.com/intent/tweet?text=${encodeURIComponent(post.text)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Xに投稿
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <WatchBanner org={selectedEvent.organization.toLowerCase() as "ufc" | "rizin"} />
            </div>
          )}
        </main>
      )}
      {activeTab === "accuracy" && (
        <main className="accuracy-section" role="tabpanel">
          {accuracyLoading ? (
            <p className="loading-text">読み込み中...</p>
          ) : !accuracyStats ? (
            <p className="loading-text">データがありません</p>
          ) : (
            <>
              <div className="accuracy-overview">
                <div className="accuracy-big">
                  <span className="accuracy-number">
                    {accuracyStats.total > 0 ? `${Math.round(accuracyStats.accuracy * 100)}%` : "—"}
                  </span>
                  <span className="accuracy-label">総合的中率</span>
                  <span className="accuracy-sub">
                    {accuracyStats.correct} / {accuracyStats.total} 試合
                  </span>
                </div>

                {Object.keys(accuracyStats.by_confidence).length > 0 && (
                  <div className="accuracy-by-conf">
                    {(["HIGH", "MEDIUM", "LOW"] as const).map((level) => {
                      const data = accuracyStats.by_confidence[level];
                      if (!data) return null;
                      return (
                        <div key={level} className="conf-stat">
                          <span className="confidence-badge" data-level={level}>{level}</span>
                          <span className="conf-accuracy">{Math.round(data.accuracy * 100)}%</span>
                          <span className="conf-count">({data.correct}/{data.total})</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {accuracyStats.recent.length > 0 && (
                <div className="accuracy-history">
                  <h3>予測履歴</h3>
                  {accuracyStats.recent.map((rec) => (
                    <div key={rec.id} className={`history-card ${rec.is_correct === true ? "correct" : rec.is_correct === false ? "incorrect" : "pending"}`}>
                      <div className="history-matchup">
                        <span className="history-org">{rec.organization}</span>
                        <span>{rec.fighter_a_name} vs {rec.fighter_b_name}</span>
                      </div>
                      <div className="history-detail">
                        <span>予測: {rec.predicted_winner} ({Math.round(Math.max(rec.fighter_a_win_prob, rec.fighter_b_win_prob) * 100)}%)</span>
                        <span className="confidence-badge" data-level={rec.confidence}>{rec.confidence}</span>
                      </div>
                      {rec.actual_winner !== null ? (
                        <div className="history-result">
                          結果: {rec.actual_winner}勝利 — {rec.is_correct ? "✓ 的中" : "✗ 不的中"}
                        </div>
                      ) : (
                        <div className="history-actions">
                          <span className="history-pending">結果未入力</span>
                          <button className="result-btn" onClick={() => recordResult(rec.id, rec.fighter_a_name)}>
                            {rec.fighter_a_name}勝利
                          </button>
                          <button className="result-btn" onClick={() => recordResult(rec.id, rec.fighter_b_name)}>
                            {rec.fighter_b_name}勝利
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </main>
      )}

      <footer className="app-footer">
        <div className="footer-links">
          <a href={AFFILIATE_LINKS.ufc.url} target="_blank" rel="noopener noreferrer">
            {AFFILIATE_LINKS.ufc.footerText}
          </a>
          <span className="footer-sep">|</span>
          <a href={AFFILIATE_LINKS.rizin.url} target="_blank" rel="noopener noreferrer">
            {AFFILIATE_LINKS.rizin.footerText}
          </a>
        </div>
        <p className="footer-copy">&copy; 2026 FIGHT PREDICT</p>
      </footer>
    </div>
  );
}

export default App;
