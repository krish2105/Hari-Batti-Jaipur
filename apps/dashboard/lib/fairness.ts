// Suggested fix size for a starved approach (pure). starvation = green given / green needed,
// so the extra green needed is given × (1 / starvation − 1), rounded up to whole seconds.
export function extraGreen(givenS: number | null | undefined, starvation: number): number | null {
  if (!givenS || starvation <= 0 || starvation >= 1) return null;
  return Math.ceil(givenS * (1 / starvation - 1));
}
