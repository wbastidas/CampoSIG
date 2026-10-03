/**
 * Reading and editing the capture policy (RF-151).
 *
 * The screen's whole job is to make two things impossible to get wrong.
 *
 * 1. **Saying nothing must not mean saying null.** The form shows fifteen fields; a save must carry
 *    only the ones the person touched. So the editing state records what changed, not what is
 *    displayed, and `changesOf` is what goes over the wire.
 * 2. **An inherited value must not look like a decision.** A field showing «1 foto» that came from
 *    the platform default reads exactly like one an administrator chose, and that is how somebody
 *    concludes the sync is broken when a zone quietly overrides their unit-level change. So every
 *    row says where its value came from, in the server's own words.
 */

import type { EffectivePolicy, PolicyList, PolicyValues } from '../../api/policy';

/** The label and the unit of each field, in es-EC. The order is the order the screen shows. */
export const FIELD_LABELS: { field: string; label: string; help: string }[] = [
  {
    field: 'store_audio',
    label: 'Guardar el audio original',
    help: 'Si no, solo se conserva la transcripción. El servidor lo rechaza, no solo el teléfono.',
  },
  {
    field: 'require_audio_consent',
    label: 'Pedir consentimiento antes de grabar',
    help: 'Grabar la voz de una persona es un dato personal (LOPDP).',
  },
  { field: 'audio_retention_days', label: 'Retención del audio (días)', help: '' },
  {
    field: 'min_photos',
    label: 'Fotos mínimas por OT',
    help: 'Un piso: el formulario puede pedir más, nunca menos.',
  },
  { field: 'photo_max_edge_px', label: 'Lado mayor de la foto (px)', help: '' },
  { field: 'photo_quality', label: 'Calidad JPEG (1 a 100)', help: '' },
  { field: 'evidence_retention_days', label: 'Retención de evidencias (días)', help: '' },
  {
    field: 'upload_on_metered',
    label: 'Subir por datos móviles',
    help: 'Si no, la evidencia espera una red Wi-Fi.',
  },
  {
    field: 'metered_upload_limit_mb',
    label: 'Tope diario por datos móviles (MB)',
    help: 'Vacío: sin tope.',
  },
  {
    field: 'downscale_on_metered',
    label: 'Reducir la foto fuera de Wi-Fi',
    help: '',
  },
  {
    field: 'require_position_consent',
    label: 'Pedir consentimiento para reportar la posición',
    help:
      'La ubicación de una persona es un dato personal (LOPDP). Retirarlo borra la última posición.',
  },
  {
    field: 'position_report_minutes',
    label: 'Reportar la posición cada (minutos)',
    help: 'De 1 a 240, solo dentro de la jornada.',
  },
  {
    field: 'workday_start',
    label: 'Inicio de la jornada (HH:MM)',
    help: 'Hora de Ecuador. Fuera de la jornada no se reporta ni se guarda la posición.',
  },
  {
    field: 'workday_end',
    label: 'Fin de la jornada (HH:MM)',
    help: 'Antes del inicio: turno nocturno que cruza la medianoche. 24:00 cierra el día.',
  },
  {
    field: 'workdays',
    label: 'Días laborables',
    help: 'Del 1 (lunes) al 7 (domingo), separados por comas: 1,2,3,4,5.',
  },
];

/** Which fields are booleans, so the screen renders a checkbox and not a number. */
export const BOOLEAN_FIELDS = [
  'store_audio',
  'require_audio_consent',
  'upload_on_metered',
  'downscale_on_metered',
  'require_position_consent',
];

/** Which fields are text (a clock time, a list of days), so the screen does not turn them into a
 *  number. */
export const TEXT_FIELDS = ['workday_start', 'workday_end', 'workdays'];

export function isText(field: string): boolean {
  return TEXT_FIELDS.includes(field);
}

export function isBoolean(field: string): boolean {
  return BOOLEAN_FIELDS.includes(field);
}

export function labelOf(field: string): string {
  return FIELD_LABELS.find((entry) => entry.field === field)?.label ?? field;
}

/** The row for a scope, or null when that scope has no row of its own. */
export function rowFor(list: PolicyList | null, zone: string | null): PolicyValues | null {
  if (!list) return null;
  const found = list.rows.find((row) => (row.zone_code ?? null) === zone);
  return found ? found.values : null;
}

