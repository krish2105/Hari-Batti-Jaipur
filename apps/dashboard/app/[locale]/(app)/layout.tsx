// Every signed-in screen shares the sidebar/top-bar frame and the pilot context (tenant + feedback).
import type { ReactNode } from "react";
import { Shell } from "@/components/Shell";
import { PilotProvider } from "@/lib/pilot";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Shell>
      <PilotProvider>{children}</PilotProvider>
    </Shell>
  );
}
