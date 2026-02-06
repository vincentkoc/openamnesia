import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import { useTheme } from "../../lib/theme";

const tabs = [
  { to: "/stream", label: "stream" },
  { to: "/skills", label: "skills" },
  { to: "/sources", label: "sources" },
] as const;

export function Header() {
  const { theme, toggle } = useTheme();

  return (
    <header className="shrink-0 border-b border-line/50 bg-void-0/90 backdrop-blur-md">
      <div className="flex h-11 items-center justify-between px-5">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent anim-pulse" />
          <span className="text-[12px] font-bold tracking-tight text-text-0">
            amnesia
          </span>
          <span className="text-[8px] tracking-[0.15em] text-text-3">v0.1</span>
        </div>

        {/* Nav */}
        <nav className="flex items-center gap-0.5">
          {tabs.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "relative px-3 py-1 text-[10px] uppercase tracking-[0.15em] font-medium transition-colors",
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

        {/* Right side */}
        <div className="flex items-center gap-3 text-[9px] uppercase tracking-[0.15em] text-text-3">
          <button
            onClick={toggle}
            className="rounded px-1.5 py-0.5 transition-colors hover:bg-void-2 hover:text-text-1"
          >
            {theme === "dark" ? "light" : "dark"}
          </button>
          <span className="text-line/50">|</span>
          <div className="flex items-center gap-1.5">
            <span className="h-1 w-1 rounded-full bg-ok anim-pulse" />
            local
          </div>
        </div>
      </div>
    </header>
  );
}
