// The curated Groupe selector (issue #15): a thin consumer of `groupeOptions`,
// which decides what to OFFER (canonical concentration fractions, the DGFiP
// families grouped by header, standalone groups on top) — never the raw machine
// codes or the ~290-bracket WID percentile lattice. Curation is presentation
// only; any underlying figure stays reachable by a hand-typed URL.
import type { Meta } from "@/api/types";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { groupeOptions } from "@/lib/domain";

interface GroupeSelectProps {
  meta: Meta;
  source: string;
  indicateur: string;
  value: string;
  onValueChange: (value: string) => void;
  /** Wires the trigger to its visible field label for screen readers. */
  labelledBy?: string;
  className?: string;
  disabled?: boolean;
}

export default function GroupeSelect({
  meta,
  source,
  indicateur,
  value,
  onValueChange,
  labelledBy,
  className,
  disabled,
}: GroupeSelectProps) {
  const groups = groupeOptions(meta, source, indicateur);
  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger className={className} aria-labelledby={labelledBy}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {groups.map((group) => (
          // Keyed by header when grouped, else by the block's first option value
          // (stable — the concentration block always starts at the same fraction,
          // the standalone block at the same group).
          <SelectGroup key={group.header ?? group.options[0]?.value}>
            {group.header && <SelectLabel>{group.header}</SelectLabel>}
            {group.options.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}
