import { useState } from "react";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Badge, Button, Field, TextInput, roleTone } from "../components/ui";
import { passwordIssues } from "../validators";

export default function Profile() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user.full_name);
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const issues = passwords.new_password ? passwordIssues(passwords.new_password) : [];

  async function saveName(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const response = await api.patch("/users/me", { full_name: name.trim() });
      refresh({ ...user, ...response.data, user: response.data });
      setMessage("Profile updated.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function savePassword(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (issues.length) {
      setError("The new password does not meet the policy.");
      return;
    }
    try {
      await api.post("/users/me/password", passwords);
      setPasswords({ current_password: "", new_password: "" });
      setMessage("Password updated. Other sessions were revoked.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Account</p>
        <h1 className="mt-1 text-2xl font-semibold">Profile</h1>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      <section className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">{user.email}</p>
            <p className="text-xs text-slate-500">Email is the account identifier and cannot be changed here.</p>
          </div>
          <Badge tone={roleTone(user.role)}>{user.role}</Badge>
        </div>
        <form onSubmit={saveName} className="space-y-4">
          <Field label="Display name">
            <TextInput value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={80} required />
          </Field>
          <Button type="submit">Save profile</Button>
        </form>
      </section>
      <section className="rounded-2xl border border-white/10 bg-[#0e1728]/90 p-5">
        <h2 className="text-lg font-semibold">Change password</h2>
        <form onSubmit={savePassword} className="mt-4 space-y-4">
          <Field label="Current password">
            <TextInput type="password" autoComplete="current-password" value={passwords.current_password} onChange={(event) => setPasswords((current) => ({ ...current, current_password: event.target.value }))} required />
          </Field>
          <Field label="New password">
            <TextInput type="password" autoComplete="new-password" value={passwords.new_password} onChange={(event) => setPasswords((current) => ({ ...current, new_password: event.target.value }))} required />
          </Field>
          {issues.length ? <ul className="text-xs text-slate-400">{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : null}
          <Button type="submit">Update password</Button>
        </form>
      </section>
    </div>
  );
}
