import { Activity, ShieldAlert, Users, Waypoints } from "lucide-react";
import { useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import { Alert, Badge } from "../components/ui";
import { EVENT_LABELS, formatWhen } from "../validators";

function Stat({ icon: Icon, label, value, hint }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-4 shadow-glow">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{label}</p>
        <Icon size={18} className="text-cyan-300" />
      </div>
      <p className="mt-3 text-3xl font-semibold text-white">{value ?? "—"}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </article>
  );
}

function EventTable({ title, rows, empty }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-4">
      <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="pb-2 font-medium">When</th>
              <th className="pb-2 font-medium">Event</th>
              <th className="pb-2 font-medium">Detail</th>
              <th className="pb-2 font-medium">IP</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-4 text-slate-500">{empty}</td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-white/5">
                  <td className="py-2 pr-3 text-slate-400">{formatWhen(row.created_at)}</td>
                  <td className="py-2 pr-3"><Badge tone={row.event_type.includes("fail") || row.event_type === "unauthorized" ? "rose" : "cyan"}>{EVENT_LABELS[row.event_type] || row.event_type}</Badge></td>
                  <td className="py-2 pr-3 text-slate-200">{row.message}</td>
                  <td className="py-2 text-slate-400">{row.ip_address || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/dashboard").then((response) => setData(response.data)).catch((err) => setError(errorMessage(err)));
  }, []);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <p className="text-sm text-slate-400">Loading security posture…</p>;

  const max = Math.max(1, ...data.event_counts.map((item) => item.count));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Overview</p>
        <h1 className="mt-1 text-2xl font-semibold">Security dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          {data.scope === "organization"
            ? "Organization view for administrators and security analysts."
            : "Personal view. Organization-wide metrics stay with analysts and administrators."}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={Users} label="Total users" value={data.total_users ?? "Restricted"} hint={data.scope === "organization" ? "Registered accounts" : "Hidden for this role"} />
        <Stat icon={Waypoints} label="Active sessions" value={data.active_sessions} hint={data.scope === "organization" ? "Unexpired, not revoked" : "Your current sessions"} />
        <Stat icon={ShieldAlert} label="Failed logins" value={data.failed_logins_24h} hint="Last 24 hours" />
        <Stat icon={Activity} label="Security events" value={data.security_events_24h} hint="Failures, denials, admin changes" />
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        <section className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-4 xl:col-span-1">
          <h2 className="text-sm font-semibold">Event volume</h2>
          <div className="mt-4 space-y-3">
            {data.event_counts.length === 0 ? <p className="text-sm text-slate-500">No audit events yet.</p> : null}
            {data.event_counts.map((item) => (
              <div key={item.event_type}>
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>{EVENT_LABELS[item.event_type] || item.event_type}</span>
                  <span>{item.count}</span>
                </div>
                <div className="h-2 rounded-full bg-white/5">
                  <div className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-300" style={{ width: `${Math.max(6, (item.count / max) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
        <div className="xl:col-span-2">
          <EventTable title="Recent audit log" rows={data.recent_audit} empty="No audit records in this view." />
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <EventTable title="Recent login activity" rows={data.recent_logins} empty="No successful logins recorded." />
        <EventTable title="Failed login attempts" rows={data.recent_failures} empty="No failed attempts in this view." />
      </div>
      <EventTable title="Security events" rows={data.recent_events} empty="No high-signal events yet." />
    </div>
  );
}
