import { useState } from "react";
import Comparison from "./views/Comparison";
import Dashboard from "./views/Dashboard";
import SourcesMethodo from "./views/SourcesMethodo";

type View = "dashboard" | "comparison" | "sources";

const TABS: { id: View; label: string }[] = [
  { id: "dashboard", label: "Tableau de bord" },
  { id: "comparison", label: "Comparaison de sources" },
  { id: "sources", label: "Sources & méthodologie" },
];

export default function App() {
  const [view, setView] = useState<View>("dashboard");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-xl font-semibold">
            Concentration du patrimoine en France depuis 2000
          </h1>
          <nav className="mt-3 flex gap-4 text-sm">
            {TABS.map((t) => (
              <button
                type="button"
                key={t.id}
                onClick={() => setView(t.id)}
                className={view === t.id ? "font-semibold text-blue-700" : "text-gray-500"}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {view === "dashboard" && <Dashboard />}
        {view === "comparison" && <Comparison />}
        {view === "sources" && <SourcesMethodo />}
      </main>
    </div>
  );
}
