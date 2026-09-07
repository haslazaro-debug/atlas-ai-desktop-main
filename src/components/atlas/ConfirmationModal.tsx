import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ShieldCheck } from "lucide-react";

export function ConfirmationModal({ onClose }: { onClose: () => void }) {
  const [sent, setSent] = useState(false);

  const confirm = () => {
    setSent(true);
    window.setTimeout(onClose, 900);
  };

  return (
    <motion.div
      layout
      className="atlas-specular w-full max-w-md rounded-2xl border border-white/10 bg-neutral-950/70 p-6 shadow-2xl shadow-black/80 backdrop-blur-2xl"
    >
      <AnimatePresence mode="wait">
        {sent ? (
          <motion.div
            key="done"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 520, damping: 38 }}
            className="flex flex-col items-center gap-3 py-8"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full border border-emerald-400/25 bg-emerald-400/10">
              <Check size={20} className="text-emerald-300" />
            </span>
            <p className="text-sm font-medium text-emerald-300">Action approved</p>
          </motion.div>
        ) : (
          <motion.div
            key="confirm"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 520, damping: 38 }}
          >
            <h2 className="text-center text-sm font-medium text-neutral-300">
              ATLAS AI - Action Confirmation
            </h2>

            <div className="mt-5 flex items-start gap-3 rounded-xl border border-white/5 bg-neutral-900/50 p-4">
              <ShieldCheck size={18} className="mt-0.5 shrink-0 text-neutral-300" />
              <p className="text-sm leading-relaxed text-neutral-400">
                ATLAS is waiting for approval before continuing this sensitive action.
              </p>
            </div>

            <div className="mt-5 flex gap-3">
              <button
                type="button"
                onClick={confirm}
                className="flex-1 rounded-xl bg-white px-4 py-2.5 text-sm font-medium text-black transition-colors hover:bg-neutral-200"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 rounded-xl border border-white/10 bg-neutral-900 px-4 py-2.5 text-sm text-neutral-400 transition-colors hover:text-white"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
