// Placeholder home page. The real dashboard is built in P5b.
// It imports the shared packages only to prove the workspace wiring works.
import { DATA_SOURCE_LABELS, type DataSource } from "@haribatti/core";
import { sourceBadgeColours } from "@haribatti/ui";

const sources = Object.keys(DATA_SOURCE_LABELS) as DataSource[];

export default function Home() {
  return (
    <main style={{ padding: 32, maxWidth: 720 }}>
      <h1>HariBatti — Signal Command dashboard</h1>
      <p>Police audit dashboard for the Mansarovar corridor (read-only). Placeholder — built in P5b.</p>
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
