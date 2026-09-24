package ec.sigec.campo.sync

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * El corpus común de validación condicional, en el módulo del móvil (I5, SRS 7.2).
 *
 * Un tercio de un contrato. Los otros dos están en
 * `backend/tests/unit/test_i5_shared_validation_contract.py` y en `web/src/forms/rules.test.ts`,
 * y los tres ejecutan el **mismo** `forms/contract/validation-cases.json`.
 *
 * Escribir el mismo algoritmo tres veces no produce acuerdo: produce tres algoritmos que
 * coinciden en los casos que a alguien se le ocurrieron. Lo que produce acuerdo es el corpus, y
 * que falle cuando una implementación se desvía.
 *
 * Corre en la JVM sin SDK, emulador ni dispositivo, que es la razón de que esta decisión viva en
 * `core:sync` y no en la capa Android (ADR-010).
 */
class FormRulesTest {
    private data class Case(
        val id: String,
        val why: String? = null,
        val rules: List<Any?> = emptyList(),
        val answers: Map<String, Any?> = emptyMap(),
        val expect: List<String> = emptyList(),
    )

    private data class Corpus(val version: Int, val cases: List<Case>)

    private val corpus: Corpus by lazy {
        // Desde el directorio del módulo hasta la raíz del monorepo. El corpus es un archivo
        // versionado, no un recurso empaquetado: las tres plataformas leen el mismo.
        val root = File(System.getProperty("user.dir")).parentFile.parentFile.parentFile
        val file = File(root, "forms/contract/validation-cases.json")
        assertTrue(file.exists(), "no se encontró el corpus compartido en ${file.absolutePath}")
        Gson().fromJson(file.readText(), object : TypeToken<Corpus>() {}.type)
    }

    @Test
    fun `el modulo del movil cumple el contrato compartido`() {
        val disagreements = mutableListOf<String>()
        for (case in corpus.cases) {
            val got = missingRequirements(case.rules, case.answers).map { it.field }
            if (got != case.expect) {
                disagreements += "${case.id}: esperado ${case.expect}, obtenido $got" +
                    (case.why?.let { " — $it" } ?: "")
            }
        }
        assertEquals(emptyList(), disagreements, "el móvil se desvía del contrato compartido")
    }

    @Test
    fun `el corpus esta sano`() {
        // Un corpus con ids repetidos o casos vacíos es un corpus que no compara nada.
        val ids = corpus.cases.map { it.id }
        assertEquals(ids.size, ids.toSet().size, "hay ids repetidos en el corpus")
        assertTrue(corpus.cases.size >= 25, "el corpus se quedó corto; el contrato deja de cubrir")
    }

    @Test
    fun `el corpus distingue la implementacion ingenua de la correcta`() {
        // Un corpus que cualquier implementación razonable pasa no mide nada. La ingenua trata el
        // cero y el falso como ausencia, que es exactamente lo que se escribe de primera
        // intención con un `if (value == null || value == "")`.
        fun naive(rules: List<Any?>, answers: Map<String, Any?>): List<String> {
            val problems = mutableListOf<String>()
            for (rule in rules) {
                val map = rule as? Map<*, *> ?: continue
                val when0 = map["when"] as? Map<*, *> ?: continue
                val operands = when0["=="] as? List<*> ?: continue
                fun read(token: Any?): Any? =
                    if (token is Map<*, *> && token.containsKey("var")) answers[token["var"]] else token
                if (read(operands[0]) != read(operands[1])) continue
                for (field in map["require"] as? List<*> ?: emptyList<Any?>()) {
                    val value = answers[field.toString()]
                    if (value == null || value == "" || value == 0.0 || value == false) {
                        problems += field.toString()
                    }
                }
            }
            return problems
        }

        val disagreements = corpus.cases.filter {
            naive(it.rules, it.answers) != it.expect
        }
        assertTrue(
            disagreements.isNotEmpty(),
            "el corpus no distingue una implementación ingenua de la correcta",
        )
    }

    // --- lo que el corpus no puede expresar -----------------------------------------
    @Test
    fun `el mensaje de la regla viaja con el campo y hay uno por defecto`() {
        val rules = listOf(
            mapOf(
                "when" to mapOf("==" to listOf(mapOf("var" to "final_state"), "no_resuelto")),
                "require" to listOf("cause"),
                "message" to "Indique la causa cuando el trabajo no quedó resuelto",
            ),
            mapOf(
                "when" to mapOf("==" to listOf(mapOf("var" to "stage"), "cierre")),
                "require" to listOf("signposted"),
            ),
        )
        val answers = mapOf<String, Any?>("final_state" to "no_resuelto", "stage" to "cierre")
        assertEquals(
            listOf(
                "Indique la causa cuando el trabajo no quedó resuelto",
                "signposted: es obligatorio en este caso",
            ),
            requirementMessages(rules, answers),
        )
    }

    @Test
    fun `que cuenta como respuesta`() {
        assertTrue(isAnswered(0))
        assertTrue(isAnswered(0.0))
        assertTrue(isAnswered(false))
        assertTrue(isAnswered(true))
        assertTrue(isAnswered("x"))
        assertTrue(isAnswered(listOf(1)))
        assertTrue(isAnswered(mapOf("a" to 1)))
        assertFalse(isAnswered(null))
        assertFalse(isAnswered(""))
        assertFalse(isAnswered("   "))
        assertFalse(isAnswered(emptyList<Any>()))
        assertFalse(isAnswered(emptyMap<String, Any>()))
    }

    @Test
    fun `un booleano no se compara igual a cero ni a uno`() {
        assertFalse(
            evaluateCondition(
                mapOf("==" to listOf(mapOf("var" to "signposted"), 1)),
                mapOf("signposted" to true),
            ),
        )
        assertFalse(
            evaluateCondition(
                mapOf("==" to listOf(mapOf("var" to "count"), false)),
                mapOf("count" to 0),
            ),
        )
    }

    @Test
    fun `un entero del catalogo y un decimal de la red se comparan iguales`() {
        // La única coerción que el contrato sí quiere: el JSON de la red trae 11.0 donde la regla
        // escribió 11, y eso es el mismo valor.
        assertTrue(
            evaluateCondition(
                mapOf("==" to listOf(mapOf("var" to "height_m"), 11)),
                mapOf("height_m" to 11.0),
            ),
        )
    }

    @Test
    fun `una lista de reglas corrupta no revienta`() {
        // El catálogo llega por la red y se guarda en la base local; un payload raro no puede
        // dejar a la cuadrilla sin poder enviar el día de trabajo.
        assertEquals(emptyList(), missingRequirements(null, emptyMap()))
        assertEquals(emptyList(), missingRequirements(listOf(null, 3, "x"), emptyMap()))
    }
}
