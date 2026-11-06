import { useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import { Alert, Badge } from "../components/ui";
import { EVENT_LABELS, formatWhen } from "../validators";

const filters = ["", "login_success", "login_failed", "logout", "register", "password_change", "role_change", "status_change", "unauthorized", "rate_limited"];

export default function Logs() {
  const [rows, setRows] = useState([]);
  const [eventType, setEventType] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = eventType ? { event_type: eventType, limit: 100 } : { limit: 100 };
    api
      .get("/logs", { params })
      .then((response) => setRows(response.data))
      .catch((err) => setError(errorMessage(err)));
  }, [eventType]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Audit</p>
          <h1 className="mt-1 text-2xl font-semibold">Security logs</h1>
          <p className="mt-1 text-sm text-slate-400">Passwords and tokens are never written to this trail.</p>
        </div>
        <select value={eventType} onChange={(event) => setEventType(event.target.value)} className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm">
          {filters.map((value) => (
            <option key={value || "all"} value={value}>{value ? EVENT_LABELS[value] : "All events"}</option>
          ))}
        </select>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0e1728]/90">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">When</th>
              <th className="px-4 py-3 font-medium">Event</th>
              <th className="px-4 py-3 font-medium">Subject</th>
              <th className="px-4 py-3 font-medium">Message</th>
              <th className="px-4 py-3 font-medium">IP</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-white/5">
                <td className="px-4 py-3 text-slate-400">{formatWhen(row.created_at)}</td>
                <td className="px-4 py-3"><Badge tone={row.event_type === "login_failed" || row.event_type === "unauthorized" || row.event_type === "rate_limited" ? "rose" : "cyan"}>{EVENT_LABELS[row.event_type] || row.event_type}</Badge></td>
                <td className="px-4 py-3 text-slate-300">{row.subject || "—"}</td>
                <td className="px-4 py-3 text-slate-100">{row.message}</td>
                <td className="px-4 py-3 text-slate-400">{row.ip_address || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
