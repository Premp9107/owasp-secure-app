import { Shield } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Button, Field, TextInput } from "../components/ui";
import { passwordIssues } from "../validators";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const issues = form.password ? passwordIssues(form.password) : [];

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (issues.length) {
      setError("Choose a stronger password before submitting.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Unable to create the account"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-12">
      <form onSubmit={onSubmit} className="w-full max-w-md space-y-5 rounded-3xl border border-white/10 bg-[#0e1728]/90 p-6 shadow-glow md:p-8">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400 text-slate-950">
            <Shield size={18} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Register</p>
            <h1 className="text-2xl font-semibold">Create a user account</h1>
          </div>
        </div>
        <p className="text-sm text-slate-400">New accounts are normal users. An administrator assigns other roles.</p>
        {error ? <Alert>{error}</Alert> : null}
        <Field label="Full name">
          <TextInput name="full_name" value={form.full_name} onChange={update} minLength={2} maxLength={80} required />
        </Field>
        <Field label="Email">
          <TextInput name="email" type="email" autoComplete="username" value={form.email} onChange={update} required />
        </Field>
        <Field label="Password" hint="12 or more characters, mixed case, a digit, and a symbol.">
          <TextInput name="password" type="password" autoComplete="new-password" value={form.password} onChange={update} required />
        </Field>
        {form.password ? (
          <ul className="space-y-1 text-xs text-slate-400">
            {issues.length ? issues.map((issue) => <li key={issue}>{issue}</li>) : <li className="text-emerald-300">Password meets the policy.</li>}
          </ul>
        ) : null}
        <Button className="w-full" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-sm text-slate-400">
          Already registered? <Link className="text-cyan-300" to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
