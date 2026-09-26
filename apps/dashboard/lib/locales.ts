// Locales, usable on the server and the client.
export const locales = ["en", "hi"] as const;
export type Locale = (typeof locales)[number];

export function isLocale(x: string): x is Locale {
  return (locales as readonly string[]).includes(x);
}
