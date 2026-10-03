/**
 * La cédula ecuatoriana del cliente (RF-046), un tercio de un contrato.
 *
 * Los otros dos tercios son `backend/app/forms/identification.py` y `core:sync`'s `Cedula.kt`, y
 * los tres ejecutan `forms/contract/identification-cases.json`.
 *
 * Diez dígitos ASCII; provincia 01 a 24, o 30 para ecuatorianos registrados en el exterior; tercer
 * dígito menor que 6 (persona natural); verificador por módulo 10 con coeficientes 2,1,2,1,…
 * Sin normalizar: espacios y guiones los quita la pantalla, no el validador.
 */
export function isValidCedula(value: string): boolean {
  // `\d` sin la bandera `u` ya es solo ASCII en JavaScript; se escribe la clase explícita igual,
  // para que nadie la «moderniza» a `\p{Nd}` y acepte dígitos de otras escrituras.
  if (!/^[0-9]{10}$/.test(value)) return false;
  const digits = Array.from(value, (char) => char.charCodeAt(0) - 48);
  const province = digits[0]! * 10 + digits[1]!;
  if (!((province >= 1 && province <= 24) || province === 30)) return false;
  if (digits[2]! >= 6) return false;
  let total = 0;
  for (let index = 0; index < 9; index += 1) {
    const product = digits[index]! * (index % 2 === 0 ? 2 : 1);
    total += product > 9 ? product - 9 : product;
  }
  return (10 - (total % 10)) % 10 === digits[9];
}

/** Which fields of a form schema carry the `ec-cedula` format, read from the data (rule 3). */
export function cedulaFields(schema: { properties?: Record<string, unknown> }): string[] {
  return Object.entries(schema.properties ?? {})
    .filter(
      ([, spec]) =>
        typeof spec === 'object' &&
        spec !== null &&
        (spec as { format?: unknown }).format === 'ec-cedula',
    )
    .map(([field]) => field);
}
