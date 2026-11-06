import { useEffect, useState } from "react";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Button } from "../components/ui";
import { formatWhen } from "../validators";

export default function Settings() {
  const { session } = useAuth();
  const [config, setConfig] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/settings/security").then((response) => setConfig(response.data)).catch((err) => setError(errorMessage(err)));
  }, []);

  async function revokeOthers() {
    setMessage("");
    setError("");
    try {
      const response = await api.post("/auth/revoke-other-sessions");
      setMessage(response.data.detail);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Posture</p>
        <h1 className="mt-1 text-2xl font-semibold">Security settings</h1>
        <p className="mt-1 text-sm text-slate-400">Live configuration from the API. Secrets are not included in this response.</p>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      <section className="grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-5">
          <h2 className="font-semibold">This session</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-slate-400">Expires</dt><dd>{formatWhen(session?.session_expires_at)}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-slate-400">Your active sessions</dt><dd>{session?.active_sessions ?? "—"}</dd></div>
          </dl>
          <Button className="mt-4" tone="ghost" onClick={revokeOthers}>Revoke other sessions</Button>
        </article>
        <article className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-5">
          <h2 className="font-semibold">Authentication policy</h2>
          {config ? (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Environment</dt><dd>{config.environment}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Access token lifetime</dt><dd>{config.access_token_minutes} min</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Secure cookies</dt><dd>{config.cookie_secure ? "On" : "Off in local HTTP"}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Password length</dt><dd>{config.password_min_length}+</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Login limit</dt><dd>{config.rate_limit_login} / {config.rate_limit_window_seconds}s</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-400">Trust proxy headers</dt><dd>{config.trust_proxy ? "Yes" : "No"}</dd></div>
            </dl>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Loading policy…</p>
          )}
        </article>
      </section>
      {config ? (
        <section className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-5">
          <h2 className="font-semibold">Response headers on the API</h2>
          <ul className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
            {config.security_headers.map((header) => (
              <li key={header} className="rounded-xl border border-white/10 px-3 py-2">{header}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            API responses use a strict content security policy because they are JSON, not documents. The Vite development server does not apply that same policy, so hot reload can run. Put a locked policy in front of the production static files.
          </p>
        </section>
      ) : null}
    </div>
  );
}
