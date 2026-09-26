"use client";
// Section "The mix": the survey's vehicle classes with vehicle share vs road-space (PCU) share,
// the survey's own PCU factors, and an interactive 3D viewer of our Blender model for each class.
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { fmt, num, type Messages } from "@/lib/i18n";
import { site } from "@/lib/site";
import { modelSpec, type ModelName } from "@/lib/vehicleModels";
import { Eyebrow, Reveal, Section } from "./Reveal";

const ModelViewer = dynamic(() => import("@/components/three/ModelViewer"), { ssr: false });

export function Mix({ t, dark }: { t: Messages; dark: boolean }) {
  const classes = site.vehicleClasses.classes;
  const totalPcu = classes.reduce((s, c) => s + c.vehicles * c.pcu, 0);
  const [sel, setSel] = useState(classes[0]!.key);
  const cls = classes.find((c) => c.key === sel)!;
  const [model, setModel] = useState<ModelName>((cls.models[0] as ModelName) ?? "scooter");
  useEffect(() => { if (cls.models[0]) setModel(cls.models[0] as ModelName); }, [cls]);
  const [near, setNear] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => e?.isIntersecting && setNear(true), { rootMargin: "500px" });
    if (box.current) io.observe(box.current);
    return () => io.disconnect();
  }, []);
  const spec = cls.models.length ? modelSpec(model) : null;
  const names = t.mix.names as Record<string, string>;
  const cnames = t.mix.classes as Record<string, string>;
  return (
    <Section id="mix">
      <Reveal className="max-w-2xl">
        <Eyebrow>{t.mix.eyebrow}</Eyebrow>
        <h2 className="display text-4xl font-semibold sm:text-5xl">{t.mix.title}</h2>
        <p className="mt-4 text-lg text-[var(--ink-2)]">{t.mix.lede}</p>
      </Reveal>
      <div className="mt-8 grid gap-4 lg:grid-cols-[1.1fr_1fr] [&>*]:min-w-0">
        <Reveal className="surface relative overflow-hidden rounded-3xl">
          <div ref={box} className="h-[340px] sm:h-[440px]">
            {near && cls.models.length > 0 ? <ModelViewer model={model} dark={dark} /> : (
              <p className="grid h-full place-items-center p-6 text-sm text-[var(--ink-2)]">{cls.models.length ? "…" : t.mix.noModel}</p>
            )}
          </div>
          <div className="absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-2 p-4">
            <div className="flex flex-wrap gap-2" role="tablist" aria-label={t.mix.models}>
              {cls.models.map((m) => (
                <button key={m} role="tab" aria-selected={m === model} onClick={() => setModel(m as ModelName)}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${m === model ? "border-[var(--accent)] bg-[var(--accent-2)]/20" : "border-[var(--line)] surface"}`}>
                  {names[m] ?? m}
                </button>
              ))}
            </div>
            {spec && (
              <p className="surface rounded-lg px-2 py-1 text-[11px] text-[var(--ink-2)]">
                {fmt(t.mix.size, { l: spec.dims.length_m, w: spec.dims.width_m, h: spec.dims.height_m })} · {fmt(t.mix.tris, { n: num(spec.dims.triangles) })}
              </p>
            )}
          </div>
          <p className="absolute left-4 top-3 text-[11px] text-[var(--ink-2)]">{t.mix.drag}</p>
        </Reveal>
        <Reveal delay={0.1} className="surface rounded-3xl p-5">
          <div className="mb-3 flex items-center justify-between"><SourceBadge kind="SURVEY" t={t.badge} /><span className="text-xs text-[var(--ink-2)]">{t.mix.vehicles} · {t.mix.pcu}</span></div>
          <ul className="grid gap-1.5">
            {classes.map((c) => {
              const pcuShare = (c.vehicles * c.pcu) / totalPcu;
              const on = c.key === sel;
              return (
                <li key={c.key}>
                  <button onClick={() => setSel(c.key)} aria-pressed={on}
                    className={`w-full rounded-xl border px-3 py-2 text-left ${on ? "border-[var(--accent)] bg-[var(--accent-2)]/12" : "border-transparent hover:border-[var(--line)]"}`}>
                    <div className="flex items-baseline justify-between gap-2 text-sm">
                      <span className="truncate font-semibold">{cnames[c.key] ?? c.label}</span>
                      <span className="shrink-0 text-[var(--ink-2)]">{t.mix.factor} <b className="text-[var(--ink)]">{c.pcu}</b></span>
                    </div>
                    <div className="mt-1.5 grid gap-1" aria-hidden>
                      <div className="h-1.5 rounded-full bg-[var(--ink)]/8"><div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${Math.max(0.6, c.share * 100)}%` }} /></div>
                      <div className="h-1.5 rounded-full bg-[var(--ink)]/8"><div className="h-full rounded-full bg-[#3b82f6]" style={{ width: `${Math.max(0.6, pcuShare * 100)}%` }} /></div>
                    </div>
                    <div className="mt-1 flex justify-between text-[11px] text-[var(--ink-2)]">
                      <span>{num(c.share * 100, 1)}% {t.mix.vehicles}</span><span>{num(pcuShare * 100, 1)}% {t.mix.pcu}</span><span>{num(c.vehicles)} {t.mix.counted}</span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-[var(--ink-2)]">{fmt(t.mix.fit, { r2: site.vehicleClasses.pcuFitR2 })} {t.mix.autos}</p>
        </Reveal>
      </div>
    </Section>
  );
}
