import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { cn } from "../../lib/utils";
import { useTheme } from "../../lib/theme";
import { api } from "../../lib/api";
import { numberFormat } from "../../lib/utils";

const tabs = [
  { to: "/stream", label: "stream" },
  { to: "/skills", label: "skills" },
  { to: "/sources", label: "sources" },
] as const;

export function Header() {
  const { theme, toggle } = useTheme();
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const [clock, setClock] = useState(() => formatClock());

  useEffect(() => {
    const id = setInterval(() => setClock(formatClock()), 1000);
    return () => clearInterval(id);
  }, []);

  const sources = stats?.sources ?? [];

  // Build ticker items: main stats + per-source counts
  const tickerItems: { label: string; value: string; accent?: boolean }[] = [];
  if (stats) {
    tickerItems.push(
      { label: "events", value: numberFormat(stats.total_events) },
      { label: "sessions", value: numberFormat(stats.total_sessions) },
      { label: "moments", value: numberFormat(stats.total_moments) },
      { label: "skills", value: String(stats.total_skills) },
      { label: "24h", value: numberFormat(stats.recent_events_24h), accent: true },
    );
    for (const s of sources) {
      tickerItems.push({ label: s.source, value: numberFormat(s.event_count) });
    }
  }

  return (
    <header className="shrink-0 bg-void-0/90 backdrop-blur-md">
      {/* Row 1: 36px — Logo, nav, clock, theme, connection */}
      <div className="flex h-9 items-center justify-between border-b border-line/50 px-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent anim-pulse" />
          <span className="font-sans text-[13px] font-bold uppercase tracking-tight text-text-0">
            AMNESIA
          </span>
        </div>

        {/* Nav */}
        <nav className="flex items-center gap-0.5">
          {tabs.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "relative px-3 py-1 font-sans text-[10px] uppercase tracking-[0.15em] font-medium transition-colors",
                  isActive ? "text-text-0" : "text-text-3 hover:text-text-1",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {label}
                  {isActive && (
                    <span className="absolute bottom-0 left-3 right-3 h-[2px] rounded-full bg-accent" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right: clock, theme, connection */}
        <div className="flex items-center gap-3 text-[9px] uppercase tracking-[0.15em] text-text-3">
          <span className="font-mono text-[11px] tabular-nums text-text-1">{clock}</span>
          <span className="text-line/30">|</span>
          <button
            onClick={toggle}
            className="rounded px-1.5 py-0.5 font-sans transition-colors hover:bg-void-2 hover:text-text-1"
          >
            {theme === "dark" ? "light" : "dark"}
          </button>
          <span className="text-line/30">|</span>
          <div className="flex items-center gap-1.5">
            <span className="h-1 w-1 rounded-full bg-ok anim-pulse" />
            local
          </div>
        </div>
      </div>

      {/* Row 2: 24px — Scrolling stats ticker */}
      <div className="flex h-6 items-center border-b border-line/30 bg-void-1/50">
        <div className="ticker-track flex-1">
          <div className="ticker-inner gap-0">
            {/* Duplicate for seamless loop */}
            {[0, 1].map((copy) => (
              <span key={copy} className="inline-flex items-center">
                {tickerItems.map((item, i) => (
                  <span key={`${copy}-${i}`} className="inline-flex items-center">
                    <span className="stat-pip mx-3">
                      <span className={cn("stat-value text-[10px]", item.accent && "!text-accent")}>
                        {item.value}
                      </span>
                      <span className="stat-label text-[8px]">{item.label}</span>
                    </span>
                    {i < tickerItems.length - 1 && (
                      <span className="text-[8px] text-line/40">|</span>
                    )}
                  </span>
                ))}
              </span>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}

function formatClock(): string {
  const now = new Date();
  return (
    String(now.getHours()).padStart(2, "0") +
    ":" +
    String(now.getMinutes()).padStart(2, "0") +
    ":" +
    String(now.getSeconds()).padStart(2, "0")
  );
}
