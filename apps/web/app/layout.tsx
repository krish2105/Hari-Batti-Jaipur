// Root layout for the web app (placeholder until P4).
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "HariBatti — 3D showcase website",
  description: "HariBatti — Jaipur signal countdown + audit (read-only).",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif" }}>{children}</body>
    </html>
  );
}
