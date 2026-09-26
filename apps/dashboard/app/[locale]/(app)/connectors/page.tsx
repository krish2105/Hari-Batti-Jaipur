"use client";
// Admin only — data connectors (P8 W12). Shows every configured read-only feed with its health
// (data age, rejected records, clock drift), lets an Admin edit a tenant's mapping (vendor field
// names, colour words and junction/arm IDs -> our approach IDs) and preview pasted sample records
// before saving. The preview is pure: the API maps the pasted text and fetches, stores, sends nothing.
import { useEffect, useMemo, useState } from "react";
import { Badge, Card, ErrorNote, Led, Loading, PageHead, Segmented } from "@/components/ui";
import { api, ApiError, roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, num, useT } from "@/lib/i18n";
import type { ConnectorList, ConnectorMapping, JunctionInfo, PreviewResult } from "@/lib/types";

const FIELD_KEYS = ["junction", "approach", "colour", "remaining", "timestamp"] as const;
// synthetic sample (the demo feed's shape), used until the Admin pastes real vendor records
const DEMO_SAMPLE = JSON.stringify(
  [
    { site: "SIG-105", arm: 1, state: "G", secs_left: 24, ts: "2026-09-01T12:00:00Z" },
    { site: "SIG-105", arm: 3, state: "R", secs_left: 31, ts: "2026-09-01T12:00:00Z" },
    { site: "SIG-105", arm: 7, state: "G", secs_left: 9 },
  ],
  null,
  1,
);

/** "R=RED\nY=AMBER" <-> {R: "RED", Y: "AMBER"} for the colour-words textarea. */
const coloursToText = (c: Record<string, string> = {}) => Object.entries(c).map(([k, v]) => `${k}=${v}`).join("\n");
const textToColours = (s: string) =>
  Object.fromEntries(s.split("\n").map((l) => l.split("=").map((x) => x.trim())).filter((p) => p.length === 2 && p[0] && p[1]));

