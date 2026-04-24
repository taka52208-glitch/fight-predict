import { useEffect, useRef } from "react";

// =====================================================
// AdSense広告ユニット統合管理
// =====================================================
// 運用手順:
// 1. AdSenseで承認されたら、下の ADS_ENABLED を true にする
// 2. AdSenseダッシュボードで各placementに対応する広告ユニットを作成し
//    AD_SLOTS のプレースホルダーIDを実際の slot ID に差し替える
// 3. git commit & push で Vercel 自動デプロイ
//
// 開発時の配置確認:
// - index.html に <meta name="ads-debug" content="true"> を追加すると
//   各広告スロットの位置が点線枠でビジュアライズされる
// =====================================================

const ADS_ENABLED = false; // TODO: AdSense承認後に true に変更
const AD_CLIENT = "ca-pub-3165615110181779";

// プレースホルダーID（TODO: AdSense承認後に実slotIDに差し替え）
const AD_SLOTS = {
  "home-top": "0000000001",
  "home-result": "0000000002",
  "home-bottom": "0000000003",
  "article-top": "0000000004",
  "article-bottom": "0000000005",
  "content-bottom": "0000000006",
} as const;

type Placement = keyof typeof AD_SLOTS;

interface AdSlotProps {
  placement: Placement;
  format?: "auto" | "fluid" | "rectangle";
}

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[];
  }
}

function isDebugMode(): boolean {
  if (typeof document === "undefined") return false;
  const meta = document.querySelector('meta[name="ads-debug"]');
  return meta?.getAttribute("content") === "true";
}

export function AdSlot({ placement, format = "auto" }: AdSlotProps) {
  const insRef = useRef<HTMLModElement>(null);

  useEffect(() => {
    if (!ADS_ENABLED) return;
    if (!insRef.current) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // AdSenseスクリプト未ロード時（広告ブロッカー等）は無視
    }
  }, [placement]);

  if (!ADS_ENABLED) {
    if (isDebugMode()) {
      return (
        <div className="ad-slot-debug" data-placement={placement}>
          <span className="ad-slot-debug-label">AD SLOT</span>
          <span className="ad-slot-debug-name">{placement}</span>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="ad-slot" data-placement={placement}>
      <ins
        ref={insRef}
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={AD_CLIENT}
        data-ad-slot={AD_SLOTS[placement]}
        data-ad-format={format}
        data-full-width-responsive="true"
      />
    </div>
  );
}
