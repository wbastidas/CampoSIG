package ec.sigec.campo.sync

import com.google.gson.Gson
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * El corpus de cédulas (RF-046), en el módulo del móvil. Los otros dos tercios del contrato están
 * en `backend/tests/unit/test_rf046_cedula_contract.py` y `web/src/forms/identification.test.ts`.
 */
class CedulaTest {
    private data class Case(val id: String, val value: String, val valid: Boolean, val why: String? = null)

    private data class Corpus(val cases: List<Case>)

    private val corpus: Corpus by lazy {
        val root = File(System.getProperty("user.dir")).parentFile.parentFile.parentFile
        Gson().fromJson(
            File(root, "forms/contract/identification-cases.json").readText(),
            Corpus::class.java,
        )
    }

    @Test
    fun `rf 046 el movil cumple el corpus de cedulas`() {
        val wrong = corpus.cases.filter { Cedula.isValid(it.value) != it.valid }.map { it.id }
        assertEquals(emptyList(), wrong)
    }

    @Test
    fun `el corpus esta sano`() {
        val ids = corpus.cases.map { it.id }
        assertEquals(ids.size, ids.toSet().size, "hay ids repetidos")
        assertTrue(corpus.cases.count { it.valid } >= 5)
        assertTrue(corpus.cases.count { !it.valid } >= 10)
    }
}
