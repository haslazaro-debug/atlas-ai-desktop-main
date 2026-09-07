import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Mic, MicOff, Settings, Zap } from "lucide-react";
import { sendCommand, transcribeAudio, type AgentMode } from "@/lib/api";

const BARS_COUNT = 20;

const WAKE_REPLIES: Record<string, string> = {
  "папочка дома": "Добро пожаловать, сэр. Все системы в боевой готовности.",
  "папочка вернулся": "Добро пожаловать, сэр. Все системы в боевой готовности.",
  "подъем": "На связи. Жду указаний.",
  "на базу": "На связи. Жду указаний.",
  "hey atlas": "Слушаю вас.",
  "эй атлас": "Слушаю вас.",
  "джарвис": "Всегда к вашим услугам."
};

const PROCESSING_STEPS = [
  "Analyzing request...",
  "Processing query...",
  "Synthesizing voice...",
];

const INCOMPLETE_ENDINGS = [
  " и", " а", " но", " что", " или", " как", " если", " то", " потому что", " чтобы", " значит", " хотя", " тогда",
  " and", " but", " or", " if", " then", " because", " so", " that", " like"
];

type SpeechRecognitionConstructor = new () => any;

function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  const speechWindow = window as any;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

function playTriggerTone(audioCtx: AudioContext) {
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.12);
  } catch (e) {
    console.warn("Tone play error:", e);
  }
}

