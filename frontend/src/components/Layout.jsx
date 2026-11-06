import { LayoutDashboard, LogOut, ScrollText, Settings, Shield, UserRound, Users } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "analyst", "user"] },
  { to: "/users", label: "Users", icon: Users, roles: ["admin", "analyst"] },
  { to: "/logs", label: "Security logs", icon: ScrollText, roles: ["admin", "analyst"] },
  { to: "/profile", label: "Profile", icon: UserRound, roles: ["admin", "analyst", "user"] },
  { to: "/settings", label: "Settings", icon: Settings, roles: ["admin", "analyst", "user"] },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const visible = links.filter((link) => link.roles.includes(user.role));

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen md:pl-64">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-white/10 bg-[#0b1220]/95 px-4 py-5 md:flex">
        <div className="flex items-center gap-3 px-2">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-slate-950 shadow-glow">
            <Shield size={20} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-wide">Vigil</p>
            <p className="text-xs text-slate-400">Security console</p>
          </div>
        </div>
        <nav className="mt-8 space-y-1">
          {visible.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? "bg-cyan-400/15 text-cyan-100" : "text-slate-300 hover:bg-white/5"}`
              }
            >
              <link.icon size={18} />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto rounded-2xl border border-white/10 bg-white/5 p-3">
          <p className="truncate text-sm font-medium">{user.full_name}</p>
          <p className="truncate text-xs text-slate-400">{user.email}</p>
          <p className="mt-2 text-xs uppercase tracking-wider text-cyan-200">{user.role}</p>
        </div>
      </aside>

      <div className="min-h-screen">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-white/10 bg-[#070d18]/85 px-4 py-3 backdrop-blur md:px-8">
          <div className="flex items-center gap-2 md:hidden">
            <Shield size={18} className="text-cyan-300" />
            <span className="text-sm font-semibold">Vigil</span>
          </div>
          <nav className="flex gap-1 overflow-x-auto md:hidden">
            {visible.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-2.5 py-1.5 text-xs ${isActive ? "bg-cyan-400/15 text-cyan-100" : "text-slate-400"}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto hidden text-right md:block">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Signed in</p>
            <p className="text-sm text-slate-200">{user.full_name}</p>
          </div>
          <button
            onClick={onLogout}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/5"
          >
            <LogOut size={16} />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </header>
        <main className="px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
