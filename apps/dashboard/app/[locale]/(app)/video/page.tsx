"use client";
// Video intake (P8 W15), Operators: upload a junction video (streamed, checked by the API), draw the
// camera profile on the privacy-blurred first frame, run the CV pipeline and review the FIELD results.
// A demo clip (not a Jaipur junction) can be analysed to learn the tools but never feeds Jaipur data.
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Badge, Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { api, API_URL, ApiError, getSession, roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, num, useT } from "@/lib/i18n";
import type { JunctionInfo } from "@/lib/types";

type Pt = [number, number];
type Job = {
  id: string; junctionId: string; status: string; message: string | null; sizeBytes: number; source: string; rawDeleted: boolean; outputs: string[]; createdAt: string;
  probe: { width: number; height: number; fps: number; seconds: number | null; quality: { ok: boolean; warnings: string[] } } | null;
  profile: Profile | null;
  summary: { seconds: number; counts: number; approachVolumes: Record<string, number>; pedestrianCrossings: number; quality: { ok: boolean; warnings: string[] };
    saturation: { measured: boolean; vehPerHour?: number; pcuPerHour?: number; headways: number; queuedCrossings?: number } } | null;
};
type Side = "N" | "E" | "S" | "W";
type Profile = {
  name?: string; date: string; start_clock: string; approaches: Partial<Record<Side, { name: string; polygon: Pt[]; count_line?: Pt[] }>>;
  stop_line?: { approach: Side; line: Pt[] }; lamp_roi?: number[]; lamp_approach?: Side; crosswalk?: Pt[];
};
type Tool = "polygon" | "count" | "stop" | "lamp" | "cross";
const SIDES: Side[] = ["N", "E", "S", "W"];
const COLOURS: Record<Side, string> = { N: "#3b82f6", E: "#f59e0b", S: "#22c55e", W: "#ec4899" };
const LIVE = ["probing", "analysing"];

