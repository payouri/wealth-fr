import Filters from "../components/Filters";

// STUB (jalon 4): top-share curves (top10/top1/top0.1) + Gini since 2000,
// source/convention toggle, 2018 rupture marker. First real curve: WID top 1%.
export default function Dashboard() {
  return (
    <div className="space-y-4">
      <Filters />
      <div className="flex h-[360px] items-center justify-center rounded border bg-white text-gray-400">
        Courbes des parts du sommet + Gini — TODO
      </div>
    </div>
  );
}
