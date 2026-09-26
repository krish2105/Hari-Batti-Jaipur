// Shapes of the API responses the dashboard reads (see services/api/app/routers).
export type ApproachInfo = { id: string; name: string; isMain: boolean; side: string; lanes: number; lanesSource: string };
export type SurveyDay = {
  surveyDate: string; totalVeh: number; totalPcu: number; twoWheelerPct: number;
  amPeakStart: string; amPeakPcuHr: number; pmPeakStart: string; pmPeakPcuHr: number; source: string; sourceLabel: string;
};
export type JunctionInfo = {
  id: string; name: string; tmcCode: string | null; controlType: string; lat: number | null; lng: number | null;
  positionStatus: string; positionNote: string; approaches: ApproachInfo[]; survey: SurveyDay[]; timing?: string;
  hourlyPcu?: Record<string, number[]>; // index = clock hour
};
export type Summary = {
  health: number | null; redWaitS: number | null; cyclesToClear: number | null; starvation: number | null;
  pedRatio: number | null; spillMin: number; flowPcu: number; worstHour: number;
};
export type ApproachHour = {
  approach: string; hour: number; vc: number; x: number; health: number; red_wait_s: number; starvation: number;
  ped_ratio: number; spill_min: number; flow_pcu_h: number; cycles_to_clear: number;
};
export type MetricHour = {
  junction_id: string; survey_date: string; hour: number; hour_start: string; health: number; red_wait_s: number;
  cycles_to_clear: number; starvation: number; ped_ratio: number; spill_min: number; flow_pcu_h: number;
  detail: { Y: number; cycle_s: number; green_s: Record<string, number>; approaches: ApproachHour[]; oversaturated: boolean };
};
export type Metrics = { junctionId: string; summary: Summary; hours: MetricHour[]; source: string; timingLabel: string };
export type Kpis = {
  corridor: string; date: string; junctionsSurveyed: number; totalVehicles24h: number; busiestPmPeak: SurveyDay & { junctionId: string };
  twoWheelerShareAvg: number; surveySource: string; health: Record<string, number>; healthAvg: number; worstJunction: string; metricsSource: string;
};
export type FairnessRow = {
  junctionId: string; hour: number; hourStart: string; approach: string; starvation: number; redWaitS: number;
  pedRatio: number | null; vc: number | null; flowPcuH: number | null; greenS: number | null; cycleS: number | null;
};
export type Fairness = { date: string; top: FairnessRow[]; count: number; method: string; source: string };
export type Colour = "RED" | "AMBER" | "GREEN" | "FLASHING_AMBER";
export type Phase = {
  junctionId: string; approachId: string; colour: Colour; secondsRemaining: number; confidence: number; source: string;
  updatedAt: string; timing?: string; timingLabel?: string; geometry?: string; geometryLabel?: string; simClock?: string;
};
export type PlanSummary = { cycleS: number; mainGreenS: number | null; crossGreenS: number | null; offsetS: number; timing: string; phases: { kind: string; durationS: number }[] };
export type PlanLibrary = {
  available: boolean; geometryLabel?: string; spacingM?: number; spacingSource?: string; order?: string[];
  plans?: Record<string, { label: string; junctions: Record<string, PlanSummary> }>;
};
export type SimSide = { label: string; tripsCompleted: number; meanDelayS: number | null; meanStops: number | null; co2Kg: number; co2PerTripG: number | null; teleports: number };
export type SimResult = { source: string; geometryLabel: string; window: string; baseline: SimSide; proposed: SimSide; changePct: Record<string, number | null>; note: string };
export type SimRun = { id: string; status: "queued" | "running" | "done" | "failed"; request: unknown; result: SimResult | null; error: string | null };
export type CitizenReport = { id: number; type: string; junction_id: string | null; lat: number; lng: number; note: string | null; status: "New" | "Assigned" | "Fixed"; group_key: string; created_at: string };
export type Analytics = { name: string; available: boolean; [k: string]: unknown };