export default function Connectors() {
  const { t } = useT();
  const { session } = useSession();
  const isAdmin = roleAtLeast(session?.role, "Admin");
  const list = useApi<ConnectorList>(isAdmin ? "/connectors" : null, { pollMs: 5000 });
  const junctions = useApi<JunctionInfo[]>(isAdmin ? "/junctions" : null);
  const [selected, setSelected] = useState<string | null>(null);
  const current = selected ?? list.data?.connectors[0]?.id ?? null;

  if (!isAdmin) {
    return (
      <>
        <PageHead title={t.connectors.title} />
        <Card><p className="text-sm">{t.connectors.adminOnly}</p></Card>
      </>
    );
  }

  return (
    <>
      <PageHead title={t.connectors.title} lead={t.connectors.lead}>
        <span className="panel-2 px-3 py-2 text-xs font-semibold">{t.connectors.readOnly}</span>
      </PageHead>
      <ErrorNote error={list.error} />
      <Card title={t.connectors.configured} badge={list.data ? <span className="faint text-xs">{t.connectors.live}: <b className="num">{list.data.active}</b></span> : undefined}>
        {!list.data ? <Loading /> : list.data.connectors.length === 0 ? <p className="muted text-sm">{t.connectors.none}</p> : (
          <div className="overflow-x-auto">
            <table className="data min-w-[860px]">
              <thead>
                <tr>
                  <th>{t.connectors.id}</th><th>{t.connectors.kind}</th><th>{t.connectors.tenant}</th><th>{t.common.source}</th><th>{t.connectors.mapped}</th>
                  <th>{t.connectors.running}</th><th>{t.connectors.received}</th><th>{t.connectors.age}</th><th>{t.connectors.drift}</th><th>{t.connectors.warnings}</th>
                </tr>
              </thead>
              <tbody>
                {list.data.connectors.map((c) => (
                  <tr key={c.id} className={c.id === current ? "bg-[var(--accent-soft)]" : ""}>
                    <td><button type="button" className="num font-semibold text-[var(--accent)] underline-offset-2 hover:underline" onClick={() => setSelected(c.id)} aria-pressed={c.id === current}>{c.id}</button></td>
                    <td className="num text-xs">{c.kind}</td>
                    <td className="text-xs">{c.tenant}</td>
                    <td><Badge kind={(["ITMS", "CROWD", "SIM"].includes(c.source) ? c.source : "ITMS") as "ITMS"} /></td>
                    <td className="num">{c.mappedApproaches}</td>
                    <td className="text-xs">{c.running ? <span className="font-semibold text-[#16a34a]">● {t.connectors.running}</span> : <span className="faint">{t.connectors.idle}</span>}</td>
                    <td className="num text-xs">{c.running ? `${num(c.health.received)} / ${num(c.health.rejected)}` : "—"}</td>
                    <td className="num text-xs">{c.health.lastDataAgeS != null ? `${num(c.health.lastDataAgeS, 1)} s` : "—"}</td>
                    <td className="num text-xs">{c.health.clockDriftS != null ? `${num(c.health.clockDriftS, 1)} s` : "—"}</td>
                    <td className="max-w-[18rem] text-xs">{c.health.warnings.length ? c.health.warnings.join("; ") : <span className="text-[#16a34a]">{t.connectors.ok}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="faint mt-3 text-xs">{t.connectors.switchHint} · {t.connectors.docs}</p>
      </Card>
      {current && <MappingEditor key={current} id={current} kind={list.data?.connectors.find((c) => c.id === current)?.kind ?? null} junctions={junctions.data ?? []} />}
    </>
  );
}

function MappingEditor({ id, kind, junctions }: { id: string; kind: string | null; junctions: JunctionInfo[] }) {
  const { t } = useT();
  const res = useApi<{ mapping: ConnectorMapping; from: string }>(`/connectors/${encodeURIComponent(id)}/mapping`);
  const [m, setM] = useState<ConnectorMapping | null>(null);
  const [colours, setColours] = useState("");
  const [rows, setRows] = useState<[string, string][]>([]);
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!res.data) return;
    setM(res.data.mapping);
    setColours(coloursToText(res.data.mapping.colour_values));
    setRows(Object.entries(res.data.mapping.ids ?? {}));
  }, [res.data]);

  const approaches = useMemo(() => junctions.flatMap((j) => j.approaches.map((a) => ({ id: a.id, label: `${j.id} · ${a.name}` }))), [junctions]);
  const draft: ConnectorMapping | null = m && {
    ...m,
    colour_values: textToColours(colours),
    ids: Object.fromEntries(rows.filter(([k, v]) => k.trim() && v)),
  };

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    setStatus(null);
    try {
      await api(`/connectors/${encodeURIComponent(id)}/mapping`, { method: "PATCH", json: draft });
      setStatus({ ok: true, msg: t.connectors.saved });
      res.refresh();
    } catch (e) {
      setStatus({ ok: false, msg: fmt(t.connectors.saveFailed, { msg: e instanceof ApiError ? e.message : String(e) }) });
    } finally {
      setSaving(false);
    }
  };

  if (res.error) return <ErrorNote error={res.error} />;
  if (!m || !draft) return <Card><Loading /></Card>;
  const set = (patch: Partial<ConnectorMapping>) => setM({ ...m, ...patch });

  return (
    <div className="grid min-w-0 gap-4 xl:grid-cols-2">
      <Card title={fmt(t.connectors.mapping, { id })} badge={<span className="faint text-xs">{fmt(t.connectors.from, { from: res.data?.from ?? "" })}</span>}>
        <div className="flex flex-col gap-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="faint text-xs">{t.connectors.tenant}</span>
              <input className="field" value={m.tenant} onChange={(e) => set({ tenant: e.target.value })} />
            </label>
            <label className="flex flex-col gap-1">
              <span className="faint text-xs">{t.connectors.source}</span>
              <select className="field" value={m.source} onChange={(e) => set({ source: e.target.value as ConnectorMapping["source"] })}>
                <option value="ITMS">ITMS</option>
                <option value="CROWD">CROWD</option>
                {kind === "replay" && <option value="SIM">SIM</option>}
              </select>
            </label>
          </div>
          <fieldset className="grid min-w-0 gap-3 sm:grid-cols-2">
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wider">{t.connectors.fields}</legend>
            {FIELD_KEYS.map((k) => (
              <label key={k} className="flex flex-col gap-1">
                <span className="faint text-xs">{t.connectors[`f_${k}` as const]}</span>
                <input className="field num" value={m.fields[k] ?? ""} onChange={(e) => set({ fields: { ...m.fields, [k]: e.target.value } })} />
              </label>
            ))}
          </fieldset>
          <label className="flex flex-col gap-1">
            <span className="faint text-xs">{t.connectors.colours} — {t.connectors.coloursHint}</span>
            <textarea className="field num min-h-20" value={colours} onChange={(e) => setColours(e.target.value)} />
          </label>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider">{t.connectors.ids}</p>
            <div className="flex flex-col gap-2">
              {rows.map(([k, v], i) => (
                <div key={i} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] items-center gap-2">
                  <input className="field num w-full min-w-0" aria-label={t.connectors.vendorKey} placeholder="SIG-105/1" value={k} onChange={(e) => setRows(rows.map((r, j) => (j === i ? [e.target.value, r[1]] : r)))} />
                  <select className="field w-full min-w-0" aria-label={t.connectors.ourApproach} value={v} onChange={(e) => setRows(rows.map((r, j) => (j === i ? [r[0], e.target.value] : r)))}>
                    <option value="">{t.connectors.choose}</option>
                    {approaches.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                    {v && !approaches.some((a) => a.id === v) && <option value={v}>{v}</option>}
                  </select>
                  <button type="button" className="btn !px-2.5 text-xs" onClick={() => setRows(rows.filter((_, j) => j !== i))}>{t.connectors.remove}</button>
                </div>
              ))}
              <button type="button" className="btn self-start text-xs" onClick={() => setRows([...rows, ["", ""]])}>+ {t.connectors.add}</button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn btn-primary" onClick={save} disabled={saving}>{t.connectors.save}</button>
            {status && <span role="status" className={`text-xs ${status.ok ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>{status.msg}</span>}
          </div>
        </div>
      </Card>
      <Preview draft={draft} kind={kind} />
    </div>
  );
}

function Preview({ draft, kind }: { draft: ConnectorMapping; kind: string | null }) {
  const { t } = useT();
  const [format, setFormat] = useState<"records" | "spat">(kind === "spat" ? "spat" : "records");
  const [text, setText] = useState(DEMO_SAMPLE);
  const [out, setOut] = useState<PreviewResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setErr(null);
    let sample: unknown;
    try {
      sample = JSON.parse(text);
    } catch (e) {
      setErr(String(e));
      return;
    }
    setBusy(true);
    try {
      setOut(await api<PreviewResult>("/connectors/preview", { method: "POST", json: { mapping: draft, sample, format, kind } }));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={t.connectors.preview}>
      <div className="flex flex-col gap-3 text-sm">
        <p className="muted text-xs">{t.connectors.previewLead}</p>
        <Segmented label={t.connectors.preview} value={format} onChange={setFormat} options={[{ value: "records", label: t.connectors.records }, { value: "spat", label: t.connectors.spat }]} />
        <textarea className="field num min-h-44 text-xs" aria-label={t.connectors.preview} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn btn-primary" onClick={run} disabled={busy}>{t.connectors.run}</button>
          <button type="button" className="btn text-xs" onClick={() => setText(DEMO_SAMPLE)}>{t.connectors.sampleHint}</button>
        </div>
        {err && <p role="alert" className="text-xs text-[#ff3b30]">{err}</p>}
        {out && out.errors.length > 0 && (
          <div role="alert" className="panel-2 p-3 text-xs">
            <p className="mb-1 font-semibold">{t.connectors.errors}</p>
            <ul className="list-disc pl-4">{out.errors.map((e) => <li key={e}>{e}</li>)}</ul>
          </div>
        )}
        {out && out.errors.length === 0 && (
          <>
            <p className="text-xs">
              <b className="text-[#16a34a]">{fmt(t.connectors.mappedN, { n: out.counts?.mapped ?? out.mapped.length })}</b> ·{" "}
              <b className={out.rejected.length ? "text-[#ffb020]" : "faint"}>{fmt(t.connectors.rejectedN, { n: out.counts?.rejected ?? out.rejected.length })}</b>
            </p>
            <ul className="flex flex-col gap-2">
              {out.mapped.slice(0, 12).map((p, i) => (
                <li key={i} className="panel-2 flex flex-wrap items-center justify-between gap-3 px-3 py-2">
                  <span className="num text-xs font-semibold">{p.approachId}</span>
                  <span className="flex items-center gap-2">
                    <Led colour={p.colour} seconds={p.secondsRemaining} size="sm" />
                    <Badge kind={(["ITMS", "CROWD", "SIM"].includes(p.source) ? p.source : "ITMS") as "ITMS"} />
                  </span>
                </li>
              ))}
            </ul>
            {out.rejected.length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer">{fmt(t.connectors.rejectedN, { n: out.rejected.length })}</summary>
                <pre className="num mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(out.rejected, null, 1)}</pre>
              </details>
            )}
          </>
        )}
      </div>
    </Card>
  );
}
