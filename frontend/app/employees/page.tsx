import { Shield } from "lucide-react";

export default function EmployeesPage() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Employee Usage Review</h1>
        <p className="text-sm text-zinc-500 mt-1">Team-first, privacy-aware · admin-restricted individual data</p>
      </div>

      <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-6 flex gap-4">
        <Shield className="h-5 w-5 text-purple-400 shrink-0 mt-0.5" />
        <div className="space-y-2">
          <p className="font-semibold text-zinc-200">Privacy-Aware Design</p>
          <ul className="text-sm text-zinc-400 space-y-1.5 list-disc list-inside">
            <li>Individual-level data is restricted to admin roles only</li>
            <li>Raw prompts are never stored — metadata only</li>
            <li>Team and department rollups are the default view</li>
            <li>No employee ranking or automated performance scoring</li>
            <li>All disciplinary decisions require human review outside this system</li>
            <li>PII redaction applied before any storage</li>
          </ul>
          <p className="text-sm text-zinc-500 mt-3">
            Department-level breakdowns are available on the{" "}
            <a href="/departments" className="text-purple-400 underline">Departments</a> page.
            Individual audit trails are available to admins via the audit log API.
          </p>
        </div>
      </div>
    </div>
  );
}
