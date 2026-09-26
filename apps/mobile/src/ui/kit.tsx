// Small shared UI pieces: buttons, the source badge (every countdown shows where it came from),
// the big countdown and a card.
import type { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View, type ViewStyle } from "react-native";
import type { SignalColour } from "@haribatti/core";
import { SIGNAL, SOURCE_TONE, type Palette } from "./theme";

export function Button({ label, onPress, c, primary, disabled, big }: { label: string; onPress: () => void; c: Palette; primary?: boolean; disabled?: boolean; big?: boolean }) {
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress}
      style={({ pressed }) => [s.btn, { borderColor: c.line, backgroundColor: primary ? c.accent : c.panel, opacity: disabled ? 0.45 : pressed ? 0.8 : 1 }, big && s.big]}>
      <Text style={[s.btnText, { color: primary ? "#1a0f10" : c.ink }, big && { fontSize: 20 }]}>{label}</Text>
    </Pressable>
  );
}

export function Badge({ source, label }: { source: string; label: string }) {
  const tone = SOURCE_TONE[source] ?? "#888";
  return (
    <View style={[s.badge, { borderColor: tone, backgroundColor: `${tone}22` }]} accessibilityLabel={`Source: ${label}`}>
      <View style={[s.dot, { backgroundColor: tone }]} />
      <Text style={[s.badgeText, { color: tone }]}>{label}</Text>
    </View>
  );
}

/** The countdown. The colour name is always written too (colour is never the only cue). */
export function Countdown({ colour, text, colourName, size = 120 }: { colour: SignalColour; text: string; colourName: string; size?: number }) {
  const hex = SIGNAL[colour];
  return (
    <View style={{ alignItems: "center" }} accessibilityLabel={`${colourName}, ${text}`}>
      <Text style={{ fontSize: size, fontWeight: "800", color: hex, fontVariant: ["tabular-nums"], textShadowColor: `${hex}88`, textShadowRadius: 18 }}>{text}</Text>
      <Text style={{ fontSize: 16, fontWeight: "800", letterSpacing: 2, color: hex }}>{colourName.toUpperCase()}</Text>
    </View>
  );
}

export function Card({ children, c, style }: { children: ReactNode; c: Palette; style?: ViewStyle }) {
  return <View style={[s.card, { backgroundColor: c.panel, borderColor: c.line }, style]}>{children}</View>;
}

const s = StyleSheet.create({
  btn: { borderWidth: 1, borderRadius: 16, paddingVertical: 14, paddingHorizontal: 18, alignItems: "center", minHeight: 52, justifyContent: "center" },
  big: { paddingVertical: 20 },
  btnText: { fontSize: 17, fontWeight: "700" },
  badge: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3, alignSelf: "flex-start" },
  dot: { width: 7, height: 7, borderRadius: 4 },
  badgeText: { fontSize: 12, fontWeight: "700" },
  card: { borderWidth: 1, borderRadius: 20, padding: 16, gap: 8 },
});
