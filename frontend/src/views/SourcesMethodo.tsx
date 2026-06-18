// Sources & méthodologie (jalons 6 + 8): the editorial heart of the explainer.
// It teaches the Conventions and why they are not interchangeable, the 2018
// ISF→IFI rupture, the survey limits, and the millésimes/révisions — then backs
// the licences with /api/sources and wraps the jalon-6 Révisions table.
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { api } from "@/api/client";
import { ErrorState, FigureSkeleton } from "@/components/figure";
import RevisionsTable from "@/components/RevisionsTable";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-serif text-headline font-semibold text-foreground">{title}</h2>
      <div className="max-w-[68ch] space-y-3 text-body text-foreground/90">{children}</div>
    </section>
  );
}

export default function SourcesMethodo() {
  const sourcesQ = useQuery({
    queryKey: ["sources"],
    queryFn: api.sources,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const revisionsQ = useQuery({ queryKey: ["revisions"], queryFn: api.revisions });
  // Meta carries `tranche_taux`, so a revised IFI tranche reads as its rate
  // ("Tranche à 0,7 %") rather than an opaque ordinal (issue #15).
  const metaQ = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
    staleTime: Number.POSITIVE_INFINITY,
  });

  return (
    <div className="space-y-12">
      <header className="max-w-[68ch] space-y-2">
        <h1 className="font-serif text-headline font-semibold text-foreground">
          Sources &amp; méthodologie
        </h1>
        <p className="text-body text-muted-foreground">
          Trois sources publiques mesurent la concentration du patrimoine en France, chacune avec sa
          propre définition. Cette page explique ce que chaque chiffre signifie, pourquoi on ne les
          additionne pas, et d'où ils viennent.
        </p>
      </header>

      <Section title="Trois sources, trois Conventions">
        <p>
          <strong>WID.world</strong> raisonne par <em>adulte</em> sur le patrimoine <em>net</em>{" "}
          (actifs moins dettes), et corrige le sommet de la distribution en combinant données
          fiscales et comptabilité nationale. <strong>L'INSEE</strong> raisonne par <em>ménage</em>{" "}
          sur le patrimoine <em>brut</em>, à partir d'enquêtes qui décrivent bien l'ensemble des
          ménages mais sous-estiment les plus fortunés. <strong>La DGFiP</strong> donne une vue
          administrative par <em>foyer fiscal</em>, issue de l'ISF puis de l'IFI.
        </p>
        <p>
          Ces unités, par adulte, par ménage, par foyer fiscal, ne sont pas interchangeables : un «
          top 1 % » d'adultes n'est pas un « top 1 % » de ménages. On peut superposer les courbes
          pour comparer leur <em>allure</em>, jamais les fusionner en une seule série ni lire leurs
          niveaux comme une même grandeur. C'est la règle qui structure tout le site : chaque courbe
          affiche sa Convention.
        </p>
      </Section>

      <Section title="La rupture ISF → IFI de 2018">
        <p>
          Jusqu'en 2017, l'impôt de solidarité sur la fortune (ISF) portait sur l'ensemble du
          patrimoine. Depuis 2018, l'impôt sur la fortune immobilière (IFI) ne porte plus que sur
          l'immobilier. Les séries DGFiP avant et après 2018 ne mesurent donc pas la même chose.
        </p>
        <p>
          Cette rupture n'est pas lissée : elle est signalée par un repère ambre sur les graphiques,
          et encodée dans la donnée par le <code>concept_patrimoine</code> (« total » jusqu'en 2017,
          « immobilier » à partir de 2018). C'est une discontinuité méthodologique, pas une alerte.
        </p>
      </Section>

      <Section title="Limites des enquêtes">
        <p>
          Les enquêtes par sondage atteignent mal le tout-haut de la distribution : les très grands
          patrimoines sont rares et difficiles à interroger, ce qui tend à sous-estimer la
          concentration. C'est pourquoi WID.world recourt aux données fiscales pour corriger le
          sommet, et pourquoi la vue administrative de la DGFiP, bien que partielle, reste
          précieuse. Aucune source ne suffit seule : c'est leur lecture croisée, à Convention
          explicite, qui donne une image défendable.
        </p>
      </Section>

      <Section title="Millésimes et révisions">
        <p>
          Les sources recalculent parfois le passé : une même observation (même année, même source,
          même Convention) peut exister dans plusieurs <em>millésimes</em>, avec des valeurs
          différentes. On ne remplace jamais l'ancienne valeur par la nouvelle : les deux millésimes
          coexistent, chacun avec sa date d'extraction. Le tableau ci-dessous liste les révisions
          détectées dans le jeu de données courant.
        </p>
        {revisionsQ.isPending ? (
          <FigureSkeleton height={120} />
        ) : revisionsQ.isError ? (
          <ErrorState onRetry={() => revisionsQ.refetch()} height={120} />
        ) : (
          <RevisionsTable revisions={revisionsQ.data ?? []} meta={metaQ.data} />
        )}
      </Section>

      <Section title="Licences et attributions">
        <p>
          Réutilisez ces données en citant leur source. Les conditions ci-dessous proviennent
          directement de l'API, pour rester synchronisées avec le jeu de données.
        </p>
        {sourcesQ.isPending ? (
          <FigureSkeleton height={160} />
        ) : sourcesQ.isError ? (
          <ErrorState onRetry={() => sourcesQ.refetch()} height={160} />
        ) : (
          <dl className="divide-y divide-border rounded-lg border border-border">
            {(sourcesQ.data ?? []).map((s) => (
              <div key={s.source} className="grid gap-1 px-4 py-3.5 sm:grid-cols-[10rem_1fr]">
                <dt className="font-serif text-title font-semibold text-foreground">
                  {s.source}
                  <span className="mt-0.5 block font-sans text-label font-normal text-muted-foreground">
                    {s.convention}
                  </span>
                </dt>
                <dd className="space-y-1 text-sm text-foreground/90">
                  <p>
                    <span className="text-muted-foreground">Attribution :</span> {s.attribution}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Licence :</span> {s.licence}
                  </p>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded-sm text-accent-strong underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  >
                    {s.url.replace(/^https?:\/\//, "")}
                    <ExternalLink className="size-3.5" aria-hidden />
                  </a>
                </dd>
              </div>
            ))}
          </dl>
        )}
      </Section>
    </div>
  );
}
