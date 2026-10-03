/**
 * Reading the crews' positions on the dispatch map (RF-020).
 *
 * The map answers one question — «who is closest to this fault?» — and every judgement here exists
 * to stop it answering it wrongly:
 *
 * 1. **A dot is as old as the last sync.** The position is captured when the phone talks to the
 *    server, so it can be hours old. The age is shown next to every dot, and a stale one is drawn
 *    differently, because a dispatcher who trusts an old dot sends a crew to the wrong parish.
 * 2. **A fix with 900 m of accuracy is not a location.** It is shown as doubtful rather than as a
 *    confident point on a street.
 * 3. **A phone is not a crew.** The link comes from the work the phone is carrying, so a phone with
 *    no crew work says so instead of being labelled with somebody else's crew.
 * 4. **The thresholds come from the server.** Repeating «two hours» here would let the map keep
 *    calling something recent after the server stopped doing so.
 */

import type { CrewPositionCollection, CrewPositionFeature } from '../../api/dispatch';

export interface PositionRow {
  feature: CrewPositionFeature;
  /** Crews this phone is carrying work for, as one label. */
  crewLabel: string;
  ageLabel: string;
  /** What can be said about this dot: it drives both the colour and the sentence. */
  confidence: 'reciente' | 'vieja' | 'dudosa';
}

export const CONFIDENCE_LABEL: Record<PositionRow['confidence'], string> = {
  reciente: 'Posición reciente',
  vieja: 'Posición vieja',
  dudosa: 'Posición dudosa',
};

/** Grey for stale, hollow-ish amber for doubtful, blue for usable. Never red: nothing is wrong. */
export const CONFIDENCE_COLOR: Record<PositionRow['confidence'], string> = {
  reciente: '#1e3a5f',
  dudosa: '#a16207',
  vieja: '#78716c',
};

export function ageLabel(minutes: number): string {
  if (minutes <= 0) return 'ahora mismo';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours < 24) return rest === 0 ? `hace ${hours} h` : `hace ${hours} h ${rest} min`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'hace más de un día' : `hace ${days} días`;
}

export function crewLabel(feature: CrewPositionFeature): string {
  const crews = feature.properties.crews;
  if (crews.length === 0) {
    // Dicho y no escondido: el teléfono está ahí, pero la plataforma no puede decir de qué
    // cuadrilla es, porque el vínculo sale del trabajo que lleva y no lleva ninguno.
    return 'Sin trabajo de cuadrilla';
  }
  return crews.map((crew) => `${crew.code} — ${crew.name}`).join('; ');
}

export function confidenceOf(feature: CrewPositionFeature): PositionRow['confidence'] {
  // El orden importa: una posición vieja **y** dudosa es, sobre todo, vieja. Una precisión mala se
  // puede mirar con cuidado; una hora de antigüedad ya no dice dónde está la cuadrilla.
  if (feature.properties.stale) return 'vieja';
  if (feature.properties.doubtful) return 'dudosa';
  return 'reciente';
}

export function rows(collection: CrewPositionCollection | null): PositionRow[] {
  if (!collection) return [];
  return (
    collection.features
      .map((feature) => ({
        feature,
        crewLabel: crewLabel(feature),
        ageLabel: ageLabel(feature.properties.minutes_old),
        confidence: confidenceOf(feature),
      }))
      // Lo más fresco primero: es lo que se puede usar para despachar.
      .sort(
        (left, right) => left.feature.properties.minutes_old - right.feature.properties.minutes_old,
      )
  );
}

/** What the map cannot promise, said with its numbers and in the server's terms. */
export function positionCaveats(collection: CrewPositionCollection | null): string[] {
  if (!collection) return [];
  const caveats: string[] = [];
  const stale = collection.features.filter((feature) => feature.properties.stale).length;
  const doubtful = collection.features.filter(
    (feature) => feature.properties.doubtful && !feature.properties.stale,
  ).length;
  const hours = Math.round(collection.stale_after_minutes / 60);
  if (stale > 0) {
    caveats.push(
      `${stale} de ${collection.features.length} posiciones tienen más de ${hours} h: ` +
        'la cuadrilla pudo moverse desde entonces.',
    );
  }
  if (doubtful > 0) {
    caveats.push(
      `${doubtful} posiciones tienen una precisión peor que ` +
        `${Math.round(collection.doubtful_accuracy_m)} m: sirven para la zona, no para la calle.`,
    );
  }
  return caveats;
}

/** The headline: how many phones the map is drawing, and how many are worth dispatching on. */
export function headline(collection: CrewPositionCollection | null): string {
  if (!collection || collection.features.length === 0) {
    return 'Ningún teléfono ha reportado su posición.';
  }
  const usable = collection.features.filter((feature) => !feature.properties.stale).length;
  return `${collection.features.length} teléfonos con posición; ${usable} reportaron hace poco.`;
}

/** Accuracy as the panel says it, with the unit and never as a bare number. */
export function accuracyLabel(feature: CrewPositionFeature): string {
  const accuracy = feature.properties.accuracy_m;
  if (accuracy === null) return 'Precisión no reportada';
  return `± ${Math.round(accuracy)} m`;
}
