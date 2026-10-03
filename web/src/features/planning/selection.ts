/**
 * Lasso selection geometry and state, kept free of React and MapLibre.
 *
 * Separated deliberately: this is the logic that decides which work orders a planner just
 * selected, and getting it wrong means assigning the wrong work to the wrong crew. Pure
 * functions can be tested exhaustively without a browser or a map.
 */

import type { BoundingBox, WorkOrderFeature } from '../../api/planning';

export interface ScreenPoint {
  x: number;
  y: number;
}

export interface LngLat {
  lng: number;
  lat: number;
}

/** A drag rectangle, normalised so direction of travel does not matter. */
export function normaliseDragBox(start: ScreenPoint, end: ScreenPoint) {
  return {
    left: Math.min(start.x, end.x),
    top: Math.min(start.y, end.y),
    right: Math.max(start.x, end.x),
    bottom: Math.max(start.y, end.y),
  };
}

/** A drag shorter than this is a click, not a lasso. */
export const MIN_DRAG_PIXELS = 4;

export function isLasso(start: ScreenPoint, end: ScreenPoint): boolean {
  const box = normaliseDragBox(start, end);
  return box.right - box.left >= MIN_DRAG_PIXELS && box.bottom - box.top >= MIN_DRAG_PIXELS;
}

/** Bounding box from two corners in geographic coordinates. */
export function boundsFromCorners(a: LngLat, b: LngLat): BoundingBox {
  return {
    west: Math.min(a.lng, b.lng),
    south: Math.min(a.lat, b.lat),
    east: Math.max(a.lng, b.lng),
    north: Math.max(a.lat, b.lat),
  };
}

export function containsPoint(bounds: BoundingBox, lng: number, lat: number): boolean {
  return lng >= bounds.west && lng <= bounds.east && lat >= bounds.south && lat <= bounds.north;
}

/**
 * Which features a lasso selected.
 *
 * Only assignable work is selectable: a planner dragging across the map must not pick up
 * orders a crew is already executing, because "assign" would be refused for them anyway and
 * the refusals would drown the result.
 */
export function selectableInBounds(
  features: WorkOrderFeature[],
  bounds: BoundingBox,
): WorkOrderFeature[] {
  return features.filter(
    (feature) =>
      isAssignable(feature) &&
      containsPoint(bounds, feature.geometry.coordinates[0], feature.geometry.coordinates[1]),
  );
}

/** Mirrors the server's rule (`WorkOrder.is_assignable`) so the UI never offers what the
 *  API would reject. Duplicated on purpose, and the contract test keeps the two in step. */
export function isAssignable(feature: WorkOrderFeature): boolean {
  return feature.properties.state === 'planificada' || feature.properties.state === 'asignada';
}

export interface SelectionSummary {
  total: number
  unassigned: number
  reassignment: number
  byPriority: Record<string, number>
}

/** What the assignment panel shows before the planner commits. */
export function summarise(features: WorkOrderFeature[]): SelectionSummary {
  const byPriority: Record<string, number> = {};
  let unassigned = 0;
  let reassignment = 0;
  for (const feature of features) {
    const { priority, assigned } = feature.properties;
    byPriority[priority] = (byPriority[priority] ?? 0) + 1;
    if (assigned) reassignment += 1;
    else unassigned += 1;
  }
  return { total: features.length, unassigned, reassignment, byPriority };
}

/** Toggle one feature in a selection, for click-to-add after a lasso. */
export function toggle(selected: Set<string>, id: string): Set<string> {
  const next = new Set(selected);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}
