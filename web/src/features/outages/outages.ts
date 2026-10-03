/**
 * Reading consignaciones (RF-024).
 *
 * Four things the screen has to make impossible to miss, because each is a way a board of descargos
 * looks fine while the field situation is not:
 *
 * 1. **The number is the authority, not the state.** A row that says «aprobada» with no number opens
 *    no permit, and the two look identical unless the screen says which one it is looking at.
 * 2. **A granted descargo nobody used is a line de-energised for nothing** — customers without
 *    service and an index the unit reports. It is shown, never counted in silence.
 * 3. **A window that already closed while the descargo is still granted** is a crew with the paper
 *    in hand and equipment that may already be energised. The dates alone do not say it.
 * 4. **Whoever asked does not grant.** The server refuses it by author, and the screen says so
 *    before the click so nobody reads a 403 as a bug.
 */

import type { OutageList, OutageRequestRow, OutageStateValue } from '../../api/outages';

export const STATE_LABEL: Record<string, string> = {
  solicitada: 'Solicitada',
  aprobada: 'Otorgada',
  rechazada: 'Negada',
  vencida: 'Vencida',
  devuelta: 'Devuelta',
};

export function stateLabel(state: string): string {
  return STATE_LABEL[state] ?? state;
}

/** es-EC: día/mes y hora de 24 h, que es como el Centro de Control dice una ventana. */
export function windowLabel(row: OutageRequestRow): string {
  const start = new Date(row.window_start);
  const end = new Date(row.window_end);
  const day = new Intl.DateTimeFormat('es-EC', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'America/Guayaquil',
  });
  const time = new Intl.DateTimeFormat('es-EC', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'America/Guayaquil',
  });
  const sameDay = day.format(start) === day.format(end);
  return sameDay
    ? `${day.format(start)}, ${time.format(start)} a ${time.format(end)}`
    : `${day.format(start)} ${time.format(start)} a ${day.format(end)} ${time.format(end)}`;
}

/** What this row authorises, in one line. Never «aprobada» on its own. */
export function authorityLine(row: OutageRequestRow): string {
  if (row.grants_permit && row.number) {
    return `Habilita el F-TR-02 con el N.º ${row.number}`;
  }
  if (row.state === 'aprobada') {
    // Una fila así solo se consigue por carga directa o migración a medias, y no habilita nada.
    return 'Otorgada sin número: no habilita el F-TR-02. El número es la autoridad.';
  }
  return 'No habilita el F-TR-02';
}

export interface OutageRow {
  request: OutageRequestRow;
  /** True while the Centro de Control still owes an answer. */
  awaiting: boolean;
  /** Granted, in force, and with no work order under it. */
  unused: boolean;
  /** Granted and the window already closed: the equipment may already be energised. */
  overdue: boolean;
}

export function rows(list: OutageList | null, now: Date = new Date()): OutageRow[] {
  if (!list) return [];
  const view = list.requests.map((request) => ({
    request,
    awaiting: request.state === 'solicitada',
    unused: Boolean(request.unused),
    overdue: request.state === 'aprobada' && new Date(request.window_end) < now,
  }));
  // Lo que espera una decisión primero, y dentro de cada grupo por ventana: es el orden en que el
  // Centro de Control trabaja, no el de creación.
  return view.sort((left, right) => {
    if (left.awaiting !== right.awaiting) return left.awaiting ? -1 : 1;
    return left.request.window_start.localeCompare(right.request.window_start);
  });
}

/** How many are waiting on the Centro de Control, for the headline. */
export function awaitingCount(list: OutageList | null): number {
  return list?.counts.solicitada ?? 0;
}

/** Said with the count, because one unused descargo is a phone call and six are a problem. */
export function unusedWarning(view: OutageRow[]): string | null {
  const count = view.filter((row) => row.unused).length;
  if (count === 0) return null;
  return count === 1
    ? 'Una consignación otorgada no tiene ninguna OT vinculada: es una línea desenergizada para nada.'
    : `${count} consignaciones otorgadas no tienen ninguna OT vinculada: son líneas desenergizadas ` +
        'para nada.';
}

export function overdueWarning(view: OutageRow[]): string | null {
  const count = view.filter((row) => row.overdue).length;
  if (count === 0) return null;
  return count === 1
    ? 'Una consignación otorgada tiene la ventana cerrada y sigue vigente: devuélvala si el trabajo terminó.'
    : `${count} consignaciones otorgadas tienen la ventana cerrada y siguen vigentes: devuélvalas si ` +
        'el trabajo terminó.';
}

export function canDecide(row: OutageRow): boolean {
  return row.awaiting;
}

export function canHandBack(row: OutageRow): boolean {
  return row.request.state === 'aprobada';
}

/**
 * Whether this person asked for this descargo, so the screen can say it before the server does.
 *
 * The server refuses the approval by author (403) whatever the roles say. Hiding the button would
 * be a lie about why; saying it is what lets a supervisor call the Centro de Control instead of
 * reporting a bug.
 */
export function isOwnRequest(row: OutageRow, subject: string | null): boolean {
  return Boolean(subject) && row.request.requested_by === subject;
}

export interface DecisionDraft {
  decision: 'otorgar' | 'negar' | '';
  number: string;
  note: string;
}

export const EMPTY_DECISION: DecisionDraft = { decision: '', number: '', note: '' };

/** Why a decision cannot be sent yet, in the words the person needs to fix it. */
export function decisionProblems(draft: DecisionDraft): string[] {
  const problems: string[] = [];
  if (!draft.decision) problems.push('Elija si otorga o niega.');
  if (draft.decision === 'otorgar' && !draft.number.trim()) {
    problems.push('Escriba el N.º de consignación: es lo que la cuadrilla repite por radio.');
  }
  if (draft.decision === 'negar' && !draft.note.trim()) {
    problems.push('Escriba el motivo: un «no» sin motivo manda al planificador al teléfono.');
  }
  return problems;
}

/** What the decision is about to do, said before it is taken. */
export function decisionAdvice(row: OutageRow, draft: DecisionDraft): string | null {
  if (draft.decision === 'otorgar') {
    return (
      `Con el N.º ${draft.number.trim() || '…'} se habilita el F-TR-02 para las OT de esta ` +
      `consignación, en la ventana ${windowLabel(row.request)}.`
    );
  }
  if (draft.decision === 'negar') {
    return 'Negada, el permiso de trabajo no se habilita y el motivo queda con su autor.';
  }
  return null;
}

/** Why a new request cannot be sent, checked here so the person is not sent to a 422. */
export function requestProblems(draft: {
  equipment: string;
  windowStart: string;
  windowEnd: string;
}): string[] {
  const problems: string[] = [];
  if (!draft.equipment.trim()) problems.push('Diga qué equipo o tramo se consigna.');
  if (!draft.windowStart || !draft.windowEnd) {
    problems.push('Una consignación sin ventana no se puede comparar con nada.');
  } else if (new Date(draft.windowEnd) <= new Date(draft.windowStart)) {
    problems.push('La ventana termina antes de empezar.');
  }
  return problems;
}

export const STATES: { value: OutageStateValue | ''; label: string }[] = [
  { value: '', label: 'Todas' },
  { value: 'solicitada', label: 'Solicitadas' },
  { value: 'aprobada', label: 'Otorgadas' },
  { value: 'devuelta', label: 'Devueltas' },
  { value: 'rechazada', label: 'Negadas' },
  { value: 'vencida', label: 'Vencidas' },
];
