/**
 * The auditor's screen (RF-161), over the immutable trail of RF-160.
 *
 * Four filters because RF-161 asks four questions — by work order, by asset, by person, by device —
 * and they compose, so «what did this person do to this work order» is one query.
 *
 * The screen has no button that changes anything, and that is the requirement rather than an
 * oversight. What it does have is the chain verification, shown at the top where it cannot be
 * missed: a trail whose integrity nobody checks is a trail that proves nothing, and the check is
 * one click precisely so that it gets made.
 */

import { useCallback, useEffect, useState } from 'react';

import { type AuditEvent, type ChainCheck, fetchTrail, verifyChain } from '../../api/audit';
import {
  ACTOR_LABEL,
  chainVerdict,
  kindLabel,
  modelBehind,
  mostRecentFirst,
  summarise,
} from './trail';

export interface AuditScreenProps {
  /** Required: a unit's trail is the unit's (ADR-009). */
  businessUnit: string;
}

const PAGE = 100;

export function AuditScreen({ businessUnit }: AuditScreenProps) {
  const [filters, setFilters] = useState({ workOrderId: '', assetCode: '', actor: '', deviceKey: '' });
  const [applied, setApplied] = useState(filters);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [check, setCheck] = useState<ChainCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const body = await fetchTrail(
          businessUnit,
          {
            workOrderId: applied.workOrderId || undefined,
            assetCode: applied.assetCode || undefined,
            actor: applied.actor || undefined,
            deviceKey: applied.deviceKey || undefined,
            limit: PAGE,
          },
          signal,
        );
        setEvents(body.events);
        setTotal(body.total);
        setError(null);
      } catch (cause) {
        if ((cause as Error).name === 'AbortError') return;
        setError((cause as Error).message);
      }
    },
    [businessUnit, applied],
  );

  useEffect(() => {
    const controller = new AbortController();
    // El setState ocurre tras el await dentro del callback, no en el cuerpo del efecto.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const verify = useCallback(async () => {
    setBusy(true);
    try {
      setCheck(await verifyChain(businessUnit));
      setError(null);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }, [businessUnit]);

  return (
    <section className="audit">
      <header>
        <h1>Bitácora</h1>
        <p className="review-hint">
          Registro inmutable de creación, cambios de campo, cambios de estado, accesos a evidencias,
          exportaciones y decisiones. No se puede editar ni borrar: la base lo rechaza y la cadena de
          hashes lo delataría.
        </p>
        {error && (
          <p role="alert" className="board-error">
            {error}
          </p>
        )}
      </header>

      <section aria-label="Integridad de la cadena" className="audit-chain">
        <button type="button" disabled={busy} onClick={() => void verify()}>
          Verificar la cadena
        </button>
        {check && (
          <p role="status" className={check.intact ? 'audit-ok' : 'audit-broken'}>
            {chainVerdict(check)}
          </p>
        )}
      </section>

      <form
        aria-label="Filtros de trazabilidad"
        onSubmit={(submitted) => {
          submitted.preventDefault();
          setApplied(filters);
        }}
      >
        <label htmlFor="audit-wo">Orden de trabajo</label>
        <input
          id="audit-wo"
          value={filters.workOrderId}
          onChange={(event) => setFilters({ ...filters, workOrderId: event.target.value })}
          placeholder="identificador"
        />
        <label htmlFor="audit-asset">Activo</label>
        <input
          id="audit-asset"
          value={filters.assetCode}
          onChange={(event) => setFilters({ ...filters, assetCode: event.target.value })}
        />
        <label htmlFor="audit-actor">Persona</label>
        <input
          id="audit-actor"
          value={filters.actor}
          onChange={(event) => setFilters({ ...filters, actor: event.target.value })}
        />
        <label htmlFor="audit-device">Dispositivo</label>
        <input
          id="audit-device"
          value={filters.deviceKey}
          onChange={(event) => setFilters({ ...filters, deviceKey: event.target.value })}
        />
        <button type="submit">Buscar</button>
      </form>

      <p>
        {events.length} de {total} evento(s) en la unidad.
        {events.length === PAGE && ' Se muestran los más recientes de la consulta.'}
      </p>

      {events.length === 0 ? (
        <p>Ningún evento coincide con la consulta.</p>
      ) : (
        <table className="audit-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Cuándo</th>
              <th>Qué</th>
              <th>Detalle</th>
              <th>Quién</th>
            </tr>
          </thead>
          <tbody>
            {mostRecentFirst(events).map((event) => (
              <tr key={event.sequence}>
                <td>{event.sequence}</td>
                <td>{event.occurred_at?.slice(0, 19).replace('T', ' ') ?? '—'}</td>
                <td>{kindLabel(event.kind)}</td>
                <td>
                  {summarise(event)}
                  {event.reason && <div className="ai-board-note">Motivo: {event.reason}</div>}
                  {modelBehind(event) && (
                    /* El origen que pide RF-160: la persona respondió por el valor, el modelo lo
                       propuso, y las dos cosas se leen juntas o no se entiende ninguna. */
                    <div className="ai-board-note">Propuesto por {modelBehind(event)}</div>
                  )}
                </td>
                <td>
                  {event.actor}
                  <div className="ai-board-note">
                    {ACTOR_LABEL[event.actor_kind] ?? event.actor_kind}
                    {event.device_key && ` · ${event.device_key}`}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
