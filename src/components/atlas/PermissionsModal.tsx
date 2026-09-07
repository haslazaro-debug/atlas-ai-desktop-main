import { useState } from "react";
import { motion } from "framer-motion";
import { Accessibility, Check, Mic, MonitorPlay } from "lucide-react";

const PERMS = [
  {
    id: "accessibility",
    icon: Accessibility,
    title: "Accessibility Control",
    hint: "For keyboard/mouse actions",
  },
  {
    id: "screen",
    icon: MonitorPlay,
    title: "Screen Recording",
    hint: "For vision model analysis",
  },
  {
    id: "mic",
    icon: Mic,
    title: "Microphone Input",
    hint: "For voice command capture",
  },
] as const;

export function PermissionsModal({ onComplete }: { onComplete: () => void }) {
  const [granted, setGranted] = useState<Record<string, boolean>>({});
  const all = PERMS.every((p) => granted[p.id]);

  return (
    <motion.div
      layout
      className="atlas-specular w-full max-w-md rounded-2xl border border-white/10 bg-neutral-950/70 p-6 shadow-2xl shadow-black/80 backdrop-blur-2xl"
    >
      <h2 className="text-sm font-medium text-neutral-200">System Permissions Required</h2>
      <p className="mt-1 text-[11px] text-neutral-500">
        ATLAS needs these macOS permissions to control your desktop.
      </p>

      <div className="mt-5 space-y-2.5">
        {PERMS.map(({ id, icon: Icon, title, hint }) => (
          <div
            key={id}
            className="flex items-center justify-between gap-4 rounded-xl border border-white/5 bg-neutral-900/50 px-3.5 py-3"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] text-neutral-300">
                <Icon size={14} />
              </span>
              <div>
                <p className="text-xs font-medium text-neutral-200">{title}</p>
                <p className="mt-0.5 text-[10px] text-neutral-500">{hint}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setGranted((g) => ({ ...g, [id]: true }))}
              className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-[10px] transition-colors ${
                granted[id]
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                  : "border-white/10 bg-white/[0.05] text-neutral-300 hover:bg-white/[0.1] hover:text-white"
              }`}
            >
              {granted[id] ? (
                <span className="inline-flex items-center gap-1">
                  <Check size={10} /> Granted
                </span>
              ) : (
                "Grant Access"
              )}
            </button>
          </div>
        ))}
      </div>

      <motion.button
        layout
        type="button"
        onClick={onComplete}
        className={`mt-5 w-full rounded-xl px-4 py-2.5 text-xs font-medium transition-colors ${
          all
            ? "bg-white text-black hover:bg-neutral-200"
            : "border border-white/10 bg-white/[0.06] text-neutral-400 hover:bg-white/[0.1] hover:text-white"
        }`}
      >
        Complete Setup & Launch ATLAS
      </motion.button>
    </motion.div>
  );
}
