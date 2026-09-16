// WCAG 2.1 relative luminance and contrast ratio utilities
// Implements: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance

function linearize(c: number): number {
  const sRGB = c / 255;
  return sRGB <= 0.04045 ? sRGB / 12.92 : ((sRGB + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(r: number, g: number, b: number): number {
  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

export function contrastRatio(l1: number, l2: number): number {
  const [lighter, darker] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (lighter + 0.05) / (darker + 0.05);
}

export function parseRgb(
  rgb: string
): { r: number; g: number; b: number } | null {
  const m = rgb.match(/rgb\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)/);
  if (!m) return null;
  return { r: parseInt(m[1]), g: parseInt(m[2]), b: parseInt(m[3]) };
}

export function parseHex(hex: string): { r: number; g: number; b: number } | null {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return null;
  return {
    r: parseInt(clean.slice(0, 2), 16),
    g: parseInt(clean.slice(2, 4), 16),
    b: parseInt(clean.slice(4, 6), 16),
  };
}

export function getContrastRatioFromRgb(
  color: string,
  background: string
): number | null {
  const fg = parseRgb(color);
  const bg = parseRgb(background);
  if (!fg || !bg) return null;
  const l1 = relativeLuminance(fg.r, fg.g, fg.b);
  const l2 = relativeLuminance(bg.r, bg.g, bg.b);
  return Math.round(contrastRatio(l1, l2) * 100) / 100;
}

export function getContrastRatioFromHex(
  hex1: string,
  hex2: string
): number | null {
  const c1 = parseHex(hex1);
  const c2 = parseHex(hex2);
  if (!c1 || !c2) return null;
  const l1 = relativeLuminance(c1.r, c1.g, c1.b);
  const l2 = relativeLuminance(c2.r, c2.g, c2.b);
  return Math.round(contrastRatio(l1, l2) * 100) / 100;
}

export function isLargeText(fontSize: string, fontWeight: string): boolean {
  const px = parseFloat(fontSize);
  const weight = parseInt(fontWeight, 10);
  if (isNaN(px)) return false;
  // >= 18pt (24px) normal, or >= 14pt (18.67px) bold
  return px >= 24 || (weight >= 700 && px >= 18.67);
}

export function wcagRequiredRatio(large: boolean): number {
  return large ? 3.0 : 4.5;
}

export function wcagPassesAA(ratio: number, large: boolean): boolean {
  return ratio >= wcagRequiredRatio(large);
}

export function wcagPassesAAA(ratio: number, large: boolean): boolean {
  return ratio >= (large ? 4.5 : 7.0);
}

export type WcagLevel = "AAA" | "AA" | "FAIL";

export function wcagLevel(ratio: number, large: boolean): WcagLevel {
  if (wcagPassesAAA(ratio, large)) return "AAA";
  if (wcagPassesAA(ratio, large)) return "AA";
  return "FAIL";
}
