// Spoken advice (expo-speech, on-device voices, no network). Hindi or English Indian voices.
import * as Speech from "expo-speech";
import type { Lang } from "../i18n";

let lastText = "";
let lastAt = 0;

/** Speak a short phrase; the same phrase is not repeated within 4 s. */
export function say(text: string, lang: Lang): void {
  const now = Date.now();
  if (text === lastText && now - lastAt < 4000) return;
  lastText = text;
  lastAt = now;
  void Speech.stop();
  Speech.speak(text, { language: lang === "hi" ? "hi-IN" : "en-IN", rate: 0.95 });
}

export const quiet = (): void => {
  void Speech.stop();
};
