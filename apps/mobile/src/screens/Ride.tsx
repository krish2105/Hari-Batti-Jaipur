// Ride / drive mode: the next signal with a huge countdown and colour band, the next two smaller,
// one line of advice (GLOSA v2, capped at limit - 5 km/h, never "go"), spoken at 400/200/100 m,
// the source badge, an engine-off nudge on long reds, and NO taps above 5 km/h. Screen stays on.
import { useKeepAwake } from "expo-keep-awake";
import { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { tr } from "../i18n";
import { usePosition } from "../lib/position";
import { adviceFor, countdownText, direction, engineOffNudge, junctionChainages, match, phrase, tapsLocked, TripStats, upcoming, voiceThreshold } from "../lib/ride";
import { CORRIDOR, signalFor, SPEED_LIMIT_KMH } from "../lib/signals";
import { quiet, say } from "../lib/voice";
import { Badge, Button, Card, Countdown } from "../ui/kit";
import { SIGNAL } from "../ui/theme";
import { addPoint, shouldEnd, type Arm, type Point } from "../lib/study";
import type { Ctx } from "./types";

const AT = junctionChainages(CORRIDOR);

/** A field-study run (P8 W14): in the control arm no countdown, advice or voice is shown. */
export type StudyRun = { arm: Arm; onFinish: (points: Point[], direction: "east" | "west") => void };

export function Ride({ ctx, simulated, study }: { ctx: Ctx; simulated: boolean; study?: StudyRun }) {
  useKeepAwake(); // screen stays on during a ride only
  const { lang, c, live, go } = ctx;
  const { fix, denied } = usePosition(true, simulated);
  const [rider, setRider] = useState(false);
  const stats = useRef(new TripStats());
  const prevChain = useRef<number | null>(null);
  const eastRef = useRef(true);
  const prevDist = useRef<{ id: string; d: number } | null>(null);
  const nudged = useRef<string | null>(null);
  const trace = useRef<Point[]>([]);
  const passedLast = useRef(false);
  const finished = useRef(false);
  const control = study?.arm === "control";

  const m = fix ? match(fix.p, CORRIDOR) : null;
  if (m?.onCorridor) {
    const dir = direction(prevChain.current, m.chainage);
    if (dir !== null) eastRef.current = dir;
  }
  const now = Date.now() / 1000;
  const ahead = m?.onCorridor ? upcoming(m.chainage, eastRef.current, CORRIDOR, AT) : [];
  const views = ahead.map((a) => ({ a, v: signalFor(a.junction, eastRef.current, live, now) }));
  const first = views[0];
  const advice = first ? adviceFor(first.a.distanceM, first.v, SPEED_LIMIT_KMH) : null;
  const words = first && advice ? phrase(advice, first.v, lang) : "";
  const speed = fix?.speedKmh ?? 0;
  const locked = tapsLocked(speed);

  const finishStudy = () => {
    if (!study || finished.current) return;
    finished.current = true;
    quiet();
    study.onFinish(trace.current, eastRef.current ? "east" : "west");
  };

  useEffect(() => {
    if (!fix) return;
    stats.current.update(fix.t, fix.speedKmh, m?.onCorridor ? m.chainage : null);
    if (m?.onCorridor) prevChain.current = m.chainage;
    if (study) {
      trace.current = addPoint(trace.current, fix.t, fix.p, fix.speedKmh);
      const e = shouldEnd(fix.p, eastRef.current, CORRIDOR, passedLast.current);
      passedLast.current = e.passed;
      if (e.end) finishStudy();
    }
    if (first && words && !control) {
      const prev = prevDist.current?.id === first.a.junction.id ? prevDist.current.d : null;
      if (voiceThreshold(prev, first.a.distanceM) !== null) say(words, lang);
      prevDist.current = { id: first.a.junction.id, d: first.a.distanceM };
      if (engineOffNudge(fix.speedKmh, first.v) && nudged.current !== first.a.junction.id) {
        nudged.current = first.a.junction.id;
        say(tr(lang, "engineOff"), lang);
      }
    }
  }, [fix?.t]);
  useEffect(() => () => quiet(), []);

  const end = () => {
    if (study) return finishStudy();
    const s = stats.current;
    go("summary", { summary: { stops: s.stops, waitedS: s.waitedS, distanceM: s.distanceM, idleFuelL: s.idleFuelL("scooter"), simulated } });
  };

  return (
    <View style={[s.wrap, { backgroundColor: rider ? "#000" : c.bg }]}>
      <View style={s.top}>
        <Text style={{ color: c.ink2, fontSize: 15 }}>{tr(lang, "heading", { dir: tr(lang, eastRef.current ? "east" : "west") })}</Text>
        {simulated && <Badge source="SIM" label={`${tr(lang, "SIM")} GPS`} />}
      </View>
      {study && <Text style={{ color: c.accent, fontSize: 15, fontWeight: "700" }}>{tr(lang, control ? "studyArmControl" : "studyArmAdvice")} · {tr(lang, "studyRecording")}</Text>}
      {denied && <Text style={{ color: c.ink, fontSize: 16 }}>{tr(lang, "consentBody")}</Text>}
      {control ? null : !m?.onCorridor || !first ? (
        <Card c={c}><Text style={{ color: c.ink, fontSize: 18, lineHeight: 26 }}>{tr(lang, "offCorridor")}</Text></Card>
      ) : (
        <>
          <View style={[s.band, { backgroundColor: SIGNAL[first.v.colour] }]} />
          <Text style={[s.name, { color: c.ink }]}>{first.a.junction.id} · {first.a.junction.name}</Text>
          <Text style={{ color: c.ink2, fontSize: 18 }}>{tr(lang, "ahead", { m: Math.round(first.a.distanceM) })}</Text>
          {!rider && <Countdown colour={first.v.colour} text={countdownText(first.v, lang)} colourName={tr(lang, first.v.colour)} size={150} />}
          <Text accessibilityLiveRegion="polite" style={[s.advice, { color: c.ink }]}>{words}</Text>
          <Badge source={first.v.source} label={tr(lang, first.v.source)} />
          <Text style={{ color: c.ink2, fontSize: 13 }}>{tr(lang, "limit", { kmh: SPEED_LIMIT_KMH - 5, limit: SPEED_LIMIT_KMH })}</Text>
          {engineOffNudge(speed, first.v) && <Text style={{ color: c.accent, fontSize: 17, fontWeight: "700" }}>{tr(lang, "engineOff")}</Text>}
          {!rider && (
            <View style={s.small}>
              {views.slice(1).map(({ a, v }) => (
                <Card key={a.junction.id} c={c} style={{ flex: 1, alignItems: "center" }}>
                  <Text style={{ color: c.ink, fontWeight: "700" }}>{a.junction.id} · {Math.round(a.distanceM)} m</Text>
                  <Countdown colour={v.colour} text={countdownText(v, lang)} colourName={tr(lang, v.colour)} size={40} />
                </Card>
              ))}
            </View>
          )}
        </>
      )}
      <View style={{ flex: 1 }} />
      <Button c={c} label={rider ? tr(lang, "rideDrive") : tr(lang, "rideRider")} onPress={() => setRider(!rider)} disabled={locked} />
      <Button c={c} primary big label={tr(lang, study ? "studyEnd" : "endRide")} onPress={end} disabled={locked} />
      {locked && (
        // no taps while moving: this layer swallows every touch until the speed drops below 5 km/h
        <Pressable style={s.lock} accessibilityLabel={tr(lang, "eyes")} onPress={() => undefined}>
          <Text style={s.lockText}>{tr(lang, "eyes")}</Text>
        </Pressable>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: 20, gap: 10 },
  top: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  band: { height: 10, borderRadius: 5 },
  name: { fontSize: 24, fontWeight: "800" },
  advice: { fontSize: 30, fontWeight: "800", textAlign: "center", lineHeight: 38 },
  small: { flexDirection: "row", gap: 10 },
  lock: { position: "absolute", left: 0, right: 0, bottom: 0, height: 170, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 20 },
  lockText: { color: "#fff", fontSize: 17, fontWeight: "700", textAlign: "center" },
});
