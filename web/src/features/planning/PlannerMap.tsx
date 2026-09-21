/**
 * Graphical assignment: the planner's map.
 *
 * The map is the primary tool, not a decoration beside a table. A planner sees the work,
 * drags a box around a cluster of it, picks a crew and assigns — one gesture instead of
 * twenty rows of checkboxes.
 *
 * The selection logic lives in `selection.ts` as pure functions, so the part where a mistake
 * would assign the wrong work to the wrong crew is tested without a browser.
 */

import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from 'maplibre-gl';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  ApiError,
  assignSelection,
  type Crew,
  fetchCrews,
  fetchWorkOrders,
  type WorkOrderCollection,
  type WorkOrderFeature,
} from '../../api/planning';
import {
  boundsFromCorners,
  isLasso,
  type ScreenPoint,
  selectableInBounds,
  summarise,
  toggle,
} from './selection';
import { workOrderCirclePaint } from './style';

const SOURCE_ID = 'work-orders';
const LAYER_ID = 'work-orders-circles';

/** Offline-capable basemap: PMTiles served by our own backend, not a commercial tile
 *  provider (addendum 5.4). No API key, no external dependency, no per-view cost. */
const BASEMAP_STYLE = '/tiles/basemap.json';

export interface PlannerMapProps {
  /** Required: one platform instance serves every business unit and nothing crosses
   *  between them (ADR-009). */
  businessUnit: string;
  initialCenter?: [number, number];
  initialZoom?: number;
}

