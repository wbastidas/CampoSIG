/**
 * Los juicios del panel de ruta sugerida (RF-025).
 *
 * Lo que este módulo decide: qué tan buena es la sugerencia frente a lo que ya había, y cómo se
 * dice — nunca como un porcentaje suelto, siempre con las dos distancias detrás (RF-025's own
 * comparison against the naive order).
 */

import type { RouteSuggestion } from '../../api/routing';

/** Kilómetros con una cifra decimal, en es-EC (coma decimal, regla 11). */
export function km(meters: number): string {
  return (meters / 1000).toFixed(1).replace('.', ',');
}

/**
 * Cuánto se ahorra, dicho con las dos distancias detrás.
 *
 * Nunca un porcentaje solo: «un 42% menos» no dice si eran 2 km o 200, y las dos son preguntas
 * distintas para quien decide si vale la pena seguir la sugerencia.
 */
export function savingsHeadline(suggestion: RouteSuggestion): string {
  if (suggestion.naive_distance_m <= 0) {
    return `${km(suggestion.total_distance_m)} km`;
  }
  const saved = suggestion.naive_distance_m - suggestion.total_distance_m;
  if (saved <= 0) {
    return `${km(suggestion.total_distance_m)} km — ya era el mejor orden`;
  }
  const pct = Math.round((saved / suggestion.naive_distance_m) * 100);
  return (
    `${km(suggestion.total_distance_m)} km, frente a ${km(suggestion.naive_distance_m)} km en ` +
    `el orden pedido (${pct} % menos)`
  );
}

/** Por qué no se puede pedir una ruta todavía, en las palabras que hay que arreglar. */
export function requestProblems(selectedCount: number): string[] {
  if (selectedCount < 2) {
    return ['Seleccione al menos dos OT para pedir una ruta.'];
  }
  return [];
}
