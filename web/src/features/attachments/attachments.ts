/**
 * Reading a work order's office attachments (RF-017).
 *
 * The panel exists to make three things impossible to miss, because each is a way a list of
 * drawings looks healthy while the crew ends up without them:
 *
 * 1. **What the download weighs, against its ceiling.** A crew with a 300 MB set of drawings and a
 *    2G link has no drawings. The number and the limit are shown together, in megabytes with the
 *    coma decimal of es-EC, before anybody leaves the office.
 * 2. **What is not travelling.** An attachment marked as not-offline is on the screen and not on
 *    the phone, and the two look identical unless the screen says so.
 * 3. **Whose drawing it is.** A front sees its work's attachments (RF-015). Presenting them as the
 *    front's own would have somebody withdraw the work's plan to fix one front.
 */

import type { Attachment, AttachmentList } from '../../api/attachments';

export const KIND_LABEL: Record<string, string> = {
  plano: 'Plano',
  diseno: 'Diseño',
  documento: 'Documento',
  permiso: 'Permiso',
  referencia: 'Referencia',
};

/** Megabytes with one decimal and the coma decimal of es-EC (regla 11). */
export function megabytes(value: number): string {
  return (value / (1024 * 1024)).toFixed(1).replace('.', ',');
}

export function kindLabel(kind: string): string {
  return KIND_LABEL[kind] ?? kind;
}

export interface AttachmentRow {
  attachment: Attachment;
  /** True when the file belongs to the work and is shared with this front (RF-015). */
  fromWork: boolean;
  /** What the row says about travelling: it is what decides whether the crew has the file. */
  travel: 'viaja' | 'no_viaja' | 'retirado';
}

export function rows(list: AttachmentList | null): AttachmentRow[] {
  if (!list) return [];
  return list.attachments.map((attachment) => ({
    attachment,
    fromWork: attachment.work_order_id !== list.work_order_id,
    travel: !attachment.is_active ? 'retirado' : attachment.offline ? 'viaja' : 'no_viaja',
  }));
}

export const TRAVEL_LABEL: Record<AttachmentRow['travel'], string> = {
  viaja: 'Viaja en el paquete',
  no_viaja: 'No baja al teléfono',
  retirado: 'Retirado',
};

/** What the crew downloads for this order, said with its ceiling and never as a bare percentage. */
export function budgetHeadline(list: AttachmentList | null): string {
  if (!list) return 'Sin adjuntos';
  return `${megabytes(list.offline_bytes)} de ${megabytes(list.max_offline_bytes)} MB`;
}

/**
 * Whether the package is close enough to its ceiling to say so.
 *
 * Warned at four fifths and not at the limit: the limit is where the next upload is refused, and
 * discovering that while assembling a work order's drawings is late. Nothing is blocked here — the
 * server decides — this only puts the number in front of the person before they hit it.
 */
export function budgetWarning(list: AttachmentList | null): string | null {
  if (!list || list.max_offline_bytes <= 0) return null;
  if (list.offline_bytes < list.max_offline_bytes * 0.8) return null;
  return (
    `Esta OT ya lleva ${megabytes(list.offline_bytes)} MB de adjuntos offline, de ` +
    `${megabytes(list.max_offline_bytes)} MB. Marque como «no baja al teléfono» lo que no se abre ` +
    'en el sitio.'
  );
}

/** Why a withdrawal cannot be sent yet, in the words the person needs to fix it. */
export function withdrawProblems(reason: string): string[] {
  if (!reason.trim()) {
    return ['Escriba el motivo: la cuadrilla pudo haber trabajado con este plano.'];
  }
  return [];
}

/** What a row is about to do, said before it does it. */
export function withdrawAdvice(row: AttachmentRow): string {
  const shared = row.fromWork
    ? ' Es un adjunto de la obra: al retirarlo deja de viajar para todos sus frentes.'
    : '';
  return (
    `«${row.attachment.title}» deja de viajar en los paquetes nuevos. No se borra: ` +
    `la cuadrilla pudo ejecutar el trabajo con él.${shared}`
  );
}
