import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, useMemo } from "react";
import { cn, formatTime, truncate, sourceColor } from "../../lib/utils";
import { useTheme } from "../../lib/theme";
import { api } from "../../lib/api";
import { IconDefragLogo, IconActivity, IconZap, IconDatabase, IconExport } from "../common/Icons";

const tabs = [
  { to: "/stream", label: "stream", icon: IconActivity },
  { to: "/skills", label: "skills", icon: IconZap },
  { to: "/sources", label: "sources", icon: IconDatabase },
  { to: "/exports", label: "exports", icon: IconExport },
] as const;

export function Header() {
  const { theme, toggle } = useTheme();
  const { data: events } = useQuery({
    queryKey: ["events"],
    queryFn: () => api.events({ limit: 30 }),
  });
  const { data: moments } = useQuery({
    queryKey: ["moments"],
    queryFn: () => api.moments({ limit: 10 }),
  });
  const [clock, setClock] = useState(() => formatClock());

  useEffect(() => {
    const id = setInterval(() => setClock(formatClock()), 1000);
    return () => clearInterval(id);
  }, []);

  // Build ticker items from real events and moments
  const tickerItems = useMemo(() => {
    const items: { text: string; source: string; type: "event" | "moment" }[] = [];

    if (moments?.items) {
      for (const m of moments.items) {
        items.push({
          text: `[${m.source ?? "?"}] ${m.intent ?? m.summary ?? ""}`,
          source: m.source ?? "",
          type: "moment",
        });
      }
    }
    if (events?.items) {
      for (const e of events.items.slice(0, 20)) {
        items.push({
          text: `${formatTime(e.ts)} ${e.actor}${e.tool_name ? "/" + e.tool_name : ""}: ${truncate(e.content, 80)}`,
          source: e.source,
          type: "event",
        });
      }
    }
    return items;
  }, [events, moments]);

  return (
    <header className="shrink-0 bg-void-0/90 backdrop-blur-md">
      {/* Row 1: 42px — Logo, nav, clock, theme, db */}
      <div className="flex h-[42px] items-center justify-between border-b border-line/50 px-5">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <IconDefragLogo size={22} className="text-accent" />
          <span className="font-mono text-[15px] font-bold tracking-tight text-text-0">
            Open<span className="text-accent">Amnesia</span>
          </span>
        </div>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {tabs.map(({ to, label, icon: TabIcon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-1 px-3 py-1.5 font-sans text-[11px] uppercase tracking-[0.12em] font-medium transition-colors",
                  isActive ? "text-text-0" : "text-text-3 hover:text-text-1",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <TabIcon size={12} />
                  {label}
                  {isActive && (
                    <span className="absolute bottom-0 left-3 right-3 h-[2px] rounded-full bg-accent" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right: clock, theme, db */}
        <div className="flex items-center gap-3 text-[9px] uppercase tracking-[0.12em] text-text-3">
          <span className="font-mono text-[12px] tabular-nums text-text-1">{clock}</span>
          <span className="text-line/30">|</span>
          <button
            onClick={toggle}
            className="rounded px-1.5 py-0.5 font-sans transition-colors hover:bg-void-2 hover:text-text-1"
          >
            {theme === "dark" ? "light" : "dark"}
          </button>
          <span className="text-line/30">|</span>
          <div className="flex items-center gap-1.5">
            <span className="h-[6px] w-[6px] rounded-full bg-ok anim-led text-ok" />
            <svg width="10" height="10" viewBox="0 0 16 16" fill="none" className="text-text-3">
              <path d="M2 4h12v8H2z" stroke="currentColor" strokeWidth="1.5" fill="none" rx="1" />
              <path d="M5 4V2h6v2" stroke="currentColor" strokeWidth="1.5" fill="none" />
              <line x1="5" y1="7" x2="11" y2="7" stroke="currentColor" strokeWidth="1" />
              <line x1="5" y1="9.5" x2="9" y2="9.5" stroke="currentColor" strokeWidth="1" />
            </svg>
            <span className="font-mono text-[8px] text-text-3">sqlite.db</span>
          </div>
        </div>
      </div>

      {/* Row 2: 26px — Scrolling event/memory stream */}
      <div className="flex h-[26px] items-center border-b border-line/30 bg-void-1/40">
        <div className="ticker-track flex-1">
          <div className="ticker-inner gap-0">
            {[0, 1].map((copy) => (
              <span key={copy} className="inline-flex items-center">
                {tickerItems.map((item, i) => (
                  <span key={`${copy}-${i}`} className="inline-flex items-center">
                    <span className={cn("mx-1 h-1 w-1 rounded-full", sourceColor(item.source))} />
                    <span className={cn(
                      "mx-1 font-mono text-[10px]",
                      item.type === "moment" ? "text-accent font-medium" : "text-text-2",
                    )}>
                      {item.text}
                    </span>
                    <span className="mx-2 text-[8px] text-line/30">&bull;</span>
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
