/**
 * Reading and checking zones before they reach the server (RF-152).
 *
 * The pure half of the screen. Two jobs:
 *
 * 1. **Refuse locally what the server would refuse anyway.** A paste that is not GeoJSON, or a
 *    collection with no features, comes back from the server as a 422 — but telling the operator
 *    *here* costs nothing and saves them a round trip while they are fixing a file.
 * 2. **Say what the numbers mean.** «94 % de cobertura» is not actionable; «11 OT abiertas no caen
 *    en ninguna zona» is. So the coverage reads as counts first and the share second, and the two
 *    things that are not a zone problem — the orders with no coordinates — are stated apart.
 *
 * What is deliberately *not* here: any attempt to repair a geometry. The server refuses an invalid
 * ring rather than redrawing it, and a browser that quietly cleaned one up first would defeat that.
 */

import type {
  BackfillReport,
  CoverageReport,
  ImportReport,
  ZoneCollection,
  ZoneFeature,
} from '../../api/zones';

/** A share as a percentage, es-EC: comma decimal. */
export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits).replace('.', ',')} %`;
}

/** A quantity with a point for thousands, the way Ecuador writes it. */
export function integer(value: number): string {
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

export interface ParsedDocument {
  /** The parsed document, ready to send. Null when it could not be used.
   *
   * Typed `object` and not `unknown` so that `parsed.document && …` is a boolean test in JSX; a
   * `unknown` on the left of `&&` renders as `unknown`, which TypeScript rejects and React would
   * have rendered as nothing. */
  document: object | null;
  /** How many features it carries, for the confirmation before importing. */
  features: number;
  /** Why it cannot be used, in Spanish, or null. */
  problem: string | null;
}

/**
 * Parse pasted or uploaded text as a GeoJSON document of zones.
 *
 * Accepts a `FeatureCollection` or a single `Feature`, which is what the server accepts, because a
 * desktop GIS exporting one selected polygon produces the second and an operator will paste it.
 */
export function parseDocument(text: string): ParsedDocument {
  const trimmed = text.trim();
  if (!trimmed) return { document: null, features: 0, problem: 'No hay nada que importar.' };
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return { document: null, features: 0, problem: 'El texto no es JSON válido.' };
  }
  if (typeof parsed !== 'object' || parsed === null) {
    return { document: null, features: 0, problem: 'El JSON no es un objeto GeoJSON.' };
  }
  const shape = parsed as { type?: unknown; features?: unknown };
  if (shape.type === 'Feature') return { document: parsed, features: 1, problem: null };
  if (shape.type !== 'FeatureCollection') {
    const seen = typeof shape.type === 'string' ? shape.type : 'sin type';
    return {
      document: null,
      features: 0,
      problem: `Se esperaba un FeatureCollection o un Feature de GeoJSON; llegó «${seen}».`,
    };
  }
  if (!Array.isArray(shape.features) || shape.features.length === 0) {
    return { document: null, features: 0, problem: 'El FeatureCollection no trae ningún rasgo.' };
  }
  return { document: parsed, features: shape.features.length, problem: null };
}

/**
 * The codes a document carries, so the operator sees what is about to be created or replaced
 * *before* importing. The same generic property names the server looks at, in the same order.
 */
export const CODE_PROPERTIES = ['code', 'codigo', 'zone', 'zona', 'id'];

export function codesIn(document: unknown, codeProperty?: string): (string | null)[] {
  const shape = document as { type?: unknown; features?: unknown };
  const features: unknown[] =
    shape.type === 'Feature' ? [document] : Array.isArray(shape.features) ? shape.features : [];
  const wanted = codeProperty ? [codeProperty.toLowerCase()] : CODE_PROPERTIES;
  return features.map((feature) => {
    const properties = (feature as { properties?: unknown }).properties;
    if (typeof properties !== 'object' || properties === null) return null;
    for (const name of wanted) {
      for (const [key, value] of Object.entries(properties as Record<string, unknown>)) {
        // Only a scalar is a code. A nested object would stringify to «[object Object]» and the
        // preview would show the operator a code the server is never going to see.
        if (key.toLowerCase() !== name) continue;
        if (typeof value === 'string' && value !== '') return value;
        if (typeof value === 'number' || typeof value === 'boolean') return String(value);
      }
    }
    return null;
  });
}

/** How the coverage reads: counts first, because a count is what a planner can act on. */
export function coverageHeadline(report: CoverageReport): string {
  const { coverage } = report;
  if (coverage.open_orders === 0) return 'No hay trabajo abierto que ubicar.';
  if (coverage.outside === 0 && coverage.ambiguous === 0) {
    return `Las ${integer(coverage.open_orders)} OT abiertas que tienen punto caen en una zona.`;
  }
  const parts: string[] = [];
  if (coverage.outside > 0) {
    parts.push(`${integer(coverage.outside)} no cae(n) en ninguna zona`);
  }
  if (coverage.ambiguous > 0) {
    parts.push(`${integer(coverage.ambiguous)} cae(n) en más de una`);
  }
  return `De ${integer(coverage.open_orders)} OT abiertas, ${parts.join(' y ')}.`;
}

/**
 * What the headline does not say.
 *
 * The orders without coordinates are listed here and not counted against the zones: a unit that
 * has not started capturing points would otherwise read as broken zones, which is true of the
 * points and false of the zones.
 */
export function coverageCaveats(report: CoverageReport): string[] {
  const { coverage } = report;
  const lines: string[] = [];
  if (coverage.without_location > 0) {
    lines.push(
      `${integer(coverage.without_location)} OT abierta(s) no tienen punto, así que ninguna zona ` +
        'puede ubicarlas. No cuentan contra la cobertura.',
    );
  }
  if (coverage.covered_share === null) {
    lines.push(
      'No hay ninguna OT abierta con coordenadas, así que no se puede calcular el porcentaje de ' +
        'cobertura.',
    );
  } else {
    lines.push(`Cobertura de las que sí tienen punto: ${percent(coverage.covered_share, 1)}.`);
  }
  if (coverage.ambiguous > 0) {
    lines.push(
      'Una OT que cae en dos zonas no tiene respuesta: hay que corregir el solapamiento antes ' +
        'de asignar por zona.',
    );
  }
  return lines;
}

/** The overlaps, in the server's own words. Empty is the expected state and says so. */
export function overlapLines(report: CoverageReport): string[] {
  if (report.overlaps.length === 0) return [];
  return report.overlaps.map((item) => item.text);
}

export interface ZoneRow {
  code: string;
  name: string;
  origin: string;
  active: boolean;
  updatedBy: string;
  updatedAt: string;
}

/** The table, active first and then by code, which is how an administrator looks for one. */
export function zoneRows(collection: ZoneCollection | null): ZoneRow[] {
  if (!collection) return [];
  const rows = collection.features.map((feature: ZoneFeature) => ({
    code: feature.properties.code,
    name: feature.properties.name,
    origin: feature.properties.origin,
    active: feature.properties.active,
    updatedBy: feature.properties.updated_by ?? '—',
    updatedAt: feature.properties.updated_at ?? '—',
  }));
  return rows.sort((a, b) => {
    if (a.active !== b.active) return a.active ? -1 : 1;
    return a.code.localeCompare(b.code);
  });
}

/** What an import did, in one line. Both halves, always: accepted and refused. */
export function importHeadline(report: ImportReport): string {
  const parts: string[] = [];
  if (report.created.length > 0) parts.push(`${report.created.length} creada(s)`);
  if (report.updated.length > 0) parts.push(`${report.updated.length} reemplazada(s)`);
  if (parts.length === 0) parts.push('ninguna aceptada');
  const tail =
    report.rejected.length > 0 ? `; ${report.rejected.length} rechazada(s)` : '; sin rechazos';
  return `${parts.join(' y ')}${tail}.`;
}

/**
 * Whether an import is worth calling a failure.
 *
 * A file where nothing was accepted is: the operator has to fix something. A file where
 * thirty-nine of forty went in is not — it is progress with a list of what to fix.
 */
export function importFailed(report: ImportReport): boolean {
  return report.accepted === 0;
}

/** What the backfill did, with the two groups it refused to guess at kept apart. */
export function backfillLines(report: BackfillReport): string[] {
  const filled = Object.keys(report.filled).length;
  const ambiguous = Object.keys(report.ambiguous).length;
  const lines: string[] = [];
  const verb = report.dry_run ? 'se llenaría(n)' : 'se llenó/llenaron';
  lines.push(`${integer(filled)} OT: ${verb} la zona desde el polígono.`);
  if (ambiguous > 0) {
    lines.push(
      `${integer(ambiguous)} OT caen en más de una zona y quedan sin tocar: elegir una por ` +
        'la plataforma sería una decisión que nadie podría revisar.',
    );
  }
  if (report.outside.length > 0) {
    lines.push(`${integer(report.outside.length)} OT no caen en ninguna zona.`);
  }
  if (report.dry_run) {
    lines.push('Es una simulación: todavía no se escribió nada.');
  }
  return lines;
}
