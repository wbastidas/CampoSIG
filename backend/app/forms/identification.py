"""La cédula ecuatoriana del cliente (RF-046), un tercio de un contrato.

Los otros dos tercios son `web/src/forms/identification.ts` y `core:sync`'s `Cedula.kt`, y los tres
ejecutan `forms/contract/identification-cases.json`.

Diez dígitos ASCII; provincia 01 a 24, o 30 para ecuatorianos registrados en el exterior; tercer
dígito menor que 6 (persona natural); verificador por módulo 10 con coeficientes 2,1,2,1,…
Sin normalizar espacios ni guiones: eso lo hace la pantalla, para que las tres plataformas no
discrepen en qué limpiar.
"""

from __future__ import annotations

import re

#: El nombre del formato en los esquemas de formulario. Un dato del bloque (`format: ec-cedula`),
#: no un nombre de campo que el código reconozca (regla 3).
CEDULA_FORMAT = "ec-cedula"

# `[0-9]` y no `\d`: en Python `\d` acepta dígitos de cualquier escritura.
_TEN_DIGITS = re.compile(r"[0-9]{10}")


def is_valid_cedula(value: str) -> bool:
    if not isinstance(value, str) or not _TEN_DIGITS.fullmatch(value):
        return False
    digits = [ord(char) - 48 for char in value]
    province = digits[0] * 10 + digits[1]
    if not (1 <= province <= 24 or province == 30):
        return False
    if digits[2] >= 6:
        return False
    total = 0
    for index in range(9):
        product = digits[index] * (2 if index % 2 == 0 else 1)
        total += product - 9 if product > 9 else product
    return (10 - total % 10) % 10 == digits[9]
