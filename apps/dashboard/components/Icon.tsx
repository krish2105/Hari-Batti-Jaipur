// Line icons for the sidebar (24 px grid, stroke = currentColor). Hand-drawn paths, no icon font.
const PATHS: Record<string, string> = {
  overview: "M3 12h4l3-8 4 16 3-8h4",
  live: "M9 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM12 7.5h.01M12 12h.01M12 16.5h.01",
  audit: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  plans: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  insights: "M12 3v3M12 18v3M4.2 7.5l2.6 1.5M17.2 15l2.6 1.5M4.2 16.5l2.6-1.5M17.2 9l2.6-1.5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  copilot: "M4 5h16v11H9l-5 4V5zM8 10h.01M12 10h.01M16 10h.01",
  reports: "M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11zM12 8v3M12 13.5h.01",
  events: "M4 20l4-16M20 20l-4-16M12 4v2M12 10v3M12 17v3",
  monthly: "M6 3h9l4 4v14H6V3zM14 3v5h5M9 13h7M9 17h5",
  admin: "M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3zM9 12l2 2 4-4",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6L6 18",
  sun: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  out: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
};

export function Icon({ name, className = "size-[18px]" }: { name: keyof typeof PATHS | string; className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d={PATHS[name] ?? ""} />
    </svg>
  );
}
