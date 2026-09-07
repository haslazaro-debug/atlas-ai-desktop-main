export type AgentMode = "text" | "vision_screen" | "vision_camera";

export interface AgentResponse {
  status: string;
  transcription?: string;
  response: string;
  text?: string;
  audio?: string;
  error?: string | null;
  requires_confirmation?: boolean;
  action_type?: string | null;
}

const API_URL = import.meta.env?.['VITE_API_URL'] || "http://127.0.0.1:8000";

export async function sendCommand(
  command: string,
  mode: AgentMode = "text",
  image?: string | null,
  signal?: AbortSignal,
): Promise<AgentResponse> {
  const payload = { command, mode, ...(image ? { image } : {}) };
  console.log("[sendCommand] Request URL:", `${API_URL}/api/command`, "Payload:", payload);
  try {
    const res = await fetch(`${API_URL}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...(signal ? { signal } : {}),
    });

    if (!res.ok) {
      throw new Error(`Server error: ${res.statusText}`);
    }

    const data = await res.json();
    return data as AgentResponse;
  } catch (error) {
    console.error("[sendCommand] Raw network error:", error);
    throw new Error("Connection error");
  }
}

export async function sendVoiceCommand(
  audioBlob: Blob,
  mode: AgentMode = "text",
  image?: string | null,
  signal?: AbortSignal,
): Promise<AgentResponse> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  formData.append("mode", mode);
  if (image) formData.append("image", image);
  
  console.log("[sendVoiceCommand] Request URL:", `${API_URL}/api/voice`, "Payload (FormData keys):", Array.from(formData.keys()));
  
  try {
    const res = await fetch(`${API_URL}/api/voice`, {
      method: "POST",
      body: formData,
      ...(signal ? { signal } : {}),
    });

    if (!res.ok) {
      const errText = await res.text();
      try {
        const errJson = JSON.parse(errText);
        throw new Error(errJson.response || "Server error");
      } catch {
        throw new Error(`Server error: ${res.statusText}`);
      }
    }

    const data = await res.json();
    return data as AgentResponse;
  } catch (error) {
    console.error("[sendVoiceCommand] Raw network error:", error);
    throw new Error("Connection error");
  }
}

export async function transcribeAudio(
  audioBlob: Blob,
  signal?: AbortSignal,
): Promise<{ text: string; success: boolean; error?: string }> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  
  console.log("[transcribeAudio] Request URL:", `${API_URL}/api/transcribe`, "Payload (FormData keys):", Array.from(formData.keys()));
  
  try {
    const res = await fetch(`${API_URL}/api/transcribe`, {
      method: "POST",
      body: formData,
      ...(signal ? { signal } : {}),
    });

    if (!res.ok) {
      const errText = await res.text();
      try {
        const errJson = JSON.parse(errText);
        throw new Error(errJson.detail || errJson.response || "Server error");
      } catch {
        throw new Error(`Server error: ${res.statusText}`);
      }
    }

    return (await res.json()) as { text: string; success: boolean };
  } catch (error) {
    console.error("[transcribeAudio] Raw network error:", error);
    throw new Error("Connection error");
  }
}
