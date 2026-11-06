import { Shield } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Button, Field, TextInput } from "../components/ui";

const demos = [
  ["Administrator", "admin@example.com", "VigilAdmin!234"],
  ["Security analyst", "analyst@example.com", "VigilAnalyst!234"],
  ["Normal user", "user@example.com", "VigilUser!234"],
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      navigate(location.state?.from || "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Unable to sign in"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between border-r border-white/10 px-12 py-12 lg:flex">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan-400 text-slate-950">
            <Shield size={22} />
          </div>
          <div>
            <p className="text-lg font-semibold">Vigil</p>
            <p className="text-sm text-slate-400">Security operations console</p>
          </div>
        </div>
        <div className="max-w-md">
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-200">Portfolio demonstration</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight text-white">
            Authentication, audit, and access control in one console.
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-400">
            Sessions are server-side JWT records. Roles are enforced by the API. Passwords are stored only as Argon2id hashes.
          </p>
        </div>
        <p className="text-xs text-slate-500">Local demo data is seeded on an empty database. These are not production accounts.</p>
      </section>
      <section className="flex items-center justify-center px-4 py-12">
        <form onSubmit={onSubmit} className="w-full max-w-md space-y-5 rounded-3xl border border-white/10 bg-[#0e1728]/90 p-6 shadow-glow md:p-8">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Sign in</p>
            <h2 className="mt-2 text-2xl font-semibold">Welcome back</h2>
          </div>
          {error ? <Alert>{error}</Alert> : null}
          <Field label="Email">
            <TextInput type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Password">
            <TextInput type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <Button className="w-full" disabled={busy}>
            {busy ? "Checking credentials…" : "Sign in"}
          </Button>
          <p className="text-sm text-slate-400">
            No account? <Link className="text-cyan-300" to="/register">Create one</Link>
          </p>
          <div className="space-y-2 rounded-2xl border border-white/10 bg-black/20 p-3">
            <p className="text-xs uppercase tracking-wider text-slate-500">Seeded local accounts</p>
            {demos.map(([label, demoEmail, demoPassword]) => (
              <button
                key={demoEmail}
                type="button"
                onClick={() => {
                  setEmail(demoEmail);
                  setPassword(demoPassword);
                }}
                className="flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-left text-sm hover:bg-white/5"
              >
                <span>{label}</span>
                <span className="text-xs text-slate-500">{demoEmail}</span>
              </button>
            ))}
          </div>
        </form>
      </section>
    </div>
  );
}
