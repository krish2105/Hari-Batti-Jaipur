"use client";
// Screen 2 — Live wall: one tile per junction with every approach's phase and countdown
// (WebSocket /ws/signals, 1 Hz) and the alert rail (signal dark, phase stuck, amber in daytime).
import Link from "next/link";
import { useMemo } from "react";
import { Badge, Card, Led, PageHead } from "@/components/ui";
import { useApi } from "@/lib/api";
import { ALL_JUNCTIONS, SIGNAL_HEX } from "@/lib/health";
import { useLive } from "@/lib/live";
import { fmt, useT } from "@/lib/i18n";
import type { JunctionInfo, Phase } from "@/lib/types";

export default function LiveWall() {
  const { t, href } = useT();
  const { states, alerts, feed } = useLive();
  const js = useApi<JunctionInfo[]>("/junctions");
  const names = useMemo(() => Object.fromEntries((js.data ?? []).flatMap((j) => j.approaches.map((a) => [a.id, a.name]))), [js.data]);
  const byJ = useMemo(() => {
    const m: Record<string, Phase[]> = {};
    for (const s of states) (m[s.junctionId] ??= []).push(s);
    return m;
  }, [states]);
  const sample = states[0];
  const alertText = (a: (typeof alerts)[number]) =>
    a.kind === "dark" ? fmt(t.live.alertDark, { s: a.seconds }) : a.kind === "stuck" ? fmt(t.live.alertStuck, { s: a.seconds, colour: t.signal[a.colour ?? "RED"] }) : t.live.alertAmber;

  return (
    <>
      <PageHead title={t.live.title} lead={t.live.lead}>
        {sample?.simClock && (
          <span className="panel-2 num px-3 py-2 text-xs">
            {t.live.simClock}: {sample.simClock}
          </span>
        )}
        {sample && <Badge kind={sample.source === "ITMS" ? "ITMS" : sample.source === "CROWD" ? "CROWD" : "SIM"} />}
        {sample?.timing === "ASSUMED" && <Badge kind="ASSUMED" />}
      </PageHead>

      {states.length === 0 ? (
        <Card>
          <p className="text-sm">{feed === "down" ? t.offline.title : t.live.noFeed}</p>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
          <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
            {ALL_JUNCTIONS.map((id) => {
              const list = byJ[id] ?? [];
              const alerting = alerts.some((a) => a.junctionId === id);
              return (
                <Link key={id} href={href(`/junction/${id}`)} className={`panel block p-3.5 transition-colors hover:border-[var(--accent)] ${alerting ? "!border-[#ff3b30]/60" : ""}`}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-semibold">
                      <span className="num">{id}</span> <span className="muted text-sm font-normal">{js.data?.find((j) => j.id === id)?.name.replace(/ Junction$/, "")}</span>
                    </span>
                    {alerting && <span className="rounded-full bg-[#ff3b30]/15 px-2 py-0.5 text-[10px] font-bold text-[#ff3b30]">{t.live.alerts}</span>}
                  </div>
                  <ul className="flex flex-col gap-1.5">
                    {list.map((s) => (
                      <li key={s.approachId} className="panel-2 flex items-center justify-between gap-2 px-2.5 py-1.5">
                        <span className="flex min-w-0 items-center gap-2 text-xs">
                          <span aria-hidden className="size-2.5 shrink-0 rounded-full" style={{ background: SIGNAL_HEX[s.colour], boxShadow: `0 0 8px ${SIGNAL_HEX[s.colour]}` }} />
                          <span className="truncate">{names[s.approachId] ?? s.approachId}</span>
                        </span>
                        <Led colour={s.colour} seconds={s.secondsRemaining} size="sm" />
                      </li>
                    ))}
                  </ul>
                </Link>
              );
            })}
          </div>
          <Card title={t.live.alerts} className="self-start">
            {alerts.length === 0 ? (
              <p className="muted text-sm">{t.live.noAlerts}</p>
            ) : (
              <ul className="flex flex-col gap-2 text-sm">
                {alerts.map((a) => (
                  <li key={`${a.approachId}-${a.kind}`} className="rounded-lg border border-[#ff3b30]/30 bg-[#ff3b30]/8 p-2">
                    <span className="num font-semibold">{a.junctionId}</span> · {names[a.approachId] ?? a.approachId}
                    <br />
                    <span className="muted">{alertText(a)}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="faint mt-3 border-t border-[var(--line)] pt-3 text-xs">{t.live.alertSpill}</p>
          </Card>
        </div>
      )}
    </>
  );
}
