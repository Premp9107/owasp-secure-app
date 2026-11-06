import { useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Badge, roleTone } from "../components/ui";
import { formatWhen } from "../validators";

export default function Users() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load(nextQuery = query) {
    const response = await api.get("/users", { params: nextQuery ? { q: nextQuery } : {} });
    setRows(response.data);
  }

  useEffect(() => {
    load("").catch((err) => setError(errorMessage(err)));
  }, []);

  async function onSearch(event) {
    event.preventDefault();
    setError("");
    try {
      await load(query.trim());
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function updateUser(id, path, body, success) {
    setError("");
    setNotice("");
    try {
      await api.patch(`/users/${id}/${path}`, body);
      setNotice(success);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Directory</p>
        <h1 className="mt-1 text-2xl font-semibold">User management</h1>
        <p className="mt-1 text-sm text-slate-400">Analysts can review accounts. Only administrators can change roles or disable access.</p>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <form onSubmit={onSearch} className="flex flex-col gap-2 sm:flex-row">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search name or email"
          className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm outline-none focus:border-cyan-400/50"
        />
        <button className="rounded-xl bg-white/10 px-4 py-2.5 text-sm font-medium hover:bg-white/15">Search</button>
      </form>
      <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#0e1728]/90">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-white/5">
                <td className="px-4 py-3 text-slate-100">{row.full_name}</td>
                <td className="px-4 py-3 text-slate-300">{row.email}</td>
                <td className="px-4 py-3">
                  {user.role === "admin" ? (
                    <select
                      value={row.role}
                      disabled={row.id === user.id}
                      onChange={(event) => updateUser(row.id, "role", { role: event.target.value }, "Role updated. Existing sessions for that account were revoked.")}
                      className="rounded-lg border border-white/10 bg-slate-950 px-2 py-1 text-sm"
                    >
                      <option value="user">user</option>
                      <option value="analyst">analyst</option>
                      <option value="admin">admin</option>
                    </select>
                  ) : (
                    <Badge tone={roleTone(row.role)}>{row.role}</Badge>
                  )}
                </td>
                <td className="px-4 py-3">
                  {user.role === "admin" ? (
                    <button
                      disabled={row.id === user.id}
                      onClick={() => updateUser(row.id, "status", { is_active: !row.is_active }, row.is_active ? "Account disabled." : "Account enabled.")}
                      className="text-cyan-200 disabled:text-slate-500"
                    >
                      {row.is_active ? "Active" : "Disabled"}
                    </button>
                  ) : (
                    <Badge tone={row.is_active ? "emerald" : "rose"}>{row.is_active ? "Active" : "Disabled"}</Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-400">{formatWhen(row.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