async function download(path: string, name: string) {
  const r = await fetch(`${API_URL}${path}`, { headers: { authorization: `Bearer ${getSession()?.token ?? ""}` } });
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export default function VideoIntake() {
  const { t } = useT();
  const v = t.video;
  const { session } = useSession();
  const can = roleAtLeast(session?.role, "Operator");
  const list = useApi<{ uploads: Job[] }>(can ? "/video/uploads" : null, { pollMs: 4000 });
  const junctions = useApi<JunctionInfo[]>(can ? "/junctions" : null);
  const [openId, setOpenId] = useState<string | null>(null);
  if (!can) return (<><PageHead title={v.title} /><Card><p className="text-sm">{v.operatorOnly}</p></Card></>);
  const open = list.data?.uploads.find((u) => u.id === openId) ?? null;
  return (
    <>
      <PageHead title={v.title} lead={v.lead} />
      <ErrorNote error={list.error} />
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <Uploader junctions={junctions.data ?? []} onDone={(id) => { list.refresh(); setOpenId(id); }} />
          <Card title={v.uploads}>
            {!list.data ? <Loading /> : list.data.uploads.length === 0 ? <p className="muted text-sm">{v.none}</p> : (
              <ul className="flex flex-col gap-2">
                {list.data.uploads.map((u) => (
                  <li key={u.id}>
                    <button type="button" onClick={() => setOpenId(u.id)} className={`panel-2 flex w-full flex-wrap items-center justify-between gap-2 px-3 py-2 text-left text-sm ${u.id === openId ? "ring-2 ring-[var(--accent)]" : ""}`}>
                      <span><b className="num">{u.junctionId === "DEMO" ? "DEMO" : u.junctionId}</b> <span className="faint num text-xs">{u.id.slice(0, 6)} · {num(u.sizeBytes / 1e6, 1)} MB</span></span>
                      <span className={`text-xs font-semibold ${u.status === "done" ? "text-[#16a34a]" : u.status === "rejected" || u.status === "failed" ? "text-[#ff3b30]" : ""}`}>{(v as Record<string, string>)[`s_${u.status}`] ?? u.status}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
        {open && <JobView key={open.id} job={open} junction={junctions.data?.find((j) => j.id === open.junctionId) ?? null} onChange={list.refresh} />}
      </div>
    </>
  );
}

function Uploader({ junctions, onDone }: { junctions: JunctionInfo[]; onDone: (id: string) => void }) {
  const { t } = useT();
  const v = t.video;
  const [junction, setJunction] = useState("J05");
  const [file, setFile] = useState<File | null>(null);
  const [pct, setPct] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const send = () => {
    if (!file) return;
    setErr(null);
    setPct(0);
    // XMLHttpRequest for upload progress; the body is the raw file (the API streams it to disk)
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/video/uploads?junction=${junction}&filename=${encodeURIComponent(file.name)}`);
    xhr.setRequestHeader("authorization", `Bearer ${getSession()?.token ?? ""}`);
    xhr.setRequestHeader("content-type", "application/octet-stream");
    xhr.upload.onprogress = (e) => e.lengthComputable && setPct(Math.round((100 * e.loaded) / e.total));
    xhr.onload = () => {
      setPct(null);
      try {
        const j = JSON.parse(xhr.responseText);
        if (xhr.status >= 300) setErr(typeof j.detail === "string" ? j.detail : xhr.statusText);
        else onDone(j.id);
      } catch {
        setErr(xhr.statusText);
      }
    };
    xhr.onerror = () => { setPct(null); setErr("API not reachable"); };
    xhr.send(file);
  };
  return (
    <Card title={v.upload}>
      <div className="flex flex-col gap-3 text-sm">
        <label className="flex flex-col gap-1"><span className="faint text-xs">{v.junction}</span>
          <select className="field" value={junction} onChange={(e) => setJunction(e.target.value)}>
            {junctions.map((j) => <option key={j.id} value={j.id}>{j.id} · {j.name}</option>)}
            <option value="DEMO">{v.demo}</option>
          </select>
        </label>
        <label className="flex flex-col gap-1"><span className="faint text-xs">{v.file}</span>
          <input type="file" accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm,.mp4,.mov,.avi,.mkv,.webm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <button type="button" className="btn btn-primary self-start" disabled={!file || pct !== null} onClick={send}>{pct === null ? v.send : fmt(v.uploading, { pct })}</button>
        {err && <p role="alert" className="text-xs text-[#ff3b30]">{err}</p>}
      </div>
    </Card>
  );
}

function JobView({ job, junction, onChange }: { job: Job; junction: JunctionInfo | null; onChange: () => void }) {
  const { t } = useT();
  const v = t.video;
  const q = job.summary?.quality ?? job.probe?.quality;
  return (
    <div className="flex min-w-0 flex-col gap-4">
      {job.message && <p role="status" className="rounded-lg border border-[#ffb020]/50 bg-[#ffb020]/10 p-3 text-sm">{job.message}</p>}
      {job.junctionId === "DEMO" && <p className="panel-2 p-3 text-xs">{v.demoNote}</p>}
      {job.probe && (
        <Card title={v.quality} badge={<Badge kind="FIELD" />}>
          <p className="text-sm"><b className={q?.ok ? "text-[#16a34a]" : "text-[#ff3b30]"}>{q?.ok ? v.qualityOk : v.withheld}</b> · <span className="num">{job.probe.width}×{job.probe.height} · {job.probe.fps} {v.fps} · {job.probe.seconds ?? "—"} {v.seconds}</span>{job.rawDeleted ? ` · ${v.rawDeleted}` : ""}</p>
          {q && q.warnings.length > 0 && <ul className="mt-1 list-disc pl-5 text-xs">{q.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        </Card>
      )}
      {LIVE.includes(job.status) && <Card><Loading /></Card>}
      {["ready", "done", "failed"].includes(job.status) && job.probe && <Setup job={job} junction={junction} onChange={onChange} />}
      {job.status === "done" && job.summary && <Results job={job} onChange={onChange} />}
    </div>
  );
}

function Setup({ job, junction, onChange }: { job: Job; junction: JunctionInfo | null; onChange: () => void }) {
  const { t } = useT();
  const v = t.video;
  const frame = useApi<{ image: string; width: number; height: number }>(`/video/uploads/${job.id}/frame`);
  const init: Profile = job.profile ?? { date: new Date().toISOString().slice(0, 10), start_clock: "18:00", approaches: {} };
  const [p, setP] = useState<Profile>(init);
  const [tool, setTool] = useState<Tool>("polygon");
  const [side, setSide] = useState<Side>("W");
  const [draft, setDraft] = useState<Pt[]>([]);
  const [maxS, setMaxS] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const names = useMemo(() => junction?.approaches.map((a) => a.name) ?? [], [junction]);
  const [name, setName] = useState(names[0] ?? "");
  useEffect(() => { if (!name && names[0]) setName(names[0]); }, [names, name]);

  const at = (e: MouseEvent<SVGSVGElement>): Pt | null => {
    const el = svg.current;
    const m = el?.getScreenCTM();
    if (!el || !m) return null;
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    return [Math.round(pt.x), Math.round(pt.y)];
  };
  const apr = (s: Side) => p.approaches[s] ?? { name: name || s, polygon: [] };
  const commit = (pts: Pt[]) => {
    if (tool === "polygon" && pts.length >= 3) setP({ ...p, approaches: { ...p.approaches, [side]: { ...apr(side), name: name || apr(side).name, polygon: pts } } });
    if (tool === "count" && pts.length === 2) setP({ ...p, approaches: { ...p.approaches, [side]: { ...apr(side), count_line: pts } } });
    if (tool === "stop" && pts.length === 2) setP({ ...p, stop_line: { approach: side, line: pts } });
    if (tool === "lamp" && pts.length === 2) {
      const [a, b] = pts as [Pt, Pt];
      setP({ ...p, lamp_roi: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])], lamp_approach: side });
    }
    if (tool === "cross" && pts.length >= 3) setP({ ...p, crosswalk: pts });
    setDraft([]);
  };
  const click = (e: MouseEvent<SVGSVGElement>) => {
    const pt = at(e);
    if (!pt) return;
    const next = [...draft, pt];
    if (["count", "stop", "lamp"].includes(tool) && next.length === 2) commit(next);
    else setDraft(next);
  };
  const clear = () => {
    const a = { ...p.approaches };
    if (tool === "polygon") delete a[side];
    if (tool === "count" && a[side]) a[side] = { ...a[side]!, count_line: undefined };
    setP({ ...p, approaches: a, ...(tool === "stop" ? { stop_line: undefined } : {}), ...(tool === "lamp" ? { lamp_roi: undefined, lamp_approach: undefined } : {}), ...(tool === "cross" ? { crosswalk: undefined } : {}) });
    setDraft([]);
  };
  const clean = (x: Profile): Profile => ({ ...x, approaches: Object.fromEntries(Object.entries(x.approaches).filter(([, a]) => a && a.polygon.length >= 3)) as Profile["approaches"] });
  const save = async () => {
    setMsg(null);
    try {
      await api(`/video/uploads/${job.id}/profile`, { method: "PATCH", json: clean(p) });
      setMsg({ ok: true, text: v.saved });
      onChange();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : String(e) });
    }
  };
  const analyse = async () => {
    setMsg(null);
    try {
      await api(`/video/uploads/${job.id}/profile`, { method: "PATCH", json: clean(p) });
      await api(`/video/uploads/${job.id}/analyse`, { method: "POST", json: { maxSeconds: maxS ? Number(maxS) : null } });
      onChange();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : String(e) });
    }
  };
  const poly = (pts: Pt[]) => pts.map((x) => x.join(",")).join(" ");
  const W = frame.data?.width ?? job.probe!.width;
  const H = frame.data?.height ?? job.probe!.height;
  const sw = Math.max(2, W / 400);
  const tools: [Tool, string][] = [["polygon", v.t_polygon], ["count", v.t_count], ["stop", v.t_stop], ["lamp", v.t_lamp], ["cross", v.t_cross]];

  return (
    <Card title={v.setup}>
      <p className="muted mb-3 text-xs">{v.setupLead}</p>
      <div className="mb-3 flex flex-wrap items-end gap-2 text-xs">
        <div className="flex flex-wrap gap-1" role="radiogroup" aria-label={v.setup}>
          {tools.map(([k, label]) => <button key={k} type="button" role="radio" aria-checked={tool === k} className={`btn !min-h-8 !px-2.5 !py-0 text-xs ${tool === k ? "btn-primary" : ""}`} onClick={() => { setTool(k); setDraft([]); }}>{label}</button>)}
        </div>
        {tool !== "cross" && (
          <label className="flex flex-col gap-1"><span className="faint">{tool === "lamp" ? v.lampFor : v.side}</span>
            <select className="field !min-h-8 !py-0" value={side} onChange={(e) => setSide(e.target.value as Side)}>{SIDES.map((s) => <option key={s} value={s}>{s}</option>)}</select>
          </label>
        )}
        {tool === "polygon" && (
          <label className="flex flex-col gap-1"><span className="faint">{v.name}</span>
            {names.length ? (
              <select className="field !min-h-8 !py-0" value={name} onChange={(e) => setName(e.target.value)}>{names.map((n) => <option key={n} value={n}>{n}</option>)}</select>
            ) : <input className="field !min-h-8 !py-0" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />}
          </label>
        )}
        {(tool === "polygon" || tool === "cross") && <button type="button" className="btn !min-h-8 !py-0 text-xs" disabled={draft.length < 3} onClick={() => commit(draft)}>{v.finish}</button>}
        <button type="button" className="btn !min-h-8 !py-0 text-xs" disabled={!draft.length} onClick={() => setDraft(draft.slice(0, -1))}>{v.undo}</button>
        <button type="button" className="btn !min-h-8 !py-0 text-xs" onClick={clear}>{v.clearTool}</button>
      </div>
      {!frame.data ? <Loading /> : (
        <svg ref={svg} viewBox={`0 0 ${W} ${H}`} className="w-full cursor-crosshair rounded-lg border border-[var(--line)]" onClick={click} role="img" aria-label={v.setup} data-testid="frame">
          <image href={frame.data.image} x={0} y={0} width={W} height={H} preserveAspectRatio="none" />
          {SIDES.map((s) => {
            const a = p.approaches[s];
            if (!a) return null;
            return (
              <g key={s}>
                {a.polygon.length >= 3 && <polygon points={poly(a.polygon)} fill={COLOURS[s]} fillOpacity={0.22} stroke={COLOURS[s]} strokeWidth={sw} />}
                {a.polygon[0] && <text x={a.polygon[0][0]} y={a.polygon[0][1]} fontSize={W / 45} fill="#fff" stroke="#000" strokeWidth={sw / 3}>{s} · {a.name}</text>}
                {a.count_line && <polyline points={poly(a.count_line)} stroke={COLOURS[s]} strokeWidth={sw * 2} strokeDasharray={`${sw * 4} ${sw * 2}`} fill="none" />}
              </g>
            );
          })}
          {p.stop_line && <polyline points={poly(p.stop_line.line)} stroke="#fff" strokeWidth={sw * 2.5} fill="none" />}
          {p.lamp_roi && <rect x={p.lamp_roi[0]} y={p.lamp_roi[1]} width={p.lamp_roi[2]} height={p.lamp_roi[3]} fill="none" stroke="#ff3b30" strokeWidth={sw} />}
          {p.crosswalk && <polygon points={poly(p.crosswalk)} fill="#fff" fillOpacity={0.18} stroke="#fff" strokeDasharray={`${sw * 3} ${sw * 2}`} strokeWidth={sw} />}
          {draft.length > 0 && <polyline points={poly(draft)} stroke="#ffb020" strokeWidth={sw} fill="none" />}
          {draft.map((d, i) => <circle key={i} cx={d[0]} cy={d[1]} r={sw * 2} fill="#ffb020" />)}
        </svg>
      )}
      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
        <label className="flex flex-col gap-1"><span className="faint text-xs">{v.date}</span><input type="date" className="field num" value={p.date} onChange={(e) => setP({ ...p, date: e.target.value })} /></label>
        <label className="flex flex-col gap-1"><span className="faint text-xs">{v.clock}</span><input type="time" className="field num" value={p.start_clock} onChange={(e) => setP({ ...p, start_clock: e.target.value })} /></label>
        <label className="flex flex-col gap-1"><span className="faint text-xs">{v.maxSeconds}</span><input className="field num" inputMode="numeric" value={maxS} onChange={(e) => setMaxS(e.target.value.replace(/\D/g, ""))} /></label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" className="btn" onClick={save}>{v.save}</button>
        <button type="button" className="btn btn-primary" onClick={analyse} disabled={job.rawDeleted}>{v.analyse}</button>
        {msg && <span role="status" className={`text-xs ${msg.ok ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>{msg.text}</span>}
      </div>
    </Card>
  );
}

function Results({ job, onChange }: { job: Job; onChange: () => void }) {
  const { t } = useT();
  const v = t.video;
  const s = job.summary!;
  const [msg, setMsg] = useState<string | null>(null);
  const propose = async () => {
    try {
      const r = await api<{ rows: number }>(`/video/uploads/${job.id}/timings-proposal`, { method: "POST" });
      setMsg(fmt(v.proposed, { n: r.rows }));
      onChange();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : String(e));
    }
  };
  return (
    <Card title={v.results} badge={<span className="faint text-xs">{job.source}</span>}>
      {!s.quality.ok ? <p className="text-sm text-[#ff3b30]">{v.withheld}</p> : (
        <div className="flex flex-col gap-3 text-sm">
          <p><b className="num">{num(s.counts)}</b> {v.counts} · <b className="num">{num(s.pedestrianCrossings)}</b> {v.peds} · <span className="num">{s.seconds} {v.seconds}</span></p>
          <div>
            <p className="eyebrow mb-1">{v.volumes}</p>
            <ul className="grid gap-1 sm:grid-cols-2">{Object.entries(s.approachVolumes).map(([k, n]) => <li key={k} className="panel-2 flex justify-between px-3 py-1.5 text-xs"><span>{k}</span><b className="num">{num(n)}</b></li>)}</ul>
          </div>
          <p><span className="eyebrow">{v.saturation}: </span>{s.saturation.measured ? fmt(v.satValue, { v: num(s.saturation.vehPerHour ?? 0), p: num(s.saturation.pcuPerHour ?? 0), n: s.saturation.headways }) : fmt(v.satNotMeasured, { n: s.saturation.queuedCrossings ?? 0 })}</p>
        </div>
      )}
      <div className="mt-4">
        <p className="eyebrow mb-2">{v.downloads}</p>
        <div className="flex flex-wrap gap-2">{job.outputs.map((o) => <button key={o} type="button" className="btn !min-h-8 !py-0 text-xs" onClick={() => download(`/video/uploads/${job.id}/outputs/${o}`, `${job.id}-${o}`)}>{o}</button>)}</div>
      </div>
      {job.junctionId !== "DEMO" && s.quality.ok && job.outputs.includes("signal_timings_field.csv") && (
        <button type="button" className="btn btn-primary mt-4" onClick={propose}>{v.propose}</button>
      )}
      {msg && <p role="status" className="mt-2 text-xs">{msg}</p>}
    </Card>
  );
}
