// Home: the corridor as a strip of six signals (live colour dots, west to east), a countdown for the
// chosen signal, and the big buttons. Works offline with simulated countdowns (labelled).
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Text as SvgText } from "react-native-svg";
import { tr } from "../i18n";
import { countdownText } from "../lib/ride";
import { CORRIDOR, signalFor } from "../lib/signals";
import { Badge, Button, Card, Countdown } from "../ui/kit";
import { SIGNAL } from "../ui/theme";
import type { Ctx } from "./types";

export function Home({ ctx }: { ctx: Ctx }) {
  const { lang, c, live, feed, go, setLang } = ctx;
  const [sel, setSel] = useState("J05");
  const now = Date.now() / 1000;
  const views = CORRIDOR.map((j) => signalFor(j, true, live, now));
  const j = CORRIDOR.find((x) => x.id === sel)!;
  const east = signalFor(j, true, live, now);
  const west = signalFor(j, false, live, now);
  const W = 340;
  const x = (i: number) => 24 + (i * (W - 48)) / (CORRIDOR.length - 1);
  return (
    <ScrollView contentContainerStyle={s.wrap}>
      <View style={s.head}>
        <View style={{ flex: 1 }}>
          <Text style={[s.brand, { color: c.accent }]}>{tr(lang, "appName")}</Text>
          <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "homeTitle")}</Text>
        </View>
        <Pressable accessibilityRole="button" onPress={() => setLang(lang === "en" ? "hi" : "en")} style={[s.lang, { borderColor: c.line }]}>
          <Text style={{ color: c.ink, fontWeight: "700" }}>{tr(lang, "language")}</Text>
        </Pressable>
      </View>
      <Text style={{ color: c.ink2, fontSize: 16, lineHeight: 23 }}>{tr(lang, "homeLead")}</Text>
      <Badge source={feed === "live" ? (views[0]?.source ?? "SIM") : "SIM"} label={feed === "live" ? tr(lang, "feedLive") : tr(lang, "feedOffline")} />

      <Card c={c}>
        <Svg width="100%" height={96} viewBox={`0 0 ${W} 96`} accessibilityLabel={tr(lang, "homeTitle")}>
          <Line x1={16} x2={W - 16} y1={40} y2={40} stroke={c.ink2} strokeOpacity={0.4} strokeWidth={8} strokeLinecap="round" />
          {CORRIDOR.map((jj, i) => (
            <Circle key={jj.id} cx={x(i)} cy={40} r={jj.id === sel ? 14 : 11} fill={SIGNAL[views[i]!.colour]} stroke={jj.id === sel ? c.ink : c.panel} strokeWidth={3} />
          ))}
          {CORRIDOR.map((jj, i) => (
            <SvgText key={`t${jj.id}`} x={x(i)} y={80} fontSize={13} fontWeight="700" fill={c.ink} textAnchor="middle">{jj.id}</SvgText>
          ))}
        </Svg>
        <View style={s.row}>
          {CORRIDOR.map((jj) => (
            <Pressable key={jj.id} accessibilityRole="button" accessibilityLabel={`${jj.id} ${jj.name}`} onPress={() => setSel(jj.id)} style={[s.chip, { borderColor: jj.id === sel ? c.accent : c.line }]}>
              <Text style={{ color: c.ink, fontWeight: "700" }}>{jj.id}</Text>
            </Pressable>
          ))}
        </View>
      </Card>

      <Card c={c}>
        <Text style={{ color: c.ink, fontSize: 20, fontWeight: "800" }}>{j.id} · {j.name}</Text>
        <View style={s.pair}>
          {[{ label: tr(lang, "east"), v: east }, { label: tr(lang, "west"), v: west }].map(({ label, v }) => (
            <View key={label} style={{ flex: 1, alignItems: "center", gap: 4 }}>
              <Text style={{ color: c.ink2, fontSize: 13, textAlign: "center" }}>{label}</Text>
              <Countdown colour={v.colour} text={countdownText(v, lang)} colourName={tr(lang, v.colour)} size={64} />
            </View>
          ))}
        </View>
        <Badge source={east.source} label={tr(lang, east.source)} />
        <Text style={{ color: c.ink2, fontSize: 12 }}>{east.timingLabel}</Text>
      </Card>

      <Button c={c} big primary label={tr(lang, "startRide")} onPress={() => go("ride", { simulated: false })} />
      <Button c={c} label={`${tr(lang, "startRide")} · ${tr(lang, "SIM")}`} onPress={() => go("ride", { simulated: true })} />
      <View style={s.pair}>
        <View style={{ flex: 1 }}><Button c={c} label={tr(lang, "walk")} onPress={() => go("walk")} /></View>
        <View style={{ flex: 1 }}><Button c={c} label={tr(lang, "report")} onPress={() => go("report")} /></View>
      </View>
      <Pressable accessibilityRole="button" onPress={() => go("study")} style={{ paddingVertical: 8 }}>
        <Text style={{ color: c.ink2, fontSize: 14, textDecorationLine: "underline" }}>{tr(lang, "studyLink")}</Text>
      </Pressable>
      <Text style={{ color: c.ink2, fontSize: 12 }}>{tr(lang, "positions")}</Text>
      <Text style={{ color: c.ink2, fontSize: 12 }}>{tr(lang, "beta")}</Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { padding: 20, gap: 14, paddingBottom: 48 },
  head: { flexDirection: "row", alignItems: "center", gap: 12 },
  brand: { fontSize: 15, fontWeight: "800", letterSpacing: 1 },
  title: { fontSize: 28, fontWeight: "800" },
  lang: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "space-between" },
  chip: { borderWidth: 2, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8 },
  pair: { flexDirection: "row", gap: 12 },
});
