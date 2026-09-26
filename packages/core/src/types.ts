// Shared data model for every HariBatti app (website, dashboard, mobile).
// Source: docs/00-overview.md "Architecture", plus the SURVEY data source.
// Read-only: nothing here can control a traffic signal.

/**
 * Where a number or timer came from. Every number shown in any UI must carry one of these.
 * - SIM:    our SUMO simulator (demo only)
 * - FIELD:  our own field work (stopwatch signal timings, tape measures, GPS test drives)
 * - SURVEY: the professional traffic count survey, May 2026 (data/processed/*.csv)
 * - CROWD:  estimates from anonymous app GPS
 * - ITMS:   the Jaipur Police ITMS feed (only after an MoU)
 */
export type DataSource = "SIM" | "FIELD" | "SURVEY" | "CROWD" | "ITMS";

/** Short labels for source badges in the UI. */
export const DATA_SOURCE_LABELS: Record<DataSource, string> = {
  SIM: "Simulated",
  FIELD: "Field measured",
  SURVEY: "Survey, May 2026",
  CROWD: "Crowd estimate",
  ITMS: "Live · ITMS",
};

/** Only these sources can supply a live signal phase (countdown). */
export type PhaseSource = Extract<DataSource, "SIM" | "CROWD" | "ITMS">;

/** How the junction's signal is controlled. */
export type ControlType = "AI_ITMS" | "FIXED" | "FLASHING" | "UNKNOWN";

/** Signal colour shown to one approach. */
export type SignalColour = "RED" | "AMBER" | "GREEN" | "FLASHING_AMBER";

/** One road arm coming into a junction (e.g. "Mansarover Metro" approach at J03). */
export type Approach = {
  id: string; // e.g. "J03-A1"
  name: string; // road name as written in data/junction_registry.csv
};

/** One signalised junction on the map. IDs come ONLY from data/junction_registry.csv (J01–J08). */
export type Junction = {
  id: string; // e.g. "J03"
  name: string; // "Jansunvai Junction"
  lat: number;
  lng: number;
  controlType: ControlType;
  approaches: Approach[]; // one per road arm
};

/** Live state for one approach, pushed every second over WebSocket. */
export type PhaseState = {
  junctionId: string;
  approachId: string;
  colour: SignalColour;
  secondsRemaining: number; // countdown shown to users
  confidence: number; // 0–1; 1.0 only with police feed
  source: PhaseSource; // always shown in UI
  updatedAt: string; // ISO time
  // Optional labels sent by the simulator (P2) so the UI can show what is assumed:
  timing?: "FIELD" | "ASSUMED"; // FIELD = stopwatch timings, ASSUMED = default plan
  timingLabel?: string; // e.g. "Assumed timing – demand-proportional (2-phase, free left)"
  geometry?: "SCHEMATIC" | "OSM" | "OSM_CANDIDATE"; // road network the simulator used
  geometryLabel?: string; // e.g. "Schematic network – coordinates pending"
  simClock?: string; // survey-day clock, e.g. "18:15:03 IST, survey day 2026-05-11"
};
