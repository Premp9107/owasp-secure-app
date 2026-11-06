export function passwordIssues(password) {
  const issues = [];
  if (password.length < 12) issues.push("At least 12 characters");
  if (!/[a-z]/.test(password)) issues.push("One lowercase letter");
  if (!/[A-Z]/.test(password)) issues.push("One uppercase letter");
  if (!/\d/.test(password)) issues.push("One digit");
  if (!/[^A-Za-z0-9]/.test(password)) issues.push("One symbol");
  if (/\s/.test(password)) issues.push("No spaces");
  return issues;
}

export function formatWhen(value) {
  if (!value) return "—";
  const text = String(value);
  const date = new Date(text.endsWith("Z") ? text : `${text}Z`);
  if (Number.isNaN(date.getTime())) return text;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const EVENT_LABELS = {
  login_success: "Login",
  login_failed: "Failed login",
  logout: "Logout",
  register: "Registration",
  password_change: "Password change",
  role_change: "Role change",
  status_change: "Account update",
  unauthorized: "Unauthorized",
  rate_limited: "Rate limited",
};
