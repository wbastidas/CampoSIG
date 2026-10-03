/**
 * Map styling for the planner (dataviz-consistent, colour-blind safe).
 *
 * Priority drives colour and assignment drives shape, so the two dimensions stay readable
 * independently — a planner scanning for critical work should not have to also decode
 * whether each pin is assigned.
 */

import type { Priority } from '../../api/planning';

/** Ordered worst-first, matching the server's sort. */
export const PRIORITY_ORDER: Priority[] = ['critica', 'alta', 'media', 'baja'];

/**
 * Sequential ramp: perceptually ordered and distinguishable under deuteranopia and
 * protanopia, which rules out the red/green pairing this kind of board usually reaches for.
 */
export const PRIORITY_COLOR: Record<Priority, string> = {
  critica: '#7f1d1d',
  alta: '#c2410c',
  media: '#a16207',
  baja: '#3f6212',
};

export const PRIORITY_LABEL: Record<Priority, string> = {
  critica: 'Crítica',
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
};

/** MapLibre paint for the work-order layer. */
export function workOrderCirclePaint() {
  return {
    'circle-radius': [
      'case',
      ['boolean', ['feature-state', 'selected'], false],
      9,
      6,
    ],
    'circle-color': [
      'match',
      ['get', 'priority'],
      'critica', PRIORITY_COLOR.critica,
      'alta', PRIORITY_COLOR.alta,
      'media', PRIORITY_COLOR.media,
      'baja', PRIORITY_COLOR.baja,
      '#57534e',
    ],
    // Unassigned work gets a white ring so it reads as "available" at a glance; selected
    // work gets a heavier ring so the lasso result is unmistakable.
    'circle-stroke-width': [
      'case',
      ['boolean', ['feature-state', 'selected'], false],
      3,
      ['get', 'assigned'],
      1,
      2,
    ],
    'circle-stroke-color': [
      'case',
      ['boolean', ['feature-state', 'selected'], false],
      '#0c4a6e',
      '#ffffff',
    ],
    'circle-opacity': ['case', ['get', 'assigned'], 0.65, 0.95],
  };
}
