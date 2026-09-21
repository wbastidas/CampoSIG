/**
 * Tests for the lasso selection logic.
 *
 * This is where a mistake assigns the wrong work to the wrong crew, so it is tested as pure
 * logic rather than through the map.
 */

import { describe, expect, it } from 'vitest';

import type { Priority, WorkOrderFeature, WorkOrderState } from '../../api/planning';
import {
  boundsFromCorners,
  containsPoint,
  isAssignable,
  isLasso,
  MIN_DRAG_PIXELS,
  normaliseDragBox,
  selectableInBounds,
  summarise,
  toggle,
} from './selection';

function feature(
  id: string,
  lng: number,
  lat: number,
  state: WorkOrderState = 'planificada',
  priority: Priority = 'media',
  assigned = false,
): WorkOrderFeature {
  return {
    type: 'Feature',
    id,
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: {
      code: id,
      work_type: 'inspeccion_preventiva',
      form_code: 'F-MT-01',
      state,
      priority,
      assigned,
      crew_id: assigned ? 'crew-1' : null,
      asset_code: null,
      feeder_code: null,
      sla_due_at: null,
      version: 1,
    },
  };
}

describe('normaliseDragBox', () => {
  it('normalises a drag regardless of direction', () => {
    const downRight = normaliseDragBox({ x: 10, y: 10 }, { x: 50, y: 40 });
    const upLeft = normaliseDragBox({ x: 50, y: 40 }, { x: 10, y: 10 });
    expect(downRight).toEqual(upLeft);
  });
});

describe('isLasso', () => {
  it('treats a tiny drag as a click, not a lasso', () => {
    expect(isLasso({ x: 10, y: 10 }, { x: 11, y: 11 })).toBe(false);
  });

  it('treats a deliberate drag as a lasso', () => {
    const far = MIN_DRAG_PIXELS + 1;
    expect(isLasso({ x: 10, y: 10 }, { x: 10 + far, y: 10 + far })).toBe(true);
  });

  it('a thin horizontal sweep is not a lasso', () => {
    // Otherwise a slightly imprecise click would select a whole row of pins.
    expect(isLasso({ x: 10, y: 10 }, { x: 200, y: 11 })).toBe(false);
  });
});

describe('boundsFromCorners', () => {
  it('orders the corners', () => {
    const bounds = boundsFromCorners({ lng: -79.7, lat: -1.9 }, { lng: -80.1, lat: -2.4 });
    expect(bounds).toEqual({ west: -80.1, south: -2.4, east: -79.7, north: -1.9 });
  });

  it('survives crossing the equator', () => {
    const bounds = boundsFromCorners({ lng: -78, lat: 0.5 }, { lng: -79, lat: -0.5 });
    expect(bounds.south).toBeLessThan(0);
    expect(bounds.north).toBeGreaterThan(0);
  });
});

describe('containsPoint', () => {
  const bounds = { west: -80.1, south: -2.4, east: -79.7, north: -1.9 };

  it('includes an interior point', () => {
    expect(containsPoint(bounds, -79.9, -2.17)).toBe(true);
  });

  it('includes points exactly on the edge', () => {
    // Inclusive on purpose: a pin that visually sits on the lasso edge should be selected.
    expect(containsPoint(bounds, -80.1, -2.4)).toBe(true);
  });

  it('excludes an outside point', () => {
    expect(containsPoint(bounds, -78.47, -0.18)).toBe(false);
  });
});

describe('isAssignable', () => {
  it('accepts planned and assigned work', () => {
    expect(isAssignable(feature('a', 0, 0, 'planificada'))).toBe(true);
    expect(isAssignable(feature('b', 0, 0, 'asignada'))).toBe(true);
  });

  it.each<WorkOrderState>(['en_ejecucion', 'cerrada', 'anulada', 'en_revision'])(
    'rejects %s',
    (state) => {
      expect(isAssignable(feature('c', 0, 0, state))).toBe(false);
    },
  );
});

describe('selectableInBounds', () => {
  const bounds = { west: -80.1, south: -2.4, east: -79.7, north: -1.9 };

  it('selects assignable work inside the box', () => {
    const features = [
      feature('inside', -79.9, -2.17),
      feature('outside', -78.47, -0.18),
    ];
    expect(selectableInBounds(features, bounds).map((f) => f.id)).toEqual(['inside']);
  });

  it('skips work already in execution even when inside the box', () => {
    // The server would refuse these, and the refusals would drown the useful result.
    const features = [
      feature('ok', -79.9, -2.17),
      feature('busy', -79.91, -2.18, 'en_ejecucion'),
    ];
    expect(selectableInBounds(features, bounds).map((f) => f.id)).toEqual(['ok']);
  });

  it('returns nothing for an empty map', () => {
    expect(selectableInBounds([], bounds)).toEqual([]);
  });
});

describe('summarise', () => {
  it('separates new assignments from reassignments', () => {
    const summary = summarise([
      feature('a', 0, 0, 'planificada', 'critica', false),
      feature('b', 0, 0, 'asignada', 'media', true),
      feature('c', 0, 0, 'asignada', 'media', true),
    ]);
    expect(summary.total).toBe(3);
    expect(summary.unassigned).toBe(1);
    // The planner needs to know they are taking work off someone before they confirm.
    expect(summary.reassignment).toBe(2);
    expect(summary.byPriority).toEqual({ critica: 1, media: 2 });
  });

  it('handles an empty selection', () => {
    expect(summarise([])).toEqual({ total: 0, unassigned: 0, reassignment: 0, byPriority: {} });
  });
});

describe('toggle', () => {
  it('adds then removes', () => {
    const once = toggle(new Set<string>(), 'a');
    expect(once.has('a')).toBe(true);
    expect(toggle(once, 'a').has('a')).toBe(false);
  });

  it('does not mutate the input', () => {
    const original = new Set(['a']);
    toggle(original, 'b');
    expect(original.size).toBe(1);
  });
});
