import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { cn } from "@/lib/utils";
import Comparison from "./views/Comparison";
import Dashboard from "./views/Dashboard";
import SourcesMethodo from "./views/SourcesMethodo";

const TABS = [
  { to: "/dashboard", label: "Tableau de bord" },
  { to: "/comparison", label: "Comparaison de sources" },
  { to: "/sources", label: "Sources & méthodologie" },
];

function Tab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          // Tabs read as an underline, never a boxed/pill control (DESIGN.md §5).
          "relative -mb-px border-b-2 px-1 py-3 text-title font-semibold transition-colors outline-none",
          "focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          isActive
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Aller au contenu
      </a>
      <header className="border-b border-border bg-background">
        <div className="mx-auto max-w-6xl px-5 pt-6">
          <p className="font-sans text-label font-medium text-muted-foreground uppercase">
            France · depuis 2000
          </p>
          <h1 className="mt-1 font-serif text-display font-semibold text-foreground">
            Concentration du patrimoine
          </h1>
          <nav className="mt-4 flex gap-6 border-b border-border" aria-label="Sections">
            {TABS.map((t) => (
              <Tab key={t.to} {...t} />
            ))}
          </nav>
        </div>
      </header>
      <main id="contenu" className="mx-auto max-w-6xl px-5 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/comparison" element={<Comparison />} />
          <Route path="/sources" element={<SourcesMethodo />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
