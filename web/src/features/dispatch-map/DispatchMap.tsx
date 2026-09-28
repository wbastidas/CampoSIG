/**
 * El tablero de despacho con mapa (RF-020).
 *
 * «El mapa muestra OT y cuadrillas con filtros por área, zona y prioridad». Es una pantalla distinta
 * del tablero de despacho en tabla —que contesta «¿llegó el trabajo al teléfono?»— porque esta
 * contesta una pregunta espacial: «¿quién está más cerca de esta falla?».
 *
 * Dos cosas que la pantalla no hace: no dibuja una posición sin decir de cuándo es, y no repite los
 * umbrales del servidor. Una posición se captura cuando el teléfono sincroniza, así que puede tener
 * horas; un punto viejo pintado como uno fresco manda una cuadrilla a la parroquia equivocada.
 *
 * Todo juicio vive en `positions.ts` y se prueba ahí. Este archivo pinta.
 */

import { type GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl';
import { useCallback, useEffect, useRef, useState } from 'react';

import { type CrewPositionCollection, fetchCrewPositions } from '../../api/dispatch';
import {
  ApiError,
  fetchWorkOrders,
  type Priority,
  type WorkOrderCollection,
} from '../../api/planning';
import { PRIORITY_COLOR, PRIORITY_LABEL, PRIORITY_ORDER } from '../planning/style';
import {
  accuracyLabel,
  CONFIDENCE_COLOR,
  CONFIDENCE_LABEL,
  headline,
  positionCaveats,
  rows,
} from './positions';

const ORDERS_SOURCE = 'dispatch-work-orders';
const ORDERS_LAYER = 'dispatch-work-orders-circles';
const CREWS_SOURCE = 'dispatch-crews';
const CREWS_LAYER = 'dispatch-crews-circles';

/** El mismo basemap propio del planificador: PMTiles servidas por nuestro backend (anexo 5.4). */
const BASEMAP_STYLE = '/tiles/basemap.json';

/** Las áreas del SRS (1.3), que son las que declara cada formulario. */
const AREAS: { value: string; label: string }[] = [
  { value: '', label: 'Todas las áreas' },
  { value: 'operacion', label: 'Operación' },
  { value: 'mantenimiento', label: 'Mantenimiento' },
  { value: 'apg', label: 'Alumbrado público' },
  { value: 'ingenieria', label: 'Ingeniería' },
  { value: 'sso', label: 'Seguridad y salud' },
];

export interface DispatchMapProps {
  businessUnit: string;
  initialCenter?: [number, number];
  initialZoom?: number;
}

export function DispatchMap({
  businessUnit,
  initialCenter = [-79.9, -2.17],
  initialZoom = 12,
}: DispatchMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  const [area, setArea] = useState('');
  const [zone, setZone] = useState('');
  const [priorities, setPriorities] = useState<Priority[]>([]);
  const [orders, setOrders] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [crews, setCrews] = useState<CrewPositionCollection | null>(null);
  const [status, setStatus] = useState<string | null>(null);

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
          {
            ...(area ? { area } : {}),
            ...(zone ? { zone } : {}),
            ...(priorities.length > 0 ? { priorities } : {}),
          },
          signal,
        );
        setOrders(collection.features.length);
        setTruncated(collection.truncated);
        const ordersSource = map.getSource<GeoJSONSource>(ORDERS_SOURCE);
        void ordersSource?.setData(collection);

        // Las posiciones se filtran por zona y no por el viewport: un despachador que busca quién
        // está más cerca necesita ver también el teléfono que está justo fuera del encuadre.
        const positions = await fetchCrewPositions(businessUnit, zone ? { zone } : {}, signal);
        setCrews(positions);
        const crewsSource = map.getSource<GeoJSONSource>(CREWS_SOURCE);
        void crewsSource?.setData(positions);
        setStatus(null);
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setStatus(
          error instanceof ApiError ? error.message : 'No se pudo cargar el mapa de despacho',
        );
      }
    },
    [area, businessUnit, priorities, zone],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: initialCenter,
      zoom: initialZoom,
    });
    mapRef.current = map;

    map.on('load', () => {
      map.addSource(ORDERS_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        promoteId: 'id',
      });
      map.addLayer({
        id: ORDERS_LAYER,
        type: 'circle',
        source: ORDERS_SOURCE,
        paint: {
          'circle-radius': 6,
          'circle-color': [
            'match',
            ['get', 'priority'],
            ...PRIORITY_ORDER.flatMap((priority) => [priority, PRIORITY_COLOR[priority]]),
            '#57534e',
          ],
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff',
        } as never,
      });
      map.addSource(CREWS_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        promoteId: 'device_key',
      });
      map.addLayer({
        id: CREWS_LAYER,
        type: 'circle',
        source: CREWS_SOURCE,
        paint: {
          // Las cuadrillas se dibujan más grandes y con borde grueso: son pocas y son lo que se
          // busca. Y el color dice la confianza, no la prioridad de nada.
          'circle-radius': 9,
          'circle-color': [
            'case',
            ['boolean', ['get', 'stale'], false],
            CONFIDENCE_COLOR.vieja,
            ['boolean', ['get', 'doubtful'], false],
            CONFIDENCE_COLOR.dudosa,
            CONFIDENCE_COLOR.reciente,
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
          // Una posición vieja se dibuja translúcida: está ahí, pero no se despacha sobre ella.
          'circle-opacity': ['case', ['boolean', ['get', 'stale'], false], 0.45, 0.95],
        } as never,
      });
      void reload();
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // Se construye una vez: recrear el mapa en cada cambio de filtro perdería el encuadre.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    // Un cambio de filtro recarga sin esperar a que alguien mueva el mapa.
    void reload(controller.signal);
    return () => {
      controller.abort();
      map.off('moveend', onMoveEnd);
    };
  }, [reload]);

  const togglePriority = (priority: Priority) => {
    setPriorities((current) =>
      current.includes(priority)
        ? current.filter((item) => item !== priority)
        : [...current, priority],
    );
  };

  const view = rows(crews);
  const caveats = positionCaveats(crews);

  return (
    <div className="planner">
      <div ref={containerRef} className="planner__map" />

      <aside className="planner__panel" aria-label="Despacho">
        <h2>Despacho en el mapa</h2>
        <p className="planner__hint">
          {orders} OT en esta vista. {headline(crews)}
        </p>

        {truncated && (
          <p role="status" className="planner__warning">
            El mapa muestra solo parte de las OT de esta vista. Acerque para verlas todas.
          </p>
        )}

        <label htmlFor="area">Área</label>
        <select id="area" value={area} onChange={(event) => setArea(event.target.value)}>
          {AREAS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <label htmlFor="zona">Zona</label>
        <input
          id="zona"
          value={zone}
          onChange={(event) => setZone(event.target.value)}
          placeholder="Todas"
        />

        <fieldset className="dm-priorities">
          <legend>Prioridad</legend>
          {PRIORITY_ORDER.map((priority) => (
            <label key={priority}>
              <input
                type="checkbox"
                checked={priorities.includes(priority)}
                onChange={() => togglePriority(priority)}
              />
              {PRIORITY_LABEL[priority]}
            </label>
          ))}
        </fieldset>

        {caveats.map((line) => (
          <p key={line} role="status" className="planner__warning">
            {line}
          </p>
        ))}

        <h3>Cuadrillas</h3>
        {view.length === 0 && <p className="planner__hint">Ninguna posición para este filtro.</p>}
        <ul className="dm-crews">
          {view.map((row) => (
            <li key={row.feature.properties.device_key}>
              <strong>{row.crewLabel}</strong>
              <span>
                {CONFIDENCE_LABEL[row.confidence]} · {row.ageLabel} · {accuracyLabel(row.feature)}
              </span>
              <span className="dm-device">{row.feature.properties.device_key}</span>
            </li>
          ))}
        </ul>

        {status && (
          <p role="status" className="planner__status">
            {status}
          </p>
        )}
      </aside>
    </div>
  );
}
