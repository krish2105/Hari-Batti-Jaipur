// First launch: what the app does, the safety rule (the real signal always wins) and the language.
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { tr } from "../i18n";
import { Button } from "../ui/kit";
import type { Ctx } from "./types";

export function Onboarding({ ctx, onDone }: { ctx: Ctx; onDone: () => void }) {
  const { lang, c, setLang } = ctx;
  const [i, setI] = useState(0);
  const cards = [
    [tr(lang, "onb1Title"), tr(lang, "onb1Body")],
    [tr(lang, "onb2Title"), tr(lang, "onb2Body")],
    [tr(lang, "onb3Title"), tr(lang, "onb3Body")],
  ] as const;
  const [title, body] = cards[i]!;
  return (
    <View style={s.wrap}>
      <Text style={[s.brand, { color: c.accent }]}>{tr(lang, "appName")}</Text>
      <View style={s.dots}>{cards.map((_, k) => <View key={k} style={[s.dot, { backgroundColor: k === i ? c.accent : c.line }]} />)}</View>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{title}</Text>
      <Text style={[s.body, { color: c.ink2 }]}>{body}</Text>
      {i === 2 && (
        <View style={{ gap: 12 }}>
          <Button c={c} label="हिंदी" primary={lang === "hi"} onPress={() => setLang("hi")} />
          <Button c={c} label="English" primary={lang === "en"} onPress={() => setLang("en")} />
        </View>
      )}
      <View style={{ flex: 1 }} />
      <Button c={c} big primary label={i < 2 ? tr(lang, "next") : tr(lang, "done")} onPress={() => (i < 2 ? setI(i + 1) : onDone())} />
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: 24, gap: 16 },
  brand: { fontSize: 18, fontWeight: "800", letterSpacing: 1 },
  dots: { flexDirection: "row", gap: 8 },
  dot: { width: 28, height: 6, borderRadius: 3 },
  title: { fontSize: 32, fontWeight: "800", lineHeight: 40 },
  body: { fontSize: 19, lineHeight: 29 },
});
