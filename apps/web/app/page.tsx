// Placeholder home page. The real web is built in P4.
// It imports the shared packages only to prove the workspace wiring works.
import { DATA_SOURCE_LABELS, type DataSource } from "@haribatti/core";
import { sourceBadgeColours } from "@haribatti/ui";

const sources = Object.keys(DATA_SOURCE_LABELS) as DataSource[];

export default function Home() {
  return (
    <main style={{ padding: 32, maxWidth: 720 }}>
      <h1>HariBatti — 3D showcase website</h1>
      <p>Mansarovar corridor pilot, junctions J01–J08. Placeholder — built in P4.</p>
      <p>Every number in HariBatti shows its source:</p>
      <ul style={{ listStyle: "none", padding: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {sources.map((s) => (
          <li
            key={s}
            style={{ background: sourceBadgeColours[s], color: "#fff", padding: "4px 10px", borderRadius: 999 }}
          >
            {s} · {DATA_SOURCE_LABELS[s]}
          </li>
        ))}
      </ul>
    </main>
  );
}
