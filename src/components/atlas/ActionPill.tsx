import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Copy, Loader2, Pause, Volume2, X } from "lucide-react";

type ActionPillData = {
  text: string;
  error?: string | undefined;
  audio_url?: string | undefined;
  isProcessing?: boolean | undefined;
  processingStep?: number | undefined;
  processingSteps?: string[] | undefined;
  requires_confirmation?: boolean | undefined;
  action_type?: string | undefined;
};

import { sendCommand } from "@/lib/api";

function MarkdownText({ text }: { text: string }) {
  if (text.includes("<b>") || text.includes("<i>") || text.includes("⚡") || text.includes("<br>")) {
    return <div dangerouslySetInnerHTML={{ __html: text.replace(/\n/g, '<br/>') }} className="space-y-3 font-sans" />;
  }

  const blocks = useMemo(
    () =>
      text
        .split(/\n{2,}/)
        .map((block) => block.trim())
        .filter(Boolean),
    [text],
  );

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => {
        if (block.startsWith("```")) {
          const code = block.replace(/^```[a-zA-Z]*\n?/, "").replace(/```$/, "");
          return (
            <pre
              key={index}
              className="overflow-x-auto rounded-lg border border-white/10 bg-black/40 p-3 text-xs text-neutral-200"
            >
              <code>{code}</code>
            </pre>
          );
        }

        if (/^[-*]\s+/m.test(block)) {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.split("\n").map((line) => (
                <li key={line}>{line.replace(/^[-*]\s+/, "")}</li>
              ))}
            </ul>
          );
        }

        if (/^\d+\.\s+/m.test(block)) {
          return (
            <ol key={index} className="list-decimal space-y-1 pl-5">
              {block.split("\n").map((line) => (
                <li key={line}>{line.replace(/^\d+\.\s+/, "")}</li>
              ))}
            </ol>
          );
        }

        if (block.startsWith("### ")) {
          return (
            <h3 key={index} className="text-sm font-semibold text-white">
              {block.replace(/^###\s+/, "")}
            </h3>
          );
        }

        if (block.startsWith("## ")) {
          return (
            <h2 key={index} className="text-base font-semibold text-white">
              {block.replace(/^##\s+/, "")}
            </h2>
          );
        }

        if (block.startsWith("# ")) {
          return (
            <h2 key={index} className="text-base font-semibold text-white">
              {block.replace(/^#\s+/, "")}
            </h2>
          );
        }

        return (
          <p key={index} className="whitespace-pre-wrap">
            {block.replace(/\*\*(.*?)\*\*/g, "$1").replace(/`([^`]+)`/g, "$1")}
          </p>
        );
      })}
    </div>
  );
}

function PlaybackWave({ active }: { active: boolean }) {
  return (
    <span className="flex h-4 items-center gap-[2px]" aria-hidden="true">
      {[0.45, 0.8, 0.55, 1, 0.65].map((scale, index) => (
        <span
          key={index}
          className="w-[2px] rounded-full bg-white/70"
          style={{
            height: `${10 + scale * 8}px`,
            animation: active ? "atlas-wave 0.55s ease-in-out infinite" : "none",
            animationDelay: `${index * 70}ms`,
            ["--bar-scale" as string]: scale,
          }}
        />
      ))}
    </span>
  );
}

export function ActionPill({ data, onEscape, onUpdate }: { data?: ActionPillData; onEscape: () => void; onUpdate?: (data: ActionPillData) => void }) {
  const [open, setOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isProcessing = data?.isProcessing ?? false;
  const isError = !!data?.error;
  const steps = data?.processingSteps ?? [];
  const activeStep = data?.processingStep ?? 0;
  
  const handleConfirmAction = async (command: string) => {
    if (onUpdate) {
      onUpdate({ text: "Processing...", isProcessing: true });
      const res = await sendCommand(command);
      onUpdate({ text: res.response || res.text || "", audio_url: res.audio, isProcessing: false, requires_confirmation: false });
    }
  };

  const copyText = () => {
    if (data?.text) {
      void navigator.clipboard.writeText(data.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  };

  const playTTS = (textToSpeak: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel(); // Stop current speech
    
    // Clean markdown
    const cleanText = textToSpeak.replace(/[*_#`]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = /[а-яА-ЯЁё]/.test(cleanText) ? "ru-RU" : "en-US";
    
    utterance.onstart = () => setPlaying(true);
    utterance.onend = () => setPlaying(false);
    utterance.onerror = () => setPlaying(false);
    
    window.speechSynthesis.speak(utterance);
  };

  // Auto-play when response is ready
  useEffect(() => {
    if (!isProcessing && !isError && data?.text && open) {
      if (!data.audio_url) {
        playTTS(data.text);
      }
    }
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isProcessing, isError, data?.text]); // Removed 'open' to prevent re-triggering when collapsing

  const replayAudio = async () => {
    if (playing) {
      window.speechSynthesis.cancel();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setPlaying(false);
      return;
    }

    if (data?.audio_url) {
      const audio = audioRef.current ?? new Audio();
      audioRef.current = audio;
      audio.src = data.audio_url;
      audio.onplay = () => setPlaying(true);
      audio.onpause = () => setPlaying(false);
      audio.onended = () => setPlaying(false);
      try {
        await audio.play();
      } catch (error) {
        console.error("Audio replay error:", error);
        setPlaying(false);
      }
    } else if (data?.text) {
      playTTS(data.text);
    }
  };

  const handleClose = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setPlaying(false);
    }
    onEscape();
  };

  return (
    <motion.div
      layout
      initial={{ y: -24, opacity: 0, scale: 0.96 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: -24, opacity: 0, scale: 0.96 }}
      transition={{ type: "spring", stiffness: 520, damping: 38 }}
      className={`atlas-specular relative w-full max-w-2xl overflow-hidden border border-white/10 bg-neutral-950/90 shadow-2xl shadow-black/80 backdrop-blur-2xl ${
        open ? "rounded-3xl" : "rounded-full"
      }`}
    >
      <motion.div layout className="atlas-radar relative flex items-center gap-3 px-5 py-3">
        {isProcessing ? (
          <Loader2 size={14} className="animate-spin text-neutral-300" />
        ) : isError ? (
          <X size={14} className="text-red-400" />
        ) : (
          <span className="atlas-pulse-dot relative z-10" />
        )}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className={`relative z-10 flex min-w-0 flex-1 items-center gap-2 text-left font-mono text-xs ${
            isError ? "text-red-400" : "text-neutral-200"
          }`}
        >
          <span className="truncate">
            {isProcessing ? data?.text : isError ? `Error: ${data?.error}` : "ATLAS Response"}
          </span>
          <motion.span animate={{ rotate: open ? 180 : 0 }} className="shrink-0 text-neutral-500">
            <ChevronDown size={12} />
          </motion.span>
        </button>
        <button
          type="button"
          onClick={handleClose}
          className="relative z-10 rounded-full border border-white/10 bg-white/[0.04] p-1.5 text-neutral-400 transition-colors hover:bg-white/10 hover:text-white"
          aria-label="Close"
        >
          <X size={13} />
        </button>
      </motion.div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="log"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 420, damping: 40 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/10 px-5 pb-5 pt-4">
              {isProcessing ? (
                <div className="space-y-2">
                  {steps.map((step, index) => (
                    <div
                      key={step}
                      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-colors ${
                        index === activeStep
                          ? "border-white/20 bg-white/[0.07] text-white"
                          : index < activeStep
                            ? "border-emerald-400/20 bg-emerald-400/[0.05] text-emerald-200"
                            : "border-white/10 bg-white/[0.03] text-neutral-500"
                      }`}
                    >
                      {index < activeStep ? (
                        <Check size={13} />
                      ) : (
                        <Loader2 size={13} className={index === activeStep ? "animate-spin" : ""} />
                      )}
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="prose prose-invert max-w-none text-sm leading-relaxed text-neutral-300">
                  <MarkdownText text={data?.error ? data.error : (data?.text ?? "")} />
                </div>
              )}

              {!isProcessing && (
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  {data?.requires_confirmation && (
                    <>
                      <button
                        type="button"
                        onClick={() => void handleConfirmAction("да")}
                        className="rounded-full border border-emerald-500/30 bg-emerald-500/[0.15] px-4 py-1.5 font-semibold text-xs text-emerald-200 transition-colors hover:bg-emerald-500/[0.25] hover:text-emerald-100"
                      >
                        Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleConfirmAction("отмена")}
                        className="rounded-full border border-red-500/30 bg-red-500/[0.1] px-4 py-1.5 font-medium text-xs text-red-200 transition-colors hover:bg-red-500/[0.2] hover:text-red-100 mr-2"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                  {data?.audio_url && !isError && (
                    <button
                      type="button"
                      onClick={() => void replayAudio()}
                      className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 font-mono text-[10px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white"
                    >
                      {playing ? <Pause size={12} /> : <Volume2 size={12} />}
                      <PlaybackWave active={playing} />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={copyText}
                    className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 font-mono text-[10px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                  <button
                    type="button"
                    onClick={handleClose}
                    className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 font-mono text-[10px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white"
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
