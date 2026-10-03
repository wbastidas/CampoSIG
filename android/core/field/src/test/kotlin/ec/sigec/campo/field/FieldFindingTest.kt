package ec.sigec.campo.field

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/** RF-049: «genera una propuesta de OT con GPS y fotos», validated offline like the server does. */
class FieldFindingTest {
    private val photo = FindingPhoto("GYE/evidencia/foto/h.jpg", "c".repeat(64), 1_790_000_000_000L)

    @Test
    fun `rf 049 a complete draft becomes the field_finding payload`() {
        val draft = FieldFindingDraft("cruceta_rota", -2.18, -79.91, listOf(photo), assetCode = "P-1")
        assertEquals(emptyList(), draft.problems())
        val payload = draft.payload()
        assertEquals("cruceta_rota", payload["defect_code"])
        assertEquals("P-1", payload["asset_code"])
        @Suppress("UNCHECKED_CAST")
        val photos = payload["photos"] as List<Map<String, Any?>>
        assertEquals("c".repeat(64), photos.single()["content_hash"])
        assertEquals("2026-09-21T14:13:20Z", photos.single()["captured_at"])
        assertTrue(draft.localId.startsWith("hallazgo:"))
    }

    @Test
    fun `the same three things the server refuses are said here, in order`() {
        val draft = FieldFindingDraft(" ", 0.0, 0.0, listOf(FindingPhoto("k", "corto")))
        assertEquals(
            listOf("Indique qué defecto encontró", "Espere a tener una posición GPS válida", "Tome al menos una foto del hallazgo"),
            draft.problems(),
        )
        assertFailsWith<IllegalStateException> { draft.payload() }
        assertEquals(listOf("Espere a tener una posición GPS válida"), FieldFindingDraft("x", null, -79.0, listOf(photo)).problems())
    }
}
