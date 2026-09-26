// Field study (P8 W14), invite only: join with an invite code (random ID, explicit consent), then
// start runs. The server decides whether each run has speed advice ON or OFF; the run records GPS once
// a second, stops by itself 250 m after the last signal and uploads (the server trims 200 m at each end).
import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { tr, type Key } from "../i18n";
import { enrol, loadEnrolment, startRun, upload, withdraw, type Arm, type Enrolment, type Point } from "../lib/study";
import { Button, Card } from "../ui/kit";
import { Ride } from "./Ride";
import type { Ctx } from "./types";

const VEHICLES: [string, Key][] = [["car", "vehCar"], ["scooter", "vehScooter"], ["motorbike", "vehMotorbike"], ["auto", "vehAuto"]];

type Phase =
  | { kind: "loading" }
  | { kind: "join" }
  | { kind: "ready"; msg?: string }
  | { kind: "run"; runId: number; arm: Arm }
  | { kind: "uploading" }
  | { kind: "failed"; runId: number; points: Point[]; direction: "east" | "west"; msg: string };

export function Study({ ctx }: { ctx: Ctx }) {
  const { lang, c, go } = ctx;
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const [me, setMe] = useState<Enrolment | null>(null);
  const [code, setCode] = useState("");
  const [vehicle, setVehicle] = useState("scooter");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadEnrolment().then((e) => {
      setMe(e);
      setPhase(e ? { kind: "ready" } : { kind: "join" });
    });
  }, []);

  const join = async () => {
    setErr(null);
    try {
      const e = await enrol(code, vehicle);
      setMe(e);
      setPhase({ kind: "ready", msg: tr(lang, "studyJoined", { id: e.participantId }) });
    } catch (x) {
      setErr(String(x instanceof Error ? x.message : x).includes("invite") ? tr(lang, "studyInvalid") : String(x));
    }
  };
  const begin = async () => {
    if (!me) return;
    setErr(null);
    try {
      const r = await startRun(me);
      setPhase({ kind: "run", runId: r.runId, arm: r.arm });
    } catch (x) {
      setErr(String(x instanceof Error ? x.message : x));
    }
  };
  const send = async (runId: number, points: Point[], direction: "east" | "west") => {
    if (!me) return;
    setPhase({ kind: "uploading" });
    try {
      const r = await upload(me, runId, points, direction);
      setMe({ ...me, runs: me.runs + 1 });
      setPhase({ kind: "ready", msg: tr(lang, "studyUploaded", { kept: r.pointsKept, trimmed: r.pointsTrimmed }) });
    } catch (x) {
      setPhase({ kind: "failed", runId, points, direction, msg: String(x instanceof Error ? x.message : x) });
    }
  };
  const leave = async () => {
    if (!me) return;
    try {
      await withdraw(me);
      setMe(null);
      setPhase({ kind: "join" });
      setErr(tr(lang, "studyLeft"));
    } catch (x) {
      setErr(String(x instanceof Error ? x.message : x));
    }
  };

  if (phase.kind === "run") return <Ride ctx={ctx} simulated={false} study={{ arm: phase.arm, onFinish: (p, d) => send(phase.runId, p, d) }} />;

  return (
    <ScrollView contentContainerStyle={s.wrap}>
      <Text accessibilityRole="header" style={[s.title, { color: c.ink }]}>{tr(lang, "studyTitle")}</Text>
      <Text style={{ color: c.ink2, fontSize: 16, lineHeight: 23 }}>{tr(lang, "studyLead")}</Text>
      {phase.kind === "join" && (
        <Card c={c}>
          <Text style={{ color: c.ink, fontWeight: "700" }}>{tr(lang, "studyCode")}</Text>
          <TextInput value={code} onChangeText={setCode} autoCapitalize="characters" autoCorrect={false} maxLength={12} accessibilityLabel={tr(lang, "studyCode")}
            style={[s.input, { color: c.ink, borderColor: c.line }]} />
          <Text style={{ color: c.ink, fontWeight: "700", marginTop: 8 }}>{tr(lang, "studyVehicle")}</Text>
          <View style={s.row}>
            {VEHICLES.map(([v, k]) => (
              <View key={v} style={{ flexBasis: "47%" }}><Button c={c} primary={vehicle === v} label={tr(lang, k)} onPress={() => setVehicle(v)} /></View>
            ))}
          </View>
          <Text style={{ color: c.ink2, fontSize: 14, lineHeight: 21, marginTop: 8 }}>{tr(lang, "studyConsent")}</Text>
          <Button c={c} primary big label={tr(lang, "studyJoin")} onPress={join} disabled={code.trim().length < 6} />
        </Card>
      )}
      {phase.kind === "ready" && me && (
        <Card c={c}>
          <Text style={{ color: c.ink, fontSize: 18, fontWeight: "800" }}>{me.participantId}</Text>
          {phase.msg && <Text accessibilityLiveRegion="polite" style={{ color: c.accent, fontSize: 15 }}>{phase.msg}</Text>}
          <Button c={c} primary big label={tr(lang, "studyStartRun", { n: me.runs + 1 })} onPress={begin} />
          <Button c={c} label={tr(lang, "studyLeave")} onPress={leave} />
        </Card>
      )}
      {phase.kind === "uploading" && <Text style={{ color: c.ink, fontSize: 16 }}>{tr(lang, "studyUploading")}</Text>}
      {phase.kind === "failed" && (
        <Card c={c}>
          <Text style={{ color: c.ink }}>{tr(lang, "studyUploadFailed", { msg: phase.msg })}</Text>
          <Button c={c} primary label={tr(lang, "studyRetry")} onPress={() => send(phase.runId, phase.points, phase.direction)} />
        </Card>
      )}
      {err && <Text accessibilityLiveRegion="polite" style={{ color: c.accent, fontSize: 15 }}>{err}</Text>}
      <Button c={c} label={tr(lang, "back")} onPress={() => go("home")} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { padding: 20, gap: 14, paddingBottom: 48 },
  title: { fontSize: 28, fontWeight: "800" },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 20, letterSpacing: 2 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
});
