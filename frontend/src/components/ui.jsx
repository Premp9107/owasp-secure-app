export function Alert({ tone = "error", children }) {
  const tones = {
    error: "border-rose-400/30 bg-rose-400/10 text-rose-100",
    info: "border-cyan-400/30 bg-cyan-400/10 text-cyan-50",
    success: "border-emerald-400/30 bg-emerald-400/10 text-emerald-50",
  };
  return <div className={`rounded-xl border px-3 py-2 text-sm ${tones[tone]}`}>{children}</div>;
}

export function Field({ label, hint, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm text-slate-300">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-slate-500">{hint}</span> : null}
    </label>
  );
}

export function TextInput(props) {
  return (
    <input
      {...props}
      className={`w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none ring-cyan-400/40 placeholder:text-slate-500 focus:border-cyan-400/50 focus:ring-2 ${props.className || ""}`}
    />
  );
}

export function Button({ children, tone = "primary", className = "", ...props }) {
  const tones = {
    primary: "bg-cyan-400 text-slate-950 hover:bg-cyan-300",
    ghost: "border border-white/10 bg-white/5 text-slate-100 hover:bg-white/10",
    danger: "bg-rose-500 text-white hover:bg-rose-400",
  };
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${tones[tone]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-500/15 text-slate-200",
    cyan: "bg-cyan-400/15 text-cyan-200",
    amber: "bg-amber-400/15 text-amber-200",
    rose: "bg-rose-400/15 text-rose-200",
    emerald: "bg-emerald-400/15 text-emerald-200",
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

export function roleTone(role) {
  if (role === "admin") return "amber";
  if (role === "analyst") return "cyan";
  return "slate";
}
