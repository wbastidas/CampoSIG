/**
 * Reading the catalogues (RF-034).
 *
 * The screen has to make three distinctions that look alike and are not:
 *
 * 1. **Empty because it is waiting for a list** (the political division, the ERP's materials) versus
 *    empty because somebody retired everything. The first is normal and has a reason; the second is
 *    a problem. So an empty catalogue is only ever shown with its `note`, and one with no note is
 *    reported as a fault.
 * 2. **Owned by the platform** versus **owned by an integration**. The second must not offer an
 *    edit button: a value typed over one the ERP overwrites tonight disappears without explanation.
 * 3. **National** versus **this unit's**. A local value overrides rather than duplicates, and the
 *    picker shows which is which — otherwise a supervisor comparing two units cannot tell whether a
 *    difference is a local decision or a data error.
 */

import type { CatalogEntryView, CatalogIndex, CatalogSummary, ResolvedCatalog } from '../../api/catalogs';

export const SOURCE_LABEL: Record<string, string> = {
  manual: 'La mantiene la administración funcional',
  integracion: 'La mantiene una integración (el ERP)',
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

/** Whether this catalogue may be edited from the web at all. */
export function isEditable(catalog: CatalogSummary | ResolvedCatalog): boolean {
  return catalog.source !== 'integracion';
}

export type Health = 'ok' | 'esperando' | 'vacio-sin-motivo';

/**
 * How healthy a catalogue is.
 *
 * `esperando` is not a fault: a catalogue with no values and a stated reason is a decision — the
 * political division stays empty until the official INEC list is loaded, because inventing it
 * partially would be worse. `vacio-sin-motivo` **is** a fault: an empty picker with no explanation.
 */
export function healthOf(catalog: CatalogSummary): Health {
  if (!catalog.empty) return 'ok';
  return catalog.note ? 'esperando' : 'vacio-sin-motivo';
}

export const HEALTH_LABEL: Record<Health, string> = {
  ok: 'Con valores',
  esperando: 'Vacío, a la espera',
  'vacio-sin-motivo': 'Vacío sin motivo declarado',
};

const HEALTH_RANK: Record<Health, number> = { 'vacio-sin-motivo': 0, esperando: 1, ok: 2 };

/** Worst first, then by code, so the list reads the same way every time. */
export function indexRows(index: CatalogIndex | null): (CatalogSummary & { health: Health })[] {
  if (!index) return [];
  return index.catalogs
    .map((catalog) => ({ ...catalog, health: healthOf(catalog) }))
    .sort((a, b) => {
      const byHealth = HEALTH_RANK[a.health] - HEALTH_RANK[b.health];
      return byHealth !== 0 ? byHealth : a.code.localeCompare(b.code);
    });
}

/** The headline. Only says «listo» when nothing is empty without a reason. */
export function indexHeadline(index: CatalogIndex | null): string {
  if (!index) return 'Cargando…';
  const rows = index.catalogs;
  if (rows.length === 0) return 'No hay ningún catálogo cargado.';
  const faults = rows.filter((row) => healthOf(row) === 'vacio-sin-motivo').length;
  const waiting = rows.filter((row) => healthOf(row) === 'esperando').length;
  const values = rows.reduce((total, row) => total + row.active_entries, 0);
  if (faults === 0 && waiting === 0) {
    return `${rows.length} catálogo(s) con ${values} valor(es) activos.`;
  }
  const parts: string[] = [];
  if (faults > 0) parts.push(`${faults} vacío(s) sin motivo`);
  if (waiting > 0) parts.push(`${waiting} a la espera de su lista`);
  return `${rows.length} catálogo(s) con ${values} valor(es) activos; ${parts.join(' y ')}.`;
}

/** What the GIS serves instead, so a reader does not go looking for `feeder` here. */
export function gisNote(index: CatalogIndex | null): string | null {
  if (!index || index.gis_backed.length === 0) return null;
  return `${index.gis_backed.join(', ')} no están aquí: llegan del SIG de la unidad en cada sincronización y difieren por unidad.`;
}

export interface EntryRow {
  code: string;
  label: string;
  synonyms: string;
  origin: string;
  extras: string;
}

/** The entries of a resolved catalogue, in the order the server returned them. */
export function entryRows(catalog: ResolvedCatalog | null): EntryRow[] {
  if (!catalog) return [];
  return catalog.entries.map((entry: CatalogEntryView) => ({
    code: entry.code,
    label: entry.label,
    synonyms: entry.synonyms.length > 0 ? entry.synonyms.join(', ') : '—',
    origin: entry.local ? 'De la unidad' : 'Nacional',
    extras: describeAttributes(entry.attributes),
  }));
}

/**
 * The extra attributes as a readable line.
 *
 * `suggested_criticality` is spelled out as a suggestion on purpose: the form asks for the
 * criticality and the person confirms it, so a reader must not take this for the value.
 */
export function describeAttributes(attributes: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(attributes)) {
    const shown =
      typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
        ? String(value)
        : JSON.stringify(value);
    if (key === 'suggested_criticality') {
      parts.push(`criticidad sugerida: ${shown}`);
    } else {
      parts.push(`${key}: ${shown}`);
    }
  }
  return parts.length > 0 ? parts.join(' · ') : '—';
}

/** What an empty catalogue tells the reader. Never an empty table with no explanation. */
export function emptyAdvice(catalog: ResolvedCatalog | null): string | null {
  if (!catalog || !catalog.empty) return null;
  if (catalog.note) return catalog.note;
  return (
    'Este catálogo no tiene ningún valor activo y no declara por qué. Un selector vacío en el ' +
    'formulario obliga al técnico a escribir en observaciones, que es donde el dato se pierde.'
  );
}
