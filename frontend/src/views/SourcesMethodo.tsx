// Routed placeholder (jalon 8): Conventions, the 2018 ISF→IFI rupture, survey
// limits, licences/attributions (HANDOFF §7), millésimes & Révisions.
import { BookOpenText } from "lucide-react";

export default function SourcesMethodo() {
  return (
    <section className="rounded-lg border border-border bg-background px-6 py-16 text-center">
      <BookOpenText className="mx-auto size-7 text-muted-foreground" aria-hidden />
      <h2 className="mt-3 font-serif text-[1.5rem] font-semibold text-foreground">
        Sources &amp; méthodologie
      </h2>
      <p className="mx-auto mt-2 max-w-prose text-sm text-muted-foreground">
        La page de méthodologie arrive au jalon 8 : Conventions de mesure, rupture ISF→IFI de 2018,
        limites des enquêtes, licences et attributions, millésimes et Révisions. En attendant, la
        provenance de chaque figure reste lisible sous les graphiques du tableau de bord.
      </p>
    </section>
  );
}
