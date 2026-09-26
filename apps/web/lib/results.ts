// Types for public/data/results.json (model results exported by scripts/export_results.py).
// Every block is null until its study has run; the Evidence section then shows it as pending.
import raw from "@/public/data/results.json";

export type Mean = { mean: number; ci95: number | null };
export type Controller = {
  id: string; label: string; kind: string; travelTimeS: Mean; waitingTimeS: Mean; stops: Mean; queueVeh: Mean;
  throughputVeh: Mean; co2PerTripG: Mean; unservedVeh: Mean;
};
export type ModelScore = { id: string; label: string; mae: number; rmse: number; wape: number; isBaseline: boolean };
export type Block = { data: string; train: string; test: string; nTrain: number; nTest: number; models: ModelScore[] };
export type Results = {
  generated: string;
  calibration: null | {
    source: string; target: number; unservedTarget: number; calibration: number; validation: number | null; unserved: number | null;
    trialsRun: number; trials: { trial: number; cal: number; val: number; unserved: number; lanes: string }[];
    variants: { id: string; label: string; cal: number; val: number; unserved: number }[]; saturationPcu: number | null;
  };
  optimisation: null | {
    source: string; evalDay: string; window: string; seeds: number; controllers: Controller[];
    greenWave: null | { cycleS: number; speedKmh: number; spacingM: number; bandwidthS: { eastbound: number; westbound: number };
      bandwidthZeroOffsetsS: { eastbound: number; westbound: number }; junctions: { id: string; x: number; cycleS: number; greenS: number; offsetS: number }[] };
  };
  forecast: null | {
    real: Block; sim: Block;
    conformal: { target: number; empirical: number; halfWidthVeh: number };
    phaseChange: null | { target: number; empirical: number; halfWidthS: number; maeS: number };
    anomalies: null | { injected: { recall: number; precision: number; alarmPrecision: number; alarms: number; n: number }; recallByKind: Record<string, number> | null };
    dataQuality: null | { correlation: number; identicalShare: number; medianRatio: number };
  };
  vision: null | {
    dataset: string; images: number; boxes: number; models: { id: string; label: string; map50_95: number; map50: number }[];
    classes: { name: string; ap50_95: number | null; n: number }[]; speedMs: { uvh: number; coco: number } | null;
    videos: { junctionId: string; clip: string; seconds: number; counts: number | null; pedestrianCrossings: number; source: string }[];
  };
};

export const results = raw as unknown as Results;
