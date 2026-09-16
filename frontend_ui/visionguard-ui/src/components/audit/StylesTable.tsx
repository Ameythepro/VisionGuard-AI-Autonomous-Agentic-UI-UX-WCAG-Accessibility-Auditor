import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import {
  getContrastRatioFromRgb,
  isLargeText,
  wcagLevel,
} from "@/lib/wcag";
import type { ComputedStyle } from "@/lib/api";
import { EmptyState } from "@/components/ui/States";
import { LayoutList } from "lucide-react";

interface StylesTableProps {
  styles: ComputedStyle[];
}

function ContrastCell({ el }: { el: ComputedStyle }) {
  const ratio = getContrastRatioFromRgb(el.color, el.backgroundColor);
  const large = isLargeText(el.fontSize, el.fontWeight);
  if (ratio === null) {
    return <span className="text-text-tertiary text-xs">—</span>;
  }
  const level = wcagLevel(ratio, large);
  const colorClass =
    level === "FAIL"
      ? "text-danger font-semibold"
      : level === "AAA"
      ? "text-success font-medium"
      : "text-accent font-medium";

  return (
    <div className="flex items-center gap-2">
      <span className={cn("text-sm tabular-nums", colorClass)}>{ratio}:1</span>
      {level === "FAIL" ? (
        <Badge variant="danger">Fail</Badge>
      ) : level === "AAA" ? (
        <Badge variant="success">AAA</Badge>
      ) : (
        <Badge variant="accent">AA</Badge>
      )}
    </div>
  );
}

export function StylesTable({ styles }: StylesTableProps) {
  if (!styles.length) {
    return (
      <EmptyState
        icon={<LayoutList />}
        title="No style data"
        description="Run an audit to extract computed styles from the target page."
      />
    );
  }

  const display = styles.slice(0, 150);

  return (
    <div>
      {styles.length > 150 && (
        <p className="text-xs text-text-tertiary mb-3">
          Showing 150 of {styles.length} elements
        </p>
      )}
      <div className="overflow-auto rounded-lg border border-border max-h-[520px]">
        <table className="w-full text-sm border-collapse min-w-[720px]">
          <thead className="bg-bg-subtle sticky top-0 z-10">
            <tr>
              {["Selector", "Tag", "Text", "Text color", "BG color", "Size", "Contrast"].map(
                (h) => (
                  <th
                    key={h}
                    className="text-left text-xs font-semibold text-text-tertiary uppercase tracking-wide px-3 py-2.5 border-b border-border whitespace-nowrap"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="bg-bg-surface divide-y divide-border">
            {display.map((el, i) => (
              <tr
                key={i}
                className="hover:bg-bg-subtle transition-colors duration-100"
              >
                <td className="px-3 py-2.5 max-w-[200px]">
                  <span className="text-xs font-mono text-accent block truncate" title={el.selector}>
                    {el.selector}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <Badge variant="default">{el.tag?.toUpperCase()}</Badge>
                </td>
                <td className="px-3 py-2.5 max-w-[180px]">
                  <span className="text-xs text-text-secondary block truncate" title={el.text ?? ""}>
                    {el.text?.trim() || "—"}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3.5 h-3.5 rounded-sm border border-border shrink-0"
                      style={{ backgroundColor: el.color }}
                      aria-hidden="true"
                    />
                    <span className="text-xs font-mono text-text-secondary whitespace-nowrap">
                      {el.color}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3.5 h-3.5 rounded-sm border border-border shrink-0"
                      style={{ backgroundColor: el.backgroundColor }}
                      aria-hidden="true"
                    />
                    <span className="text-xs font-mono text-text-secondary whitespace-nowrap">
                      {el.backgroundColor}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <span className="text-xs text-text-secondary">
                    {el.fontSize} / {el.fontWeight}w
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <ContrastCell el={el} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
