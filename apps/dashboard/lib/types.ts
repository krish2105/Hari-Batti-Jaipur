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