/** The zones that have a policy row of their own, in the order the server sent them. */
export function configuredZones(list: PolicyList | null): string[] {
  if (!list) return [];
  return list.rows
    .map((row) => row.zone_code)
    .filter((code): code is string => code !== null);
}

export interface EffectiveRow {
  field: string;
  label: string;
  value: string | number | boolean | null;
  source: string;
  /** True when nobody decided this: the platform default is standing in. */
  inherited: boolean;
}

/** The effective view, one row per field, in the screen's order. */
export function effectiveRows(policy: EffectivePolicy | null): EffectiveRow[] {
  if (!policy) return [];
  return FIELD_LABELS.map((entry) => {
    const found = policy.values[entry.field];
    return {
      field: entry.field,
      label: entry.label,
      value: found?.value ?? null,
      source: found?.source ?? '—',
      inherited: (found?.source ?? '').startsWith('por omisión'),
    };
  });
}

/** How a value reads. A boolean is «Sí»/«No» and an unset number says so rather than showing 0. */
export function displayValue(value: string | number | boolean | null): string {
  if (value === null) return 'sin definir';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value === 'number') return value.toLocaleString('es-EC').replace(/,/g, '.');
  return value;
}

/**
 * What a save should send: only the fields whose value differs from what was loaded.
 *
 * `null` in `edited` is a real value — it clears the field — so the comparison is against the
 * loaded row and never against truthiness. A field the person did not touch is simply absent.
 */
export function changesOf(loaded: PolicyValues | null, edited: PolicyValues): PolicyValues {
  const changes: PolicyValues = {};
  for (const [field, value] of Object.entries(edited)) {
    const before = loaded ? (loaded[field] ?? null) : null;
    if (value !== before) changes[field] = value;
  }
  return changes;
}

/** Whether there is anything to save. A disabled button says «nothing changed» without a dialog. */
export function hasChanges(loaded: PolicyValues | null, edited: PolicyValues): boolean {
  return Object.keys(changesOf(loaded, edited)).length > 0;
}

/**
 * Local validation, in the same terms the server uses.
 *
 * Duplicated deliberately and kept narrow: the server is the authority — an old browser must not be
 * able to store a retention of zero days — and this only saves the round trip while somebody types.
 */
export function problemsIn(values: PolicyValues): string[] {
  const problems: string[] = [];
  const positive = [
    'audio_retention_days',
    'photo_max_edge_px',
    'evidence_retention_days',
    'metered_upload_limit_mb',
  ];
  for (const field of positive) {
    const value = values[field];
    if (typeof value === 'number' && value <= 0) {
      problems.push(`«${labelOf(field)}» debe ser mayor que cero.`);
    }
  }
  const quality = values.photo_quality;
  if (typeof quality === 'number' && (quality < 1 || quality > 100)) {
    problems.push('«Calidad JPEG (1 a 100)» va de 1 a 100.');
  }
  const photos = values.min_photos;
  if (typeof photos === 'number' && photos < 0) {
    problems.push('«Fotos mínimas por OT» no puede ser negativo.');
  }
  const minutes = values.position_report_minutes;
  if (typeof minutes === 'number' && (minutes < 1 || minutes > 240)) {
    problems.push('«Reportar la posición cada (minutos)» va de 1 a 240.');
  }
  for (const field of ['workday_start', 'workday_end']) {
    const value = values[field];
    const clock = /^([01]\d|2[0-3]):[0-5]\d$/;
    const valid =
      typeof value !== 'string' ||
      clock.test(value) ||
      (field === 'workday_end' && value === '24:00');
    if (!valid) problems.push(`«${labelOf(field)}» es una hora HH:MM, por ejemplo 07:30.`);
  }
  const days = values.workdays;
  if (typeof days === 'string') {
    const parts = days.split(',').map((part) => part.trim()).filter((part) => part !== '');
    if (parts.length === 0 || parts.some((part) => !/^[1-7]$/.test(part))) {
      problems.push(
        '«Días laborables» son números del 1 (lunes) al 7 (domingo), separados por comas.',
      );
    }
  }
  return problems;
}

/** What the scope selector says about where a save will land. */
export function scopeHeadline(zone: string | null): string {
  if (zone === null) return 'Está editando la política de toda la unidad.';
  return `Está editando solo la zona ${zone}; lo que no declare aquí lo hereda de la unidad.`;
}
