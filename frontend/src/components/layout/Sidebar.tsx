import { NavLink } from "react-router-dom";
import { Activity, Brain, Cpu, Layers, Settings } from "lucide-react";
import { cn } from "../../lib/utils";

const links = [
  { to: "/stream", label: "Stream", icon: Activity },
  { to: "/skills", label: "Skills", icon: Brain },
  { to: "/sources", label: "Sources", icon: Cpu },
] as const;

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-[220px] flex-col border-r border-cream-300 bg-cream-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-700">
          <Layers className="h-4 w-4 text-white" />
        </div>
        <div>
          <span className="text-[15px] font-semibold tracking-tight text-ink-500">
            Amnesia
          </span>
          <span className="ml-1 text-[10px] font-medium text-ink-50">v0.1</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="mt-2 flex flex-1 flex-col gap-0.5 px-3">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                isActive
                  ? "bg-cream-200 text-ink-500"
                  : "text-ink-50 hover:bg-cream-100 hover:text-ink-300",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-cream-300 px-3 py-3">
        <NavLink
          to="/sources"
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium text-ink-50 hover:bg-cream-100 hover:text-ink-300"
        >
          <Settings className="h-4 w-4" />
          Settings
        </NavLink>
        <div className="mt-2 px-3 text-[11px] text-cream-500">
          Local-first memory
        </div>
      </div>
    </aside>
  );
}
