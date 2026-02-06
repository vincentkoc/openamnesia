import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";

const tabs = [
  { to: "/stream", label: "Stream" },
  { to: "/skills", label: "Skills" },
  { to: "/sources", label: "Sources" },
] as const;

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/50 bg-void-0/90 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-8">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-7 w-7 items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-accent/20 blur-md" />
            <div className="relative h-2 w-2 rounded-full bg-accent anim-pulse" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-bold tracking-tight text-text-0">
              amnesia
            </span>
            <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
              v0.1
            </span>
          </div>
        </div>

        {/* Tabs */}
        <nav className="flex items-center">
          {tabs.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "relative px-4 py-1.5 text-[11px] uppercase tracking-[0.15em] font-medium transition-colors",
                  isActive
                    ? "text-text-0"
                    : "text-text-3 hover:text-text-1",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {label}
                  {isActive && (
                    <span className="absolute bottom-0 left-4 right-4 h-px bg-accent" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <span className="h-1 w-1 rounded-full bg-ok anim-pulse" />
          <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
            local
          </span>
        </div>
      </div>
    </header>
  );
}
