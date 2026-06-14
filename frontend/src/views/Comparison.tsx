// Routed placeholder (jalon 5): overlay WID vs INSEE vs DGFiP for one
// indicateur/groupe. The legend will state each line's Convention
// (unité/concept); sources are overlaid, never merged.
import { GitCompareArrows } from "lucide-react";

export default function Comparison() {
  return (
    <section className="rounded-lg border border-border bg-background px-6 py-16 text-center">
      <GitCompareArrows className="mx-auto size-7 text-muted-foreground" aria-hidden />
      <h2 className="mt-3 font-serif text-[1.5rem] font-semibold text-foreground">
        Comparaison de sources
      </h2>
      <p className="mx-auto mt-2 max-w-prose text-sm text-muted-foreground">
        La superposition WID / INSEE / DGFiP arrive au jalon 5. Chaque courbe portera sa Convention
        (unité et concept) : les sources sont comparées côte à côte, jamais fusionnées en une seule
        série.
      </p>
    </section>
  );
}
