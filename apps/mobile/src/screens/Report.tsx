// Report a signal problem (broken / hidden / bad timing / other). Only when stopped. The location is
// rounded to about 100 m; no name, no account, no photo in the MVP. POST /reports on the API.
import { useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { tr } from "../i18n";
import { coarse, metres } from "../lib/geo";
import { API_URL } from "../lib/live";
import { usePosition } from "../lib/position";
import { tapsLocked } from "../lib/ride";
import { CORRIDOR } from "../lib/signals";
import { Button, Card } from "../ui/kit";
import type { Ctx } from "./types";

const TYPES = ["broken", "hidden", "timing_bad", "other"] as const;
const inJaipur = (lat: number, lng: number) => lat >= 26.7 && lat <= 27.1 && lng >= 75.6 && lng <= 76.0;

export function Report({ ctx }: { ctx: Ctx }) {
  const { lang, c, go } = ctx;
  const { fix } = usePosition(true, false);
  const [type, setType] = useState<(typeof TYPES)[number]>("broken");
  const nearest = fix ? CORRIDOR.reduce((a, j) => (metres(fix.p, j) < metres(fix.p, a) ? j : a), CORRIDOR[0]!) : CORRIDOR[3]!;
  const [junction, setJunction] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle"); // one report per visit: no duplicates
  const moving = tapsLocked(fix?.speedKmh ?? 0);
  const jid = junction ?? nearest.id;
  const j = CORRIDOR.find((x) => x.id === jid)!;
  const outside = !fix || !inJaipur(fix.p.lat, fix.p.lng);

  const send = async () => {
    if (state !== "idle") return;
    setState("sending");
    const at = coarse(outside ? { lat: j.lat, lng: j.lng } : fix!.p);
    try {
      const r = await fetch(`${API_URL}/reports`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ type, lat: at.lat, lng: at.lng, note: note.trim() || null, junction_id: jid }),
      });
      const body = (await r.json()) as { id?: number; detail?: unknown };
      setMsg(r.ok ? tr(lang, "sent", { id: body.id ?? "?" }) : tr(lang, "sendFailed", { msg: JSON.stringify(body.detail ?? r.status) }));
      setState(r.ok ? "sent" : "idle");
    } catch (e) {
      setMsg(tr(lang, "sendFailed", { msg: (e as Error).message }));
      setState("idle");
    }
  };

  return (
    <ScrollView contentContainerStyle={s.wrap}>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "reportTitle")}</Text>
      {moving && <Card c={c}><Text style={{ color: c.ink, fontSize: 17 }}>{tr(lang, "reportStopped")}</Text></Card>}
      <View style={s.grid}>
        {TYPES.map((k) => <View key={k} style={s.cell}><Button c={c} label={tr(lang, k)} primary={type === k} onPress={() => setType(k)} disabled={moving} /></View>)}
      </View>
      <Text style={{ color: c.ink2, fontSize: 15 }}>{tr(lang, "junctionPick")}</Text>
      <View style={s.grid}>
        {CORRIDOR.map((x) => <View key={x.id} style={s.cell3}><Button c={c} label={x.id} primary={jid === x.id} onPress={() => setJunction(x.id)} disabled={moving} /></View>)}
      </View>
      <TextInput value={note} onChangeText={setNote} placeholder={tr(lang, "note")} placeholderTextColor={c.ink2} maxLength={500} editable={!moving}
        style={[s.input, { color: c.ink, borderColor: c.line, backgroundColor: c.panel }]} multiline />
      {outside && <Text style={{ color: c.ink2, fontSize: 13 }}>{tr(lang, "outside")}</Text>}
      {msg && <Card c={c}><Text style={{ color: c.ink, fontSize: 16 }}>{msg}</Text></Card>}
      <Button c={c} big primary label={tr(lang, "send")} onPress={send} disabled={moving || state !== "idle"} />
      <Button c={c} label={tr(lang, "back")} onPress={() => go("home")} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { padding: 20, gap: 12, paddingBottom: 48 },
  title: { fontSize: 28, fontWeight: "800" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  cell: { width: "48%" },
  cell3: { width: "31%" },
  input: { borderWidth: 1, borderRadius: 14, padding: 12, minHeight: 80, fontSize: 16 },
});