// ---- analysis results served by GET /analytics/{name} (files written by services/sim, ml, cv) ----
// Each is { available: false } until its workstream has run; the dashboard then shows a Pending card.
export type Mean = { mean: number; ci95: number | null }; // mean over seeds ± 95% confidence half-width
export type CalibrationBest = Analytics & {
  trial?: number; params?: Record<string, string | number>; calibration_geh_share?: number; validation_geh_share?: number | null;
  unserved_share?: number | null; trials?: number; objective?: string;
};
export type TableResult = Analytics & { columns?: string[]; rows?: string[][] };
export type ControllerRow = {
  id: string; label: string; kind: string; runs: number; travelTimeS: Mean; waitingTimeS: Mean; stops: Mean; queueVeh: Mean;
  throughputVeh: Mean; co2PerTripG: Mean; unservedVeh: Mean;
};
export type Controllers = Analytics & {
  source?: string; network?: string; trainDay?: string; evalDay?: string; window?: string; seeds?: number[]; controllers?: ControllerRow[];
  isolated?: Record<string, ControllerRow[]>;
  distilled?: { period: string; junctions: Record<string, { cycleS: number; stages: [number, number][]; labels: string[] }> }[]; note?: string;
};
export type TimespaceResult = Analytics & {
  source?: string; speedKmh?: number; spacingM?: number; plan?: string; bandwidthS?: Record<string, number>;
  junctions?: { id: string; x: number; cycleS: number; greenS: number; offsetS: number }[]; note?: string;
};
export type ModelScore = { id: string; label: string; mae: number; rmse: number; wape: number; isBaseline?: boolean };
export type ForecastBlock = { data: string; train: string; test: string; nTrain: number; nTest: number; models: ModelScore[] };
export type Forecast = Analytics & {
  source?: string; horizonMin?: number; real?: ForecastBlock; sim?: ForecastBlock;
  conformal?: { target: number; empirical: number; meanWidthVeh: number; halfWidthVeh: number; data: string };
  phaseChange?: { target: number; empirical: number; halfWidthS: number; maeS: number; data: string } | null;
  dataQuality?: { correlation: number; identicalShare: number; medianRatio: number; note: string }; note?: string;
};
export type AnomalyItem = { junctionId: string; date: string; hour: number; kind: string; score: number; detail: string };
export type Anomalies = Analytics & {
  source?: string; method?: string; items?: AnomalyItem[]; injected?: { precision: number; alarmPrecision: number; alarms: number; recall: number; n: number; data: string }; note?: string;
};
export type CvModel = { id: string; label: string; map50_95: number; map50: number; licence: string };
export type CvEval = Analytics & {
  dataset?: string; images?: number; device?: string; models?: CvModel[]; classes?: { name: string; ap50_95: number; n: number }[];
  pipeline?: Record<string, string>; videos?: { junctionId: string; clip: string; counts: number; source: string }[]; note?: string;
};
export type CopilotAnswer = {
  answer: string; sql: string | null; columns: string[]; rows: (string | number | null)[][];
  chart: { type?: string; x?: string; y?: string } | null; error: string | null; model: string; engine: string; sourceLabel: string;
};
export type AuditEvent = { id: number; ts: string; email: string; role: string; action: string; detail: Record<string, unknown> | null };

// ---- Data connectors (P8 W12, Admin) ----
export type ConnectorMapping = {
  tenant: string; source: "ITMS" | "CROWD" | "SIM"; fields: Record<string, string>; ids: Record<string, string>;
  colour_values?: Record<string, string>; confidence?: number;
};
export type ConnectorHealth = {
  received?: number; rejected?: number; lastDataAgeS?: number | null; clockDriftS?: number; warnings: string[]; readOnly?: boolean;
};
export type ConnectorRow = { id: string; kind: string; tenant: string; source: string; mappedApproaches: number; running: boolean; health: ConnectorHealth };
export type ConnectorList = { active: string; kinds: string[]; connectors: ConnectorRow[]; readOnly: boolean; note: string };
export type PreviewResult = {
  errors: string[]; mapped: { junctionId: string; approachId: string; colour: "RED" | "AMBER" | "GREEN" | "FLASHING_AMBER"; secondsRemaining: number; source: string; updatedAt: string }[];
  rejected: unknown[]; counts?: { mapped: number; rejected: number };
};

// ---- Pilot operations and tenants (P8 W13) ----
export type Measured = { value: number | null; source: string | null; note: string | null; noteHi?: string | null; auto?: boolean };
export type PilotKpi = {
  id: number; key: string; label: string; labelHi: string | null; unit: string; better: "lower" | "higher"; method: string; methodHi: string | null; targetNote: string | null; targetHi: string | null;
  baseline: Measured; current: Measured; change: { abs: number; pct: number | null } | null; updatedBy: string | null; updatedAt: string | null;
};
export type PilotProgress = { status: "not_started" | "scheduled" | "running" | "ended"; day: number | null; days: number | null };
export type Pilot = { id: number; tenantId: string; name: string; startDate: string | null; endDate: string | null; progress: PilotProgress; kpis: PilotKpi[] };
export type ReportTemplate = { title: string; sections: string[]; footer: string };
export type Site = { id: string; name: string; kind: "junction" | "gate"; lat: number | null; lng: number | null; source: string };
export type Tenant = {
  id: string; name: string; kind: string; displayName: string | null; dataSources: string[]; reportTemplate: ReportTemplate;
  openToAll: boolean; demo: boolean; pilots: { id: number; name: string }[]; sites?: Site[]; members?: { email: string; role: string }[];
};
export type KpiTemplate = { key: string; label: string; label_hi: string; unit: string; better: string; method: string; target_note: string };
export type TenantList = { tenants: Tenant[]; kinds: string[]; sources: string[]; kpiTemplates: Record<string, KpiTemplate[]>; reportSections: string[]; connectors: string[] };
export type Note = { id: number; siteId: string; approach: string | null; text: string; pinned: boolean; resolved: boolean; author: string; createdAt: string };
export type FeedbackItem = { insight: string; page: string | null; useful: number; notUseful: number; comments: string[] };
export type FeedbackSummary = { items: FeedbackItem[]; mine: Record<string, boolean>; total: { useful: number; notUseful: number } };
export type ReviewAnswers = { daysUsed: number; mostUseful: string; actionTaken: boolean; actionNote: string; missing: string; rating: number };
export type Review = { weekStart: string; email: string; answers: ReviewAnswers };
export type TimingChange = { id: number; siteId: string; changedOn: string; timeWindow: string | null; before: string; after: string; reason: string | null; enteredBy: string; source: "FIELD" };
export type Evidence = {
  tenant: Tenant; pilot: Pilot; placeholders: string[];
  reviews: { count: number; avgRating: number | null; avgDaysUsed: number | null; actions: { weekStart: string; note: string }[]; missing: { weekStart: string; text: string }[]; weeks: Review[] };
  feedback: FeedbackSummary; changes: TimingChange[]; notes: Note[]; sources: Record<string, string>; readOnly: string;
};
