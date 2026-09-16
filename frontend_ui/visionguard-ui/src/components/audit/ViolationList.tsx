import { useState } from "react";
import { ChevronDown, Copy, Check } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import {
  getContrastRatioFromRgb,
  isLargeText,
  wcagLevel,
  wcagRequiredRatio,
  type WcagLevel,
} from "@/lib/wcag";
import type { ComputedStyle } from "@/lib/api";
import { EmptyState } from "@/components/ui/States";
import { ScanSearch } from "lucide-react";

interface ViolationListProps {
  styles: ComputedStyle[];
}

function levelBadge(level: WcagLevel) {
  if (level === "AAA") return <Badge variant="success">AAA</Badge>;
  if (level === "AA")  return <Badge variant="accent">AA</Badge>;
  return <Badge variant="danger">Fail</Badge>;
}

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="w-4 h-4 rounded-sm border border-border shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span className="text-xs text-text-secondary font-mono">{color}</span>
      <span className="text-xs text-text-tertiary">({label})</span>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button variant="ghost" size="icon" onClick={handleCopy} aria-label="Copy CSS">
      {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
    </Button>
  );
}

function ViolationItem({ el }: { el: ComputedStyle }) {
  const [open, setOpen] = useState(false);
  const ratio = getContrastRatioFromRgb(el.color, el.backgroundColor);
  const large = isLargeText(el.fontSize, el.fontWeight);
  if (ratio === null || wcagLevel(ratio, large) !== "FAIL") return null;

  const required = wcagRequiredRatio(large);
  const deficit = (required - ratio).toFixed(2);
  const textPreview = el.text?.trim().slice(0, 80) || "—";
  const cssFix = `${el.selector} {\n  color: #1a1a1a; /* ↑ contrast fix */\n  /* original: ${el.color} on ${el.backgroundColor} — ratio ${ratio}:1 */\n}`;

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "w-full flex items-start gap-3 px-4 py-3 text-left",
          "hover:bg-bg-subtle transition-colors duration-150",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
          open && "bg-bg-subtle"
        )}
        aria-expanded={open}
      >
        {/* Ratio badge */}
        <div className="shrink-0 mt-0.5 min-w-[52px]">
          <span className="text-base font-semibold text-danger tabular-nums">
            {ratio}:1
          </span>
          <p className="text-2xs text-text-tertiary">need {required}:1</p>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 space-y-0.5">
          <p className="text-sm text-text-primary font-mono truncate">{el.selector}</p>
          <p className="text-xs text-text-secondary truncate">{textPreview}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant="danger">Fail</Badge>
            {large && <Badge variant="muted">Large text</Badge>}
            <Badge variant="muted">{el.fontSize} / {el.fontWeight}w</Badge>
          </div>
        </div>

        <ChevronDown
          size={16}
          className={cn(
            "shrink-0 text-text-tertiary mt-0.5 transition-transform duration-150",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-border space-y-4 animate-fade-in">
          {/* Colors */}
          <div>
            <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-2">
              Colors
            </p>
            <div className="space-y-1.5">
              <ColorSwatch color={el.color} label="text" />
              <ColorSwatch color={el.backgroundColor} label="background" />
            </div>
          </div>

          {/* Contrast detail */}
          <div>
            <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-2">
              Contrast analysis
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-danger-subtle border border-danger-muted rounded p-2.5">
                <p className="text-lg font-semibold text-danger tabular-nums">{ratio}:1</p>
                <p className="text-2xs text-danger/70">Actual</p>
              </div>
              <div className="bg-bg-subtle border border-border rounded p-2.5">
                <p className="text-lg font-semibold text-text-primary tabular-nums">{required}:1</p>
                <p className="text-2xs text-text-tertiary">Required (AA)</p>
              </div>
              <div className="bg-warning-subtle border border-warning-muted rounded p-2.5">
                <p className="text-lg font-semibold text-warning tabular-nums">-{deficit}</p>
                <p className="text-2xs text-warning/70">Deficit</p>
              </div>
            </div>
          </div>

          {/* CSS fix */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide">
                Suggested fix
              </p>
              <CopyButton text={cssFix} />
            </div>
            <pre className="bg-bg-subtle border border-border rounded p-3 text-xs font-mono text-text-primary overflow-x-auto leading-relaxed whitespace-pre">
              {cssFix}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export function ViolationList({ styles }: ViolationListProps) {
  const violations = styles.filter((el) => {
    const ratio = getContrastRatioFromRgb(el.color, el.backgroundColor);
    const large = isLargeText(el.fontSize, el.fontWeight);
    return ratio !== null && wcagLevel(ratio, large) === "FAIL";
  });

  if (violations.length === 0) {
    return (
      <EmptyState
        icon={<ScanSearch />}
        title="No contrast violations found"
        description="All scanned elements meet WCAG 2.1 AA contrast requirements."
      />
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-text-tertiary mb-3">
        {violations.length} violation{violations.length !== 1 ? "s" : ""} detected
      </p>
      {violations.map((el, i) => (
        <ViolationItem key={`${el.selector}-${i}`} el={el} />
      ))}
    </div>
  );
}
