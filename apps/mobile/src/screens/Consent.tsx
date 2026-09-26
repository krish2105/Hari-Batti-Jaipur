// DPDP-style consent before any location use: what we take, when, and what we never keep.
import * as Location from "expo-location";
import { StyleSheet, Text, View } from "react-native";
import { tr } from "../i18n";
import { Button } from "../ui/kit";
import type { Ctx } from "./types";

export function Consent({ ctx, onDone }: { ctx: Ctx; onDone: (granted: boolean) => void }) {
  const { lang, c } = ctx;
  const allow = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync(); // "while using the app" only
    onDone(status === "granted");
  };
  return (
    <View style={s.wrap}>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "consentTitle")}</Text>
      <Text style={[s.body, { color: c.ink2 }]}>{tr(lang, "consentBody")}</Text>
      <View style={{ flex: 1 }} />
      <Button c={c} big primary label={tr(lang, "consentAllow")} onPress={allow} />
      <Button c={c} label={tr(lang, "consentLater")} onPress={() => onDone(false)} />
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: 24, gap: 16 },
  title: { fontSize: 30, fontWeight: "800", lineHeight: 38 },
  body: { fontSize: 18, lineHeight: 28 },
});
