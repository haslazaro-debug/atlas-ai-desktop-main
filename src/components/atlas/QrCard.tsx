import { Send } from "lucide-react";
import QRCode from "react-qr-code";

export function QrCard({ caption, url }: { caption: string; url?: string | null }) {
  return (
    <div className="flex flex-col items-center gap-2.5">
      <div className="flex h-[8.75rem] w-[8.75rem] items-center justify-center rounded-xl border border-dashed border-white/10 bg-neutral-900/40 p-2 overflow-hidden">
        <div className="w-full h-full bg-white p-1 rounded-lg">
          <QRCode value={url || "https://t.me/atlas_ai_bot"} size={256} style={{ height: "auto", maxWidth: "100%", width: "100%" }} />
        </div>
      </div>
      <p className="max-w-[9rem] text-center text-[10px] leading-tight text-neutral-500">
        {caption}
      </p>
    </div>
  );
}
