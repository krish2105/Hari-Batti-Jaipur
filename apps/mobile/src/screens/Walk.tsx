// Walk mode: the nearest crossing and a giant countdown for crossing the main road, spoken every
// 5 s. Estimated from the vehicle phases (no pedestrian-signal data yet) and labelled that way.
import { useKeepAwake } from "expo-keep-awake";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { tr } from "../i18n";
import { metres } from "../lib/geo";
import { usePosition } from "../lib/position";
import { CORRIDOR, signalFor } from "../lib/signals";
import { quiet, say } from "../lib/voice";
import { Badge, Button, Card, Countdown } from "../ui/kit";
import type { Ctx } from "./types";

export function Walk({ ctx }: { ctx: Ctx }) {
  useKeepAwake();
  const { lang, c, live, go } = ctx;
  const { fix } = usePosition(true, false);
  const [pick, setPick] = useState("J05");
  const nearest = fix ? CORRIDOR.reduce((a, j) => (metres(fix.p, j) < metres(fix.p, a) ? j : a), CORRIDOR[0]!) : CORRIDOR.find((j) => j.id === pick)!;
  const main = signalFor(nearest, true, live, Date.now() / 1000);
  const safe = main.colour === "RED";
  // red for the main road = time left to cross; otherwise wait for its green (+3 s amber) or amber to end
  const secs = Math.round(main.colour === "GREEN" ? main.secondsRemaining + 3 : main.secondsRemaining);
  const [n, setN] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setN((k) => k + 1), 1000);
    return () => {
      clearInterval(id);
      quiet();
    };
  }, []);
  useEffect(() => {
    if (n % 5 === 0) say(`${safe ? tr(lang, "walkNow") : tr(lang, "walkWait")}. ${secs} ${lang === "hi" ? "सेकंड" : "seconds"}`, lang);
  }, [n]);
  return (
    <View style={s.wrap}>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "walkTitle")}</Text>
      <Text style={{ color: c.ink2, fontSize: 17, lineHeight: 25 }}>{tr(lang, "walkLead", { name: `${nearest.id} ${nearest.name}` })}</Text>
      {!fix && (
        <View style={s.row}>
          {CORRIDOR.map((j) => <View key={j.id} style={{ flex: 1 }}><Button c={c} label={j.id} primary={j.id === pick} onPress={() => setPick(j.id)} /></View>)}
        </View>
      )}
      <Card c={c} style={{ alignItems: "center" }}>
        <Text style={{ color: c.ink, fontSize: 22, fontWeight: "800", textAlign: "center" }}>{safe ? tr(lang, "walkNow") : tr(lang, "walkWait")}</Text>
        <Countdown colour={safe ? "RED" : "GREEN"} text={String(Math.max(0, secs))} colourName={tr(lang, main.colour)} size={160} />
        <Badge source={main.source} label={tr(lang, main.source)} />
        <Badge source="ESTIMATE" label={tr(lang, "estimate")} />
      </Card>
      <Text style={{ color: c.ink2, fontSize: 13 }}>{tr(lang, "walkNote")}</Text>
      <View style={{ flex: 1 }} />
      <Button c={c} big primary label={tr(lang, "back")} onPress={() => go("home")} />
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: 20, gap: 12 },
  title: { fontSize: 30, fontWeight: "800" },
  row: { flexDirection: "row", gap: 6 },
});
