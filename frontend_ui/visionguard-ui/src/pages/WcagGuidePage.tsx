import { useState } from "react";
import { getContrastRatioFromHex, wcagLevel, wcagRequiredRatio } from "@/lib/wcag";
import { Badge } from "@/components/ui/Badge";

// ─── Contrast ratio calculator ────────────────────────────────────────────────
function ContrastCalculator() {
  const [fg, setFg] = useState("#334155");
  const [bg, setBg] = useState("#ffffff");
  const [large, setLarge] = useState(false);

  const ratio = getContrastRatioFromHex(fg, bg);
  const level = ratio !== null ? wcagLevel(ratio, large) : null;
  const required = wcagRequiredRatio(large);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            Text color
          </label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={fg}
              onChange={(e) => setFg(e.target.value)}
              className="w-8 h-8 rounded border border-border cursor-pointer"
              aria-label="Text foreground color"
            />
            <span className="text-sm font-mono text-text-primary">{fg}</span>
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            Background color
          </label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={bg}
              onChange={(e) => setBg(e.target.value)}
              className="w-8 h-8 rounded border border-border cursor-pointer"
              aria-label="Background color"
            />
            <span className="text-sm font-mono text-text-primary">{bg}</span>
          </div>
        </div>
      </div>

      {/* Large text toggle */}
      <label className="flex items-center gap-2 cursor-pointer w-fit">
        <input
          type="checkbox"
          checked={large}
          onChange={(e) => setLarge(e.target.checked)}
          className="accent-accent"
        />
        <span className="text-sm text-text-secondary">Large text (≥18px or ≥14px bold)</span>
      </label>

      {/* Preview */}
      <div
        className="rounded-lg p-5 border border-border"
        style={{ backgroundColor: bg }}
      >
        <p style={{ color: fg, fontSize: large ? "1.25rem" : "1rem" }} className="font-medium">
          Sample text preview
        </p>
        <p style={{ color: fg, fontSize: "0.875rem", opacity: 0.8 }}>
          The quick brown fox jumps over the lazy dog.
        </p>
      </div>

      {/* Result */}
      {ratio !== null && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-bg-subtle border border-border rounded-lg p-3 text-center">
            <p className="text-xl font-semibold text-text-primary tabular-nums">{ratio}:1</p>
            <p className="text-2xs text-text-tertiary mt-0.5">Actual ratio</p>
          </div>
          <div className="bg-bg-subtle border border-border rounded-lg p-3 text-center">
            <p className="text-xl font-semibold text-text-primary tabular-nums">{required}:1</p>
            <p className="text-2xs text-text-tertiary mt-0.5">Required (AA)</p>
          </div>
          <div className="bg-bg-subtle border border-border rounded-lg p-3 text-center flex flex-col items-center justify-center gap-1">
            {level === "AAA" && <Badge variant="success">AAA Pass</Badge>}
            {level === "AA"  && <Badge variant="accent">AA Pass</Badge>}
            {level === "FAIL" && <Badge variant="danger">Fail</Badge>}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Reference table ──────────────────────────────────────────────────────────
function ReferenceTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | React.ReactNode)[][];
}) {
  return (
    <div className="overflow-auto rounded-lg border border-border">
      <table className="w-full text-sm border-collapse">
        <thead className="bg-bg-subtle">
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="text-left text-xs font-semibold text-text-tertiary uppercase tracking-wide px-4 py-2.5 border-b border-border whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-bg-surface divide-y divide-border">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-bg-subtle transition-colors duration-100">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-sm text-text-secondary">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function WcagGuidePage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      {/* ── Intro ── */}
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-1">WCAG 2.1 Reference</h2>
        <p className="text-sm text-text-secondary">
          Web Content Accessibility Guidelines 2.1 — the international standard VisionGuard AI
          uses to evaluate every audited page.
        </p>
      </section>

      {/* ── Contrast requirements ── */}
      <section className="space-y-3" aria-labelledby="contrast-heading">
        <h3 id="contrast-heading" className="text-sm font-semibold text-text-primary">
          Contrast ratio requirements
        </h3>
        <ReferenceTable
          headers={["Text type", "WCAG AA (min)", "WCAG AAA"]}
          rows={[
            ["Normal text (< 18px / < 14px bold)", <strong>4.5:1</strong>, "7:1"],
            ["Large text (≥ 18px / ≥ 14px bold)", <strong>3.0:1</strong>, "4.5:1"],
            ["UI components & graphical objects",  <strong>3.0:1</strong>, "—"],
          ]}
        />
      </section>

      {/* ── POUR principles ── */}
      <section className="space-y-3" aria-labelledby="pour-heading">
        <h3 id="pour-heading" className="text-sm font-semibold text-text-primary">
          The four POUR principles
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            {
              letter: "P",
              title: "Perceivable",
              body: "Information and UI must be presentable to users in ways they can perceive — e.g., sufficient contrast, text alternatives for images, captions for video.",
            },
            {
              letter: "O",
              title: "Operable",
              body: "UI components and navigation must be operable — keyboard accessible, no seizure-inducing flashing, adequate time limits.",
            },
            {
              letter: "U",
              title: "Understandable",
              body: "Content and UI must be understandable — readable language, predictable navigation, input assistance and error identification.",
            },
            {
              letter: "R",
              title: "Robust",
              body: "Content must be robust enough for reliable interpretation by assistive technologies including screen readers.",
            },
          ].map(({ letter, title, body }) => (
            <div
              key={letter}
              className="bg-bg-surface border border-border rounded-lg p-4 space-y-1.5"
            >
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-accent-subtle text-accent text-xs font-bold rounded flex items-center justify-center shrink-0">
                  {letter}
                </span>
                <p className="text-sm font-semibold text-text-primary">{title}</p>
              </div>
              <p className="text-sm text-text-secondary leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Relative luminance formula ── */}
      <section className="space-y-3" aria-labelledby="formula-heading">
        <h3 id="formula-heading" className="text-sm font-semibold text-text-primary">
          Relative luminance formula
        </h3>
        <div className="bg-bg-subtle border border-border rounded-lg p-4">
          <pre className="text-xs font-mono text-text-primary leading-relaxed overflow-x-auto whitespace-pre">
{`L = 0.2126·R + 0.7152·G + 0.0722·B

Each channel is linearised:
  c ≤ 0.04045  →  c / 12.92
  c  > 0.04045  →  ((c + 0.055) / 1.055) ^ 2.4

Contrast Ratio = (L_lighter + 0.05) / (L_darker + 0.05)`}
          </pre>
        </div>
      </section>

      {/* ── Interactive calculator ── */}
      <section className="space-y-3" aria-labelledby="calc-heading">
        <h3 id="calc-heading" className="text-sm font-semibold text-text-primary">
          Live contrast calculator
        </h3>
        <div className="bg-bg-surface border border-border rounded-lg p-5">
          <ContrastCalculator />
        </div>
      </section>
    </div>
  );
}
