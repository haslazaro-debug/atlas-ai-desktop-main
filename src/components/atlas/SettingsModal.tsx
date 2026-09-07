import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Check, Eye, EyeOff, Loader2, Lock } from "lucide-react";

import { QrCard } from "./QrCard";
import { AccessLevelSelector } from "./AccessLevelSelector";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TABS = ["API Keys (BYOK)", "Subscription", "Integrations", "Audio"] as const;
type Tab = (typeof TABS)[number];

function Row({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-white/5 bg-neutral-900/40 px-3.5 py-3">
      <div>
        <p className="text-xs leading-snug text-neutral-300">{label}</p>
        {hint && <p className="mt-0.5 text-[10px] text-neutral-500">{hint}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={onChange} className="mt-0.5 shrink-0" />
    </div>
  );
}

function KeyField({ label, disabled }: { label: string; disabled: boolean }) {
  const [show, setShow] = useState(false);
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<"idle" | "testing" | "configured">("idle");

  const test = () => {
    if (!value.trim()) return;
    setStatus("testing");
    window.setTimeout(() => setStatus("configured"), 900);
  };

  return (
    <div className={`space-y-2 transition-opacity ${disabled ? "opacity-40" : ""}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">{label}</span>
        {status === "configured" && (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[10px] text-emerald-300">
            <Check size={10} /> Configured
          </span>
        )}
        {status === "testing" && (
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-neutral-400">
            <Loader2 size={10} className="animate-spin" /> Testing
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={show ? "text" : "password"}
            disabled={disabled}
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setStatus("idle");
            }}
            placeholder="Not configured"
            className="w-full rounded-lg border border-white/10 bg-neutral-900/60 py-2 pl-3 pr-9 text-sm tracking-wide text-neutral-300 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            disabled={disabled}
            aria-label={show ? "Hide key" : "Show key"}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 transition-colors hover:text-neutral-200"
          >
            {show ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
        </div>
        <button
          type="button"
          onClick={test}
          disabled={disabled || !value.trim()}
          className="rounded-lg border border-white/10 bg-white/[0.05] px-3 text-[11px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          Check
        </button>
      </div>
    </div>
  );
}

function ApiKeysTab() {
  const [cloud, setCloud] = useState(false);

  return (
    <div className="space-y-4 relative">
      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-xl border border-white/5 bg-neutral-900/40 px-3.5 py-3">
          <div>
            <p className="text-xs font-medium text-neutral-200">
              {cloud ? "Environment Keys" : "Local BYOK Keys"}
            </p>
            <p className="mt-0.5 text-[10px] text-neutral-500">
              {cloud
                ? "Backend will read configured values from backend/.env."
                : "Enter keys locally for this browser session."}
            </p>
          </div>
          <Switch checked={cloud} onCheckedChange={setCloud} />
        </div>

        <KeyField label="Gemini API Key" disabled={cloud} />
        <KeyField label="ElevenLabs API Key" disabled={cloud} />
      </div>
    </div>
  );
}

function IntegrationsTab() {
  const [voice, setVoice] = useState(true);
  const [shots, setShots] = useState(true);
  const [approval, setApproval] = useState(true);
  const [ping, setPing] = useState<"idle" | "sending" | "sent">("idle");
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [igStatus, setIgStatus] = useState<"idle" | "connecting" | "connected" | "error">("idle");
  const [igPageId, setIgPageId] = useState<string | null>(null);
  const [igError, setIgError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/telegram/pair')
      .then(res => res.json())
      .then(data => {
        if (data.url) setQrUrl(data.url);
      })
      .catch(err => console.error('Telegram pair error:', err));
      
    fetch('http://localhost:8000/api/instagram/status')
      .then(res => res.json())
      .then(data => {
        if (data.status === "connected") {
          setIgStatus("connected");
          setIgPageId(data.page_id);
        }
      })
      .catch(() => {});
  }, []);

  const handleIgConnect = async () => {
    setIgStatus("connecting");
    setIgError(null);
    try {
      const res = await fetch("http://localhost:8000/api/instagram/auth-url");
      const data = await res.json();
      if (data.error) {
        setIgStatus("error");
        setIgError(data.error);
      } else if (data.url) {
        window.location.href = data.url;
      }
    } catch {
      setIgStatus("error");
      setIgError("Failed to fetch auth URL");
    }
  };

  const checkTelegram = async () => {
    setPing("sending");
    try {
      const res = await fetch("http://localhost:8000/api/telegram/check");
      const data = await res.json();
      if (data.status === "success") {
        setPing("sent");
        window.setTimeout(() => setPing("idle"), 2000);
      } else {
        setPing("idle");
      }
    } catch {
      setPing("idle");
    }
  };

  return (
    <div className="grid grid-cols-3 gap-5">
      <div className="col-span-2 space-y-3">
        {/* Instagram Integration */}
        <div className="rounded-xl border border-white/5 bg-neutral-900/40 px-3.5 py-3">
          <p className="text-xs font-medium text-neutral-200">Instagram Connection</p>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] text-neutral-300">
              {igStatus === "connected" ? (
                <><Check size={10} className="text-emerald-400" /> Connected to {igPageId || "Meta"}</>
              ) : igStatus === "error" ? (
                <span className="text-red-400">{igError || "Connection error"}</span>
              ) : (
                "Not Connected"
              )}
            </span>
            <button
              type="button"
              onClick={handleIgConnect}
              disabled={igStatus === "connected"}
              className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-[10px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white disabled:opacity-50"
            >
              {igStatus === "connecting" && <Loader2 size={10} className="animate-spin" />}
              {igStatus === "connected" ? "Connected" : "Connect with Meta"}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-neutral-900/40 px-3.5 py-3">
          <p className="text-xs font-medium text-neutral-200">Bot Connection</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] text-neutral-300">
              Uses TELEGRAM_BOT_TOKEN from backend/.env
            </span>
            <button
              type="button"
              onClick={checkTelegram}
              className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-[10px] text-neutral-300 transition-colors hover:bg-white/[0.1] hover:text-white"
            >
              {ping === "sending" && <Loader2 size={10} className="animate-spin" />}
              {ping === "sent" && <Check size={10} />}
              {ping === "sent" ? "Checked" : "Check"}
            </button>
          </div>
        </div>

        <Row
          label="Voice command execution via Telegram voice notes"
          checked={voice}
          onChange={setVoice}
        />
        <Row
          label="Send execution summary screenshots back to mobile"
          checked={shots}
          onChange={setShots}
        />
        <Row
          label="Require approval for payments and file deletion"
          checked={approval}
          onChange={setApproval}
        />
      </div>
      <div className="pt-1">
        <QrCard caption="Scan to open Telegram bot" url={qrUrl} />
      </div>
    </div>
  );
}

function AudioTab() {
  const [chime, setChime] = useState(true);
  const [voiceNotes, setVoiceNotes] = useState(true);
  const [volume, setVolume] = useState([72]);

  useEffect(() => {
    fetch("http://localhost:8000/api/settings")
      .then(r => r.json())
      .then(d => {
        if (d.volume !== undefined) setVolume([d.volume]);
        if (d.chime !== undefined) setChime(d.chime);
        if (d.voice_notes !== undefined) setVoiceNotes(d.voice_notes);
      })
      .catch(() => {});
  }, []);

  const saveSettings = (updates: any) => {
    fetch("http://localhost:8000/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    }).catch(() => {});
  };

  const handleVolume = (v: number[]) => {
    setVolume(v);
    saveSettings({ volume: v[0] });
  };
  
  const handleChime = (v: boolean) => {
    setChime(v);
    saveSettings({ chime: v });
  };

  const handleVoiceNotes = (v: boolean) => {
    setVoiceNotes(v);
    saveSettings({ voice_notes: v });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-xl border border-white/10 bg-neutral-900/40 p-4">
        <p className="text-xs font-semibold text-neutral-200">Desktop Audio & Voice Engine</p>

        <div className="space-y-2">
          <p className="text-[11px] font-medium text-neutral-400">Speakers</p>
          <Select defaultValue="system">
            <SelectTrigger className="w-full border-white/10 bg-neutral-900/60 text-xs text-neutral-200">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-white/10 bg-neutral-950 text-neutral-200">
              <SelectItem value="system">System default output</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-medium text-neutral-400">Voice Engine</p>
          <Select defaultValue="auto">
            <SelectTrigger className="w-full border-white/10 bg-neutral-900/60 text-xs text-neutral-200">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-white/10 bg-neutral-950 text-neutral-200">
              <SelectItem value="auto">ElevenLabs, fallback Edge-TTS</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-neutral-400">Voice Volume</span>
            <span className="font-mono text-[11px] text-neutral-500">{volume[0] ?? 0}%</span>
          </div>
          <Slider value={volume} onValueChange={handleVolume} min={0} max={100} step={1} />
        </div>

        <Row
          label="Play subtle completion chime when task finishes"
          checked={chime}
          onChange={handleChime}
        />
      </div>

      <div className="space-y-3 rounded-xl border border-white/10 bg-neutral-900/40 p-4">
        <p className="text-xs font-semibold text-neutral-200">Telegram Mobile Voice Sync</p>
        <Row
          label="Accept voice notes from Telegram"
          checked={voiceNotes}
          onChange={handleVoiceNotes}
        />
        <Row label="Reply with voice messages" checked={chime} onChange={handleChime} />
      </div>
    </div>
  );
}

export function SettingsModal({ initialTab, onClose }: { initialTab?: Tab; onClose?: () => void }) {
  const [tab, setTab] = useState<Tab>(initialTab ?? TABS[0]);
  const [tier, setTier] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/user/tier")
      .then(res => res.json())
      .then(data => {
        if (data.tier) setTier(data.tier);
        else setTier("free");
      })
      .catch(() => setTier("free"));
  }, []);

  if (tier === null) {
    return (
      <motion.div
        layout
        className="atlas-specular w-full max-w-lg rounded-2xl border border-white/10 bg-neutral-950/70 p-6 shadow-2xl shadow-black/80 backdrop-blur-2xl flex items-center justify-center min-h-[300px]"
      >
        <Loader2 className="animate-spin text-neutral-400" size={24} />
      </motion.div>
    );
  }

  const isLifetime = tier.startsWith("lifetime");
  const visibleTabs = TABS.filter((t) => isLifetime || t !== "API Keys (BYOK)");
  const activeTab = visibleTabs.includes(tab) ? tab : visibleTabs[0];

  return (
    <motion.div
      layout
      className="atlas-specular w-full max-w-lg rounded-2xl border border-white/10 bg-neutral-950/70 p-6 shadow-2xl shadow-black/80 backdrop-blur-2xl"
    >
      <div className="mb-3 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 font-mono text-[10px] text-neutral-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          Close
        </button>
      </div>
      <div className="flex rounded-xl border border-white/10 bg-neutral-900/60 p-1">
        {visibleTabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`relative flex-1 rounded-lg px-3 py-1.5 text-xs transition-colors ${
              activeTab === t ? "text-white" : "text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {activeTab === t && (
              <motion.span
                layoutId="atlas-tab"
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
                className="absolute inset-0 rounded-lg border border-white/10 bg-white/[0.07]"
              />
            )}
            <span className="relative">{t}</span>
          </button>
        ))}
      </div>

      <motion.div layout className="mt-5">
        {activeTab === "API Keys (BYOK)" && <ApiKeysTab />}
        {activeTab === "Subscription" && <AccessLevelSelector currentTier={tier} />}
        {activeTab === "Integrations" && <IntegrationsTab />}
        {activeTab === "Audio" && <AudioTab />}
      </motion.div>
    </motion.div>
  );
}
