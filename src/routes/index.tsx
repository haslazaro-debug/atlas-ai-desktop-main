import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";

import { CommandBar } from "@/components/atlas/CommandBar";
import { ActionPill } from "@/components/atlas/ActionPill";
import { SettingsModal } from "@/components/atlas/SettingsModal";
import { ConfirmationModal } from "@/components/atlas/ConfirmationModal";
import { PermissionsModal } from "@/components/atlas/PermissionsModal";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ATLAS - Desktop AI Agent Overlay" },
      {
        name: "description",
        content:
          "ATLAS is a premium desktop AI agent overlay: voice command bar, live action island, BYOK keys and action confirmations.",
      },
      { property: "og:title", content: "ATLAS - Desktop AI Agent Overlay" },
      {
        property: "og:description",
        content:
          "A premium AI agent overlay with wake-word voice control, live task state, BYOK keys and action confirmations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

type StateId = 0 | 1 | 2 | 3 | 4;
type PillData = {
  text: string;
  error?: string | undefined;
  audio_url?: string | undefined;
  isProcessing?: boolean | undefined;
  processingStep?: number | undefined;
  processingSteps?: string[] | undefined;
  requires_confirmation?: boolean | undefined;
  action_type?: string | undefined;
};

const transition = { type: "spring" as const, stiffness: 520, damping: 38, mass: 0.6 };

function Stage({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={transition}
      className="w-full"
    >
      {children}
    </motion.div>
  );
}

function Index() {
  const [state, setState] = useState<StateId>(0);
  const [settingsTab, setSettingsTab] = useState<"API Keys (BYOK)" | "Subscription" | "Integrations" | "Audio">(
    "API Keys (BYOK)",
  );
  const [pillData, setPillData] = useState<PillData>({ text: "" });

  const closeActiveSurface = () => {
    window.dispatchEvent(new Event("atlas:cancel"));
    setPillData({ text: "" });
    setState(0);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeActiveSurface();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <main className="relative min-h-screen overflow-hidden bg-black">
      <h1 className="sr-only">ATLAS desktop AI agent overlay</h1>

      <div className="flex min-h-screen items-center justify-center px-6 pb-32">
        <AnimatePresence mode="wait">
          {(state === 0 || state === 1) && (
            <Stage key="bar">
              <div className="flex justify-center">
                <CommandBar
                  onOpenSettings={(tab) => {
                    setSettingsTab(tab ?? "API Keys (BYOK)");
                    setState(2);
                  }}
                  onStartTask={(data) => {
                    setPillData(data);
                    setState(1);
                  }}
                />
              </div>
            </Stage>
          )}
          {state === 2 && (
            <Stage key="settings">
              <div className="flex justify-center">
                <SettingsModal initialTab={settingsTab} onClose={closeActiveSurface} />
              </div>
            </Stage>
          )}

          {state === 3 && (
            <Stage key="confirm">
              <div className="flex justify-center">
                <ConfirmationModal onClose={closeActiveSurface} />
              </div>
            </Stage>
          )}

          {state === 4 && (
            <Stage key="permissions">
              <div className="flex justify-center">
                <PermissionsModal onComplete={closeActiveSurface} />
              </div>
            </Stage>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {state === 1 && (
          <div className="pointer-events-none fixed inset-x-0 top-6 z-40 flex justify-center px-6">
            <div className="pointer-events-auto w-full max-w-md">
              <ActionPill data={pillData} onEscape={closeActiveSurface} onUpdate={setPillData} />
            </div>
          </div>
        )}
      </AnimatePresence>
    </main>
  );
}
