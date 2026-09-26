// HariBatti mobile app: signal countdowns and spoken speed advice for the Mansarovar corridor.
// Safety: advice never says "go", is capped at the limit minus 5 km/h, taps are locked above
// 5 km/h, and the physical signal always wins. Location is used only while Ride / Walk / Report is open.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getLocales } from "expo-localization";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { useColorScheme, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import type { Lang } from "./src/i18n";
import { useLiveSignals } from "./src/lib/live";
import { Consent } from "./src/screens/Consent";
import { Home } from "./src/screens/Home";
import { Onboarding } from "./src/screens/Onboarding";
import { Report } from "./src/screens/Report";
import { Ride } from "./src/screens/Ride";
import { Summary } from "./src/screens/Summary";
import type { Ctx, Screen, Summary as TripSummary } from "./src/screens/types";
import { Walk } from "./src/screens/Walk";
import { DARK, LIGHT } from "./src/ui/theme";

const KEY = "hb.mobile.settings";

export default function App() {
  const scheme = useColorScheme();
  const c = scheme === "light" ? LIGHT : DARK;
  const { states, feed } = useLiveSignals();
  const deviceLang: Lang = getLocales()[0]?.languageCode === "hi" ? "hi" : "en";
  const [lang, setLangState] = useState<Lang>(deviceLang);
  const [screen, setScreen] = useState<Screen | null>(null);
  const [simulated, setSimulated] = useState(false);
  const [summary, setSummary] = useState<TripSummary | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        const s = raw ? (JSON.parse(raw) as { lang?: Lang; onboarded?: boolean }) : {};
        if (s.lang) setLangState(s.lang);
        setScreen(s.onboarded ? "home" : "onboarding");
      })
      .catch(() => setScreen("onboarding"));
  }, []);

  const save = (patch: Record<string, unknown>) =>
    AsyncStorage.getItem(KEY)
      .then((raw) => AsyncStorage.setItem(KEY, JSON.stringify({ ...(raw ? JSON.parse(raw) : {}), ...patch })))
      .catch(() => undefined);
  const setLang = (l: Lang) => {
    setLangState(l);
    save({ lang: l });
  };
  const go: Ctx["go"] = (s, opts) => {
    if (opts?.simulated !== undefined) setSimulated(opts.simulated);
    if (opts?.summary) setSummary(opts.summary);
    setScreen(s);
  };
  const ctx: Ctx = { lang, setLang, c, live: states, feed, go };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }}>
        <StatusBar style={scheme === "light" ? "dark" : "light"} />
        <View style={{ flex: 1 }}>
          {screen === "onboarding" && <Onboarding ctx={ctx} onDone={() => setScreen("consent")} />}
          {screen === "consent" && <Consent ctx={ctx} onDone={() => { save({ onboarded: true }); setScreen("home"); }} />}
          {screen === "home" && <Home ctx={ctx} />}
          {screen === "ride" && <Ride ctx={ctx} simulated={simulated} />}
          {screen === "summary" && summary && <Summary ctx={ctx} summary={summary} />}
          {screen === "walk" && <Walk ctx={ctx} />}
          {screen === "report" && <Report ctx={ctx} />}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}
