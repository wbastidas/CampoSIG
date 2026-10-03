package ec.sigec.campo.sync

/**
 * La cédula ecuatoriana del cliente (RF-046), un tercio de un contrato.
 *
 * Los otros dos tercios son `backend/app/forms/identification.py` y
 * `web/src/forms/identification.ts`, y los tres ejecutan `forms/contract/identification-cases.json`.
 * El teléfono la valida sin red, al momento de escribirla: una cédula mal digitada que se descubre
 * en la oficina es un cliente al que hay que volver a buscar.
 *
 * Diez dígitos ASCII; provincia 01 a 24, o 30 para ecuatorianos registrados en el exterior; tercer
 * dígito menor que 6 (persona natural); verificador por módulo 10 con coeficientes 2,1,2,1,…
 * Sin normalizar espacios ni guiones: eso lo hace la pantalla, para que las tres plataformas no
 * discrepen en qué limpiar.
 */
object Cedula {
    private const val LENGTH = 10
    private const val ABROAD = 30
    private const val LAST_PROVINCE = 24
    private const val FIRST_PUBLIC_DIGIT = 6

    fun isValid(value: String): Boolean {
        // `Char.isDigit()` acepta dígitos de cualquier escritura; la cédula es solo ASCII.
        if (value.length != LENGTH || value.any { it !in '0'..'9' }) return false
        val digits = value.map { it - '0' }
        val province = digits[0] * 10 + digits[1]
        if (province !in 1..LAST_PROVINCE && province != ABROAD) return false
        if (digits[2] >= FIRST_PUBLIC_DIGIT) return false
        val total = (0 until LENGTH - 1).sumOf { index ->
            val product = digits[index] * (if (index % 2 == 0) 2 else 1)
            if (product > 9) product - 9 else product
        }
        return (10 - total % 10) % 10 == digits[LENGTH - 1]
    }
}
