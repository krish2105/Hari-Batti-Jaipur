// Trip summary: stops, time waited, distance and an ESTIMATE of idle fuel. Nothing is uploaded.
import { StyleSheet, Text, View } from "react-native";
import { tr } from "../i18n";
import { Badge, Button, Card } from "../ui/kit";
import type { Ctx, Summary as S } from "./types";

export function Summary({ ctx, summary }: { ctx: Ctx; summary: S }) {
  const { lang, c, go } = ctx;
  const rows: [string, string][] = [
    [tr(lang, "stops"), String(summary.stops)],
    [tr(lang, "waited"), `${Math.round(summary.waitedS)} s`],
    [tr(lang, "distance"), `${(summary.distanceM / 1000).toFixed(2)} km`],
  ];
  return (
    <View style={s.wrap}>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "summaryTitle")}</Text>
      {summary.simulated && <Badge source="SIM" label={`${tr(lang, "SIM")} GPS`} />}
      <Card c={c}>
        {rows.map(([k, v]) => (
          <View key={k} style={s.row}>
            <Text style={{ color: c.ink2, fontSize: 18 }}>{k}</Text>
            <Text style={{ color: c.ink, fontSize: 24, fontWeight: "800" }}>{v}</Text>
          </View>
        ))}
        <View style={s.row}>
          <Text style={{ color: c.ink2, fontSize: 16, flex: 1 }}>{tr(lang, "idleFuel")}</Text>
          <Text style={{ color: c.ink, fontSize: 20, fontWeight: "800" }}>{(summary.idleFuelL * 1000).toFixed(0)} ml</Text>
        </View>
        <Badge source="ESTIMATE" label={tr(lang, "estimate")} />
      </Card>
      <View style={{ flex: 1 }} />
      <Button c={c} big primary label={tr(lang, "done")} onPress={() => go("home")} />
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: 24, gap: 14 },
  title: { fontSize: 30, fontWeight: "800" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 6 },
});