function Soundwave({ active, analyser }: { active: boolean; analyser: AnalyserNode | null }) {
  const barsRef = useRef<(HTMLSpanElement | null)[]>([]);

  useEffect(() => {
    let animationId: number;
    const dataArray = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;

    const render = () => {
      if (analyser && dataArray && active) {
        analyser.getByteFrequencyData(dataArray);
        for (let i = 0; i < BARS_COUNT; i++) {
          const binIndex = Math.min(
            Math.floor((i / BARS_COUNT) * dataArray.length),
            dataArray.length - 1
          );
          const rawValue = dataArray[binIndex] || 0;
          const normalized = Math.max(0.1, rawValue / 255);
          const heightPx = Math.max(4, Math.round(normalized * 32));

          const el = barsRef.current[i];
          if (el) {
            el.style.height = `${heightPx}px`;
            el.style.opacity = `${Math.max(0.3, normalized * 1.2)}`;
          }
        }
      } else {
        for (let i = 0; i < BARS_COUNT; i++) {
          const el = barsRef.current[i];
          if (el) {
            el.style.height = "4px";
            el.style.opacity = active ? "0.4" : "0.2";
          }
        }
      }
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, [active, analyser]);

  return (
    <div className="mt-2 flex h-8 items-center justify-center gap-[3px]">
      {Array.from({ length: BARS_COUNT }).map((_, i) => (
        <span
          key={i}
          ref={(el) => {
            barsRef.current[i] = el;
          }}
          className="w-[3px] rounded-full bg-white transition-[height] duration-75"
          style={{ height: "4px" }}
        />
      ))}
    </div>
  );
}

function Badge({
  children,
  onClick,
  tooltip,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  tooltip?: string;
  className?: string;
}) {
  return (
    <div className="group relative">
      <button
        type="button"
        onClick={onClick}
        className={`inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-medium tracking-tight transition-colors hover:border-white/20 hover:bg-white/[0.09] ${className}`}
      >
        {children}
      </button>
      {tooltip && (
        <span className="pointer-events-none absolute right-0 top-full z-20 mt-1.5 whitespace-nowrap rounded-md border border-white/10 bg-neutral-950/90 px-2 py-1 text-[10px] text-neutral-300 opacity-0 shadow-xl shadow-black/60 backdrop-blur-xl transition-opacity duration-150 group-hover:opacity-100">
          {tooltip}
        </span>
      )}
    </div>
  );
}

export function CommandBar({
  onOpenSettings,
  onStartTask,
}: {
  onOpenSettings: (tab?: "API Keys (BYOK)" | "Integrations" | "Audio") => void;
  onStartTask: (data: {
    text: string;
    error?: string;
    audio_url?: string;
    isProcessing?: boolean;
    processingStep?: number;
    processingSteps?: string[];
    requires_confirmation?: boolean;
    action_type?: string;
  }) => void;
}) {
  const [listening, setListening] = useState(false);
  const [vision, setVision] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const taskAbortRef = useRef<AbortController | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const processingTimersRef = useRef<number[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const lastClapTimeRef = useRef<number>(0);
  const wakeRecognitionRef = useRef<any>(null);

  const unlockAudio = useCallback(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "auto";
    }
    audioRef.current.muted = false;
  }, []);

  const clearProcessingTimers = useCallback(() => {
    processingTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    processingTimersRef.current = [];
  }, []);

  const showProcessing = useCallback(
    (step = 0, steps = PROCESSING_STEPS) => {
      onStartTask({
        text: steps[step] ?? steps[0] ?? "Processing...",
        isProcessing: true,
        processingStep: step,
        processingSteps: steps,
      });
    },
    [onStartTask]
  );

  const scheduleProcessing = useCallback((inputText: string = "") => {
    clearProcessingTimers();
    let steps = PROCESSING_STEPS;
    const lower = inputText.toLowerCase();
    if (lower.includes("бриф") || lower.includes("recon") || lower.includes("дайджест") || lower.includes("сводк")) {
      steps = [
        "Analyzing request...",
        "Сбор данных и анализ лент...",
        "Формирование сводки...",
      ];
    }
    showProcessing(0, steps);
    processingTimersRef.current = [
      window.setTimeout(() => showProcessing(1, steps), 800),
      window.setTimeout(() => showProcessing(2, steps), 4000),
    ];
  }, [clearProcessingTimers, showProcessing]);

  // Forward ref declarations to prevent TDZ ReferenceErrors
  const startRecordingRef = useRef<(() => Promise<void>) | null>(null);
  const stopRecordingRef = useRef<(() => void) | null>(null);

  const playResponseAudio = useCallback(
    async (audioUrl?: string, promptText?: string) => {
      if (!audioUrl) return;
      unlockAudio();
      const audio = audioRef.current ?? new Audio();
      audioRef.current = audio;
      audio.src = audioUrl;

      // Auto-listen if the response contains a clarifying question
      audio.onended = () => {
        if (promptText && (promptText.includes("?") || promptText.toLowerCase().includes("уточните"))) {
          void startRecordingRef.current?.();
        }
      };

      try {
        await audio.play();
      } catch (error) {
        console.error("Audio playback error:", error);
      }
    },
    [unlockAudio]
  );

  const finishTask = useCallback(
    async (res: Awaited<ReturnType<typeof sendCommand>>) => {
      clearProcessingTimers();
      taskAbortRef.current = null;

      if (res.error) {
        onStartTask({ text: "Error", error: res.error });
        return;
      }

      const payload: any = { text: res.text, isProcessing: false, requires_confirmation: (res as any).requires_confirmation, action_type: (res as any).action_type };
      if (res.audio) payload.audio_url = res.audio;
      onStartTask(payload);
      await playResponseAudio(res.audio, res.text);
    },
    [clearProcessingTimers, onStartTask, playResponseAudio]
  );

  const runTextCommand = useCallback(
    async (command: string, mode: AgentMode = vision ? "vision_screen" : "text") => {
      const trimmed = command.trim();
      if (!trimmed) {
        setListening(false);
        return;
      }

      unlockAudio();
      setListening(false);
      taskAbortRef.current?.abort();
      const controller = new AbortController();
      taskAbortRef.current = controller;
      scheduleProcessing(trimmed);

      try {
        if (controller.signal.aborted) return;
        const res = await sendCommand(trimmed, mode, null, controller.signal);
        if (!controller.signal.aborted) {
          await finishTask(res);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          clearProcessingTimers();
          taskAbortRef.current = null;
          onStartTask({
            text: "Error",
            error: err instanceof Error ? err.message : "Unknown command error.",
          });
        }
      }
    },
    [clearProcessingTimers, finishTask, onStartTask, scheduleProcessing, unlockAudio, vision]
  );

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setListening(false);
  }, []);

  const startRecording = useCallback(async () => {
    if (mediaRecorderRef.current?.state === "recording") return;
    
    // Barge-in: immediately stop any currently playing voice response
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    unlockAudio();

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone API is not supported in this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const AudioContextCls = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = audioContextRef.current || new AudioContextCls();
      audioContextRef.current = ctx;

      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);

      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      let vadAnimFrame: number;
      let isSpeaking = false;
      let lastSpeechTime = Date.now();
      let hasSpoken = false;
      
      let baselineSum = 0;
      let baselineCount = 0;
      let baseline = 15; // fallback minimum
      const calibrationEnd = Date.now() + 500; // 500ms calibration

      const checkVAD = () => {
        if (recorder.state !== "recording") return;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i]!;
        const avg = sum / dataArray.length;
        
        const now = Date.now();
        
        if (now < calibrationEnd) {
          baselineSum += avg;
          baselineCount++;
          baseline = baselineSum / baselineCount;
          lastSpeechTime = now; // prevent idle timeout during calibration
        } else {
          // Adaptive threshold: slightly above the background baseline
          const threshold = Math.max(15, baseline + 10);
          
          if (avg > threshold) {
            isSpeaking = true;
            hasSpoken = true;
            lastSpeechTime = now;
          } else {
            isSpeaking = false;
          }
          
          // 5 seconds of total silence after mic opens = abort
          if (!hasSpoken && now - lastSpeechTime > 5000) {
            recorder.stop();
            return;
          }
          
          // 1.5s natural pause during speech = submit
          if (hasSpoken && !isSpeaking && now - lastSpeechTime > 1500) {
            recorder.stop();
            return;
          }
        }
        
        vadAnimFrame = requestAnimationFrame(checkVAD);
      };

      recorder.onstop = async () => {
        cancelAnimationFrame(vadAnimFrame);
        setListening(false);
        try {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          if (audioBlob.size < 100) return;

          const controller = new AbortController();
          taskAbortRef.current = controller;
          // scheduleProcessing is handled in runTextCommand later if we have text,
          // but we can start a generic one while transcribing:
          scheduleProcessing();

          const modeToUse = vision ? "vision_screen" : "text";
          const transcribeRes = await transcribeAudio(audioBlob, controller.signal);

          if (!transcribeRes.success || !transcribeRes.text || transcribeRes.text.trim() === "") {
            clearProcessingTimers();
            taskAbortRef.current = null;
            onStartTask({ text: "Речь не распознана, попробуйте снова", isProcessing: false });
            return;
          }

          const existingText = inputRef.current?.value || "";
          const newText = transcribeRes.text.trim();
          const currentText = existingText ? `${existingText} ${newText}` : newText;
          setValue(currentText);

          const textLower = currentText.toLowerCase();
          const isIncomplete = INCOMPLETE_ENDINGS.some(ending => textLower.endsWith(ending)) || textLower.endsWith(",") || textLower.endsWith("...");

          if (isIncomplete) {
            clearProcessingTimers();
            taskAbortRef.current = null;
            onStartTask({ text: "Продолжайте мысль...", isProcessing: false });
            setTimeout(() => {
              void startRecordingRef.current?.();
            }, 150);
            return;
          }

          await runTextCommand(currentText, modeToUse);
        } catch (err) {
          clearProcessingTimers();
          taskAbortRef.current = null;
          onStartTask({
            text: "Error",
            error: err instanceof Error ? err.message : "Audio processing error.",
          });
        } finally {
          stream.getTracks().forEach((track) => track.stop());
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setListening(true);
      checkVAD();
    } catch (err) {
      setListening(false);
      let errorMsg = "Microphone permission denied. Please allow it in the browser settings.";
      if (err instanceof Error && err.name !== "NotAllowedError" && err.message !== "Permission denied") {
        errorMsg = err.message;
      }
      onStartTask({ text: "Error", error: errorMsg });
    }
  }, [clearProcessingTimers, onStartTask, runTextCommand, scheduleProcessing, unlockAudio, vision]);

  startRecordingRef.current = startRecording;
  stopRecordingRef.current = stopRecording;

  // Background Standby Double-Clap & Wake Word Listener
  useEffect(() => {
    let micStream: MediaStream | null = null;
    let animFrame: number;

    const setupStandbyClap = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        micStream = stream;
        const AudioContextCls = window.AudioContext || (window as any).webkitAudioContext;
        const ctx = audioContextRef.current || new AudioContextCls();
        audioContextRef.current = ctx;

        const analyser = ctx.createAnalyser();
        analyser.fftSize = 128;
        const source = ctx.createMediaStreamSource(stream);
        source.connect(analyser);

        const data = new Uint8Array(analyser.frequencyBinCount);

        const checkSpikes = () => {
          if (!listening) {
            analyser.getByteFrequencyData(data);
            let sum = 0;
            for (let i = 0; i < data.length; i++) sum += data[i]!;
            const avg = sum / data.length;

            if (avg > 75) {
              const now = Date.now();
              const diff = now - lastClapTimeRef.current;
              if (diff >= 180 && diff <= 650) {
                lastClapTimeRef.current = 0;
                playTriggerTone(ctx);
                void startRecordingRef.current?.();
              } else {
                lastClapTimeRef.current = now;
              }
            }
          }
          animFrame = requestAnimationFrame(checkSpikes);
        };
        checkSpikes();
      } catch (e) {
        console.warn("Standby mic for clap not granted:", e);
      }
    };

    const SpeechRec = getSpeechRecognition();
    if (SpeechRec) {
      try {
        const rec = new SpeechRec();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "ru-RU";
        rec.onresult = (event: any) => {
          let text = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            text += event.results[i][0].transcript.toLowerCase();
          }
          for (const [phrase, reply] of Object.entries(WAKE_REPLIES)) {
            if (text.includes(phrase)) {
              if (audioContextRef.current) playTriggerTone(audioContextRef.current);
              onStartTask({ text: reply, isProcessing: false });
              void startRecordingRef.current?.();
              break;
            }
          }
        };
        rec.onend = () => {
          if (!listening) {
            try { rec.start(); } catch {}
          }
        };
        rec.start();
        wakeRecognitionRef.current = rec;
      } catch {}
    }

    void setupStandbyClap();

    return () => {
      cancelAnimationFrame(animFrame);
      micStream?.getTracks().forEach((t) => t.stop());
      wakeRecognitionRef.current?.abort();
    };
  }, [listening, onStartTask]);

  const handleSubmit = useCallback(async () => {
    const currentVal = value.trim();
    if (!currentVal) return;
    setValue("");
    await runTextCommand(currentVal);
  }, [runTextCommand, value]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "Enter" && document.activeElement === inputRef.current) {
        e.preventDefault();
        void handleSubmit();
        return;
      }
      if (e.code === "Space" && document.activeElement !== inputRef.current && !e.repeat) {
        e.preventDefault();
        void startRecording();
      }
    };

    const up = (e: KeyboardEvent) => {
      if (e.code === "Space" && document.activeElement !== inputRef.current) {
        e.preventDefault();
        stopRecording();
      }
    };

    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, [handleSubmit, startRecording, stopRecording]);

  return (
    <motion.div layout className="flex w-full max-w-2xl flex-col items-center gap-3">
      <motion.div
        layout
        onClick={() => {
          unlockAudio();
          inputRef.current?.focus();
        }}
        className={`atlas-specular relative flex h-28 w-full cursor-text items-center justify-between gap-6 rounded-[2.5rem] border px-7 shadow-2xl shadow-black/80 backdrop-blur-2xl transition-colors ${
          listening
            ? "border-red-500/40 bg-neutral-900/90 shadow-red-500/10"
            : "border-white/10 bg-neutral-950/70"
        }`}
      >
        <span className="text-lg font-semibold tracking-tight text-white">ATLAS</span>

        <div className="flex-1">
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleSubmit();
              }
            }}
            placeholder={
              listening
                ? "Слушаю команду..."
                : "What's the play today?"
            }
            className="w-full border-0 bg-transparent text-center text-sm text-white placeholder:text-neutral-500 focus:outline-none"
          />
          <Soundwave active={listening} analyser={analyserRef.current} />
        </div>

        <div className="flex flex-col items-end gap-1.5" onClick={(e) => e.stopPropagation()}>
          <Badge
            onClick={() => setVision((v) => !v)}
            tooltip={vision ? "Vision mode enabled" : "Text-only mode"}
            className={vision ? "text-white" : "text-neutral-500"}
          >
            {vision ? <Zap size={12} /> : <span className="h-1.5 w-1.5 rounded-full border border-neutral-600" />}
            {vision ? "Vision ON" : "Text only"}
          </Badge>

          <Badge onClick={() => onOpenSettings()} tooltip="Settings" className="text-neutral-300">
            <Settings size={12} />
          </Badge>

          <Badge
            onClick={() => {
              if (listening) stopRecording();
              else void startRecording();
            }}
            tooltip="Нажмите или зажмите Пробел"
            className={
              listening
                ? "border-red-400/50 bg-red-500/20 text-red-300 shadow-[0_0_18px_rgba(239,68,68,0.5)]"
                : "text-neutral-300"
            }
          >
            {listening ? <MicOff size={12} /> : <Mic size={12} />}
            {listening ? "Recording" : "Mic"}
          </Badge>
        </div>
      </motion.div>
    </motion.div>
  );
}
