// Root layout for the dashboard app (placeholder until P5b).
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "HariBatti — Signal Command dashboard",
  description: "HariBatti — Jaipur signal countdown + audit (read-only).",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif" }}>{children}</body>
    </html>
  );
}