export function PlannerMap({
  businessUnit,
  initialCenter = [-79.9, -2.17],
  initialZoom = 12,
}: PlannerMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const featuresRef = useRef<WorkOrderFeature[]>([]);
  const dragStartRef = useRef<ScreenPoint | null>(null);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [crews, setCrews] = useState<Crew[]>([]);
  const [crewId, setCrewId] = useState<string>('');
  const [status, setStatus] = useState<string | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [busy, setBusy] = useState(false);

  /** Paint the selection through feature state, so changing it never refetches. */
  const paintSelection = useCallback((ids: Set<string>) => {
    const map = mapRef.current;
    if (!map) return;
    for (const feature of featuresRef.current) {
      map.setFeatureState(
        { source: SOURCE_ID, id: feature.id },
        { selected: ids.has(feature.id) },
      );
    }
  }, []);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      const map = mapRef.current;
      if (!map) return;
      const bounds = map.getBounds();
      try {
        const collection: WorkOrderCollection = await fetchWorkOrders(
          businessUnit,
          {
            west: bounds.getWest(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            north: bounds.getNorth(),
          },
          {},
          signal,
        );
        featuresRef.current = collection.features;
        setTruncated(collection.truncated);
        const source = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
        source?.setData(collection);
        paintSelection(selected);
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setStatus(error instanceof Error ? error.message : 'No se pudieron cargar las OT');
      }
    },
    [businessUnit, paintSelection, selected],
  );

  // --- map setup -----------------------------------------------------------------
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: initialCenter,
      zoom: initialZoom,
      // The planner drags to lasso, so box-zoom must not steal the gesture.
      boxZoom: false,
    });
    mapRef.current = map;

    map.on('load', () => {
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        promoteId: 'id',
      });
      map.addLayer({
        id: LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        paint: workOrderCirclePaint() as never,
      });
      void reload();
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // Built once: re-creating the map on every state change would lose the viewport.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- reload on pan and zoom, cancelling the in-flight request -------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let controller = new AbortController();
    const onMoveEnd = () => {
      controller.abort();
      controller = new AbortController();
      void reload(controller.signal);
    };
    map.on('moveend', onMoveEnd);
    return () => {
      controller.abort();
      map.off('moveend', onMoveEnd);
    };
  }, [reload]);

  // --- lasso ----------------------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const onDown = (event: maplibregl.MapMouseEvent) => {
      if (!event.originalEvent.shiftKey) return;
      // Shift-drag is the lasso; plain drag stays pan, which is what a planner expects.
      dragStartRef.current = { x: event.point.x, y: event.point.y };
      map.dragPan.disable();
    };

    const onUp = (event: maplibregl.MapMouseEvent) => {
      const start = dragStartRef.current;
      dragStartRef.current = null;
      map.dragPan.enable();
      if (!start) return;

      const end = { x: event.point.x, y: event.point.y };
      if (!isLasso(start, end)) {
        // Too small to be deliberate: treat as a click that toggles one pin.
        const hits = map.queryRenderedFeatures(event.point, { layers: [LAYER_ID] });
        const hit = hits[0];
        if (hit?.id != null) {
          const next = toggle(selected, String(hit.id));
          setSelected(next);
          paintSelection(next);
        }
        return;
      }

      const bounds = boundsFromCorners(
        map.unproject([start.x, start.y]),
        map.unproject([end.x, end.y]),
      );
      const picked = selectableInBounds(featuresRef.current, bounds);
      const next = new Set(picked.map((feature) => feature.id));
      setSelected(next);
      paintSelection(next);
      setStatus(
        picked.length
          ? null
          : 'La selección no contiene OT asignables. Las que están en ejecución no se pueden reasignar desde aquí.',
      );
    };

    map.on('mousedown', onDown);
    map.on('mouseup', onUp);
    return () => {
      map.off('mousedown', onDown);
      map.off('mouseup', onUp);
    };
  }, [paintSelection, selected]);

  // --- crews ----------------------------------------------------------------------
  useEffect(() => {
    const controller = new AbortController();
    fetchCrews(businessUnit, controller.signal)
      .then((loaded) => {
        setCrews(loaded);
        setCrewId((current) => current || loaded[0]?.crew_id || '');
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setStatus('No se pudieron cargar las cuadrillas');
      });
    return () => controller.abort();
  }, [businessUnit]);

  // --- assign ---------------------------------------------------------------------
  const onAssign = useCallback(async () => {
    if (!crewId || selected.size === 0) return;
    setBusy(true);
    setStatus(null);
    try {
      const result = await assignSelection(businessUnit, [...selected], crewId);
      const parts = [`${result.assigned.length} OT asignadas`];
      if (result.failures.length) {
        // Partial success is normal and must be stated, not hidden behind a success toast.
        parts.push(`${result.failures.length} no se pudieron asignar`);
      }
      setStatus(parts.join('; '));
      setSelected(new Set());
      paintSelection(new Set());
      await reload();
    } catch (error) {
      setStatus(
        error instanceof ApiError
          ? error.message
          : 'No se pudo completar la asignación',
      );
    } finally {
      setBusy(false);
    }
  }, [businessUnit, crewId, paintSelection, reload, selected]);

  const summary = summarise(
    featuresRef.current.filter((feature) => selected.has(feature.id)),
  );

  return (
    <div className="planner">
      <div ref={containerRef} className="planner__map" />

      <aside className="planner__panel" aria-label="Asignación">
        <h2>Asignar trabajo</h2>
        <p className="planner__hint">
          Mantenga <kbd>Shift</kbd> y arrastre para seleccionar un grupo de OT. Clic para
          añadir o quitar una.
        </p>

        {truncated && (
          <p role="status" className="planner__warning">
            El mapa muestra solo parte de las OT de esta vista. Acerque para verlas todas.
          </p>
        )}

        <dl className="planner__summary">
          <dt>Seleccionadas</dt>
          <dd>{summary.total}</dd>
          <dt>Sin asignar</dt>
          <dd>{summary.unassigned}</dd>
          <dt>Reasignaciones</dt>
          <dd>{summary.reassignment}</dd>
        </dl>

        {summary.reassignment > 0 && (
          <p role="status" className="planner__warning">
            {summary.reassignment} de las seleccionadas ya están asignadas a otra cuadrilla.
            Al confirmar se les quitará el trabajo.
          </p>
        )}

        <label htmlFor="crew">Cuadrilla</label>
        <select
          id="crew"
          value={crewId}
          onChange={(event) => setCrewId(event.target.value)}
        >
          {crews.map((crew) => (
            <option key={crew.crew_id} value={crew.crew_id}>
              {crew.code} — {crew.name} ({crew.open_work_orders} abiertas)
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => void onAssign()}
          disabled={busy || summary.total === 0 || !crewId}
        >
          {busy ? 'Asignando…' : `Asignar ${summary.total} OT`}
        </button>

        {status && (
          <p role="status" className="planner__status">
            {status}
          </p>
        )}
      </aside>
    </div>
  );
}
