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
