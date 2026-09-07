# Atlas AI Companion

Build a high-end, premium desktop AI agent overlay web application named "ATLAS". Carefully inspect the uploaded reference collage. Use React, Tailwind CSS, shadcn/ui components, Lucide React icons, and framer-motion for smooth spring animations.

GLOBAL DESIGN SYSTEM:
- Background: Pitch solid black (`bg-black` / `#000000`).
- Glassmorphism & Borders: `bg-neutral-950/70 backdrop-blur-2xl border border-white/10 shadow-2xl shadow-black/80`.
- Typography: SF Pro / Inter font, clean hierarchy, monochrome text colors (`text-white`, `text-neutral-400`, `text-neutral-500`).
- No colorful gradients or neon glow. Strictly luxury monochrome with subtle titanium/silver specular highlights.

APP ARCHITECTURE & STATE CONTROLLER:
Add a discreet floating bottom dock with 4 pill buttons to switch between UI states for previewing:
['1. Main Command Bar', '2. Action Pill', '3. Settings Modal', '4. Confirmation Modal'].

---

STATE 1: MAIN COMMAND BAR (Centered overlay)
- Geometry: Stadium capsule shape (`rounded-full h-16 max-w-2xl px-6`).
- Layout (Flex items-center justify-between):
  1. Left: Bold typographic brand "ATLAS" in pure white (`font-semibold tracking-tight text-lg`).
  2. Center: Transparent borderless input with placeholder "Ask Atlas to take action or hold Space to talk...". Below the text, add a smooth CSS soundwave equalizer animation (iridescent subtle violet/white bars).
  3. Right: Micro badges — `Vision ON` (with subtle white pulse dot), `BYOK Connected`, and a keyboard shortcut tag `⌥ Space`.

STATE 2: ACTION PILL / DYNAMIC ISLAND (Top-Right fixed widget)
- Geometry: Ultra-compact floating stadium pill (`rounded-full py-2.5 px-5`).
- Content:
  - Left: Micro pulsing white LED indicator.
  - Center: Status label "Scraping Google Maps · 34/50 leads" (`text-xs font-mono text-neutral-200`).
  - Right: Minimal clickable dark pill button `[ESC]` that triggers state change back to Main.

STATE 3: SETTINGS MODAL (Centered modal card)
- Geometry: Rounded-2xl dark frosted card (`max-w-lg p-6 rounded-2xl`).
- No heavy headers. Start directly with Segmented Tabs: ['API Keys (BYOK)', 'Telegram Remote', 'Audio'].
- Tab 1 Layout (Active by default):
  - Left Column (2/3 width):
    - Input field for 'Anthropic Claude Key' (type=password, value="sk-ant-••••••••••••") with a small `✓ Active` badge.
    - Input field for 'OpenAI Key' (type=password, value="sk-proj-••••••••••••") with a small `✓ Active` badge.
  - Right Column (1/3 width):
    - Sleek dark QR-code container with Telegram plane icon overlay in the center and caption "Scan to link mobile remote".

STATE 4: ACTION CONFIRMATION MODAL (Centered modal card)
- Geometry: Compact dark glass card (`max-w-md p-6 rounded-2xl`).
- Header: "ATLAS AI - Action Confirmation" (`text-sm font-medium text-neutral-300`).
- Action Preview Box (`bg-neutral-900/50 rounded-xl p-4 border border-white/5`):
  - Row 1: "To: john@acme.com"
  - Row 2: "Subject: Quarterly Report"
  - Row 3: Attachment chip with file icon "Leads_Miami.xlsx (2.4 MB)"
- Buttons (Flex gap-3 mt-5):
  - Primary button: Frosted white (`bg-white text-black font-medium hover:bg-neutral-200`) labeled "[Enter] Confirm & Send".
  - Secondary button: Dark glass (`bg-neutral-900 border border-white/10 text-neutral-400 hover:text-white`) labeled "[Esc] Cancel".

Wrap state transitions in framer-motion `<AnimatePresence>` with subtle scale (0.96 -> 1) and opacity fade for an ultra-fast, native macOS feel.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/b532176f-29cb-464b-9fa7-8ef9c351f2ef).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
