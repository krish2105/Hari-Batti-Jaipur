// What every screen receives from App: language, colours, the live feed and navigation.
import type { PhaseState } from "@haribatti/core";
import type { Lang } from "../i18n";
import type { Palette } from "../ui/theme";

export type Screen = "onboarding" | "consent" | "home" | "ride" | "summary" | "walk" | "report";
export type Summary = { stops: number; waitedS: number; distanceM: number; idleFuelL: number; simulated: boolean };
export type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  c: Palette;
  live: Map<string, PhaseState>;
  feed: "live" | "offline";
  go: (s: Screen, opts?: { simulated?: boolean; summary?: Summary }) => void;
};
