import { ShieldOff } from "lucide-react";
import { Link } from "react-router-dom";

export default function Denied() {
  return (
    <div className="grid min-h-[70vh] place-items-center">
      <div className="max-w-lg rounded-3xl border border-rose-400/20 bg-[#0e1728]/90 p-8 text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-rose-400/15 text-rose-200">
          <ShieldOff />
        </div>
        <h1 className="mt-4 text-2xl font-semibold">Access denied</h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          Your role does not include this area. The API enforces the same restriction, and the attempt is written to the audit log.
        </p>
        <Link to="/" className="mt-6 inline-flex rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950">
          Return to dashboard
        </Link>
      </div>
    </div>
  );
}
