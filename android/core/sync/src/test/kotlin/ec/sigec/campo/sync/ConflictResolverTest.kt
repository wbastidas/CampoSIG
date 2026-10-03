package ec.sigec.campo.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for conflict resolution (RF-105, RF-322).
 *
 * The scenario these protect: a technician works offline all afternoon while a planner
 * reassigns the work order. The one outcome that must never happen is losing the capture, so
 * every test here also asserts `keepsLocalCapture`.
 */
class ConflictResolverTest {

    private fun local(
        state: String = "en_ejecucion",
        assignedTo: String? = "tecnico.a",
        hasCapture: Boolean = true,
        baseVersion: Int = 3,
    ) = LocalWorkOrderState("wo-1", state, assignedTo, hasCapture, baseVersion)

    private fun server(
        state: String = "en_ejecucion",
        assignedTo: String? = "tecnico.a",
        version: Int = 3,
    ) = ServerWorkOrderState("wo-1", state, assignedTo, version)

    // --- agreement -----------------------------------------------------------------
    @Test
    fun `no conflict when the server has not moved`() {
        assertTrue(ConflictResolver.resolve(local(), server()).isEmpty())
    }

    @Test
    fun `comparing different work orders is a programming error`() {
        assertFailsWith<IllegalArgumentException> {
            ConflictResolver.resolve(
                local(),
                ServerWorkOrderState("wo-2", "en_ejecucion", "tecnico.a", 4),
            )
        }
    }

    // --- reassignment (RF-321, RF-322) ---------------------------------------------
    @Test
    fun `reassignment is the server's call but the capture survives`() {
        val resolutions = ConflictResolver.resolve(
            local(assignedTo = "tecnico.a", hasCapture = true),
            server(assignedTo = "tecnico.b", version = 4),
        )
        val reassignment = assertNotNull(
            resolutions.find { it.kind == ConflictKind.REASSIGNED_WHILE_HELD },
        )
        assertEquals(Authority.SERVER, reassignment.authority)
        assertTrue(reassignment.keepsLocalCapture, "jamás se descarta lo capturado")
        assertTrue(reassignment.requiresUpload, "hay que subirlo antes de liberar la OT")
    }

    @Test
    fun `reassignment without local capture needs no upload`() {
        val resolutions = ConflictResolver.resolve(
            local(assignedTo = "tecnico.a", hasCapture = false),
            server(assignedTo = "tecnico.b", version = 4),
        )
        val reassignment = assertNotNull(resolutions.firstOrNull())
        assertFalse(reassignment.requiresUpload)
    }

    @Test
    fun `the message tells the technician what will happen to their work`() {
        val resolutions = ConflictResolver.resolve(
            local(hasCapture = true),
            server(assignedTo = "tecnico.b", version = 4),
        )
        assertTrue(
            resolutions.first().message.contains("subirá"),
            "el mensaje debe decir que lo capturado se sube, no solo que perdió la OT",
        )
    }

    // --- administrative state ------------------------------------------------------
    @Test
    fun `an administrative state change is the server's call`() {
        val resolutions = ConflictResolver.resolve(
            local(state = "asignada", hasCapture = false, baseVersion = 3),
            server(state = "devuelta", version = 4),
        )
        val change = assertNotNull(
            resolutions.find { it.kind == ConflictKind.ADMIN_STATE_CHANGED },
        )
        assertEquals(Authority.SERVER, change.authority)
        assertTrue(change.keepsLocalCapture)
    }

    // --- the genuinely hard case ---------------------------------------------------
    @Test
    fun `work done in the field on a cancelled order goes to a supervisor`() {
        // Both sides acted: the office cancelled work the crew had already carried out.
        // Neither can decide alone, and discarding the capture is not an option.
        val resolutions = ConflictResolver.resolve(
            local(state = "cerrada_campo", hasCapture = true),
            server(state = "anulada", version = 5),
        )
        val conflict = assertNotNull(
            resolutions.find { it.kind == ConflictKind.CLOSED_BUT_CANCELLED },
        )
        assertEquals(Authority.SUPERVISOR, conflict.authority)
        assertTrue(conflict.keepsLocalCapture)
        assertTrue(conflict.requiresUpload)
    }

    @Test
    fun `a cancellation before any field work is simply the server's call`() {
        val resolutions = ConflictResolver.resolve(
            local(state = "asignada", hasCapture = false),
            server(state = "anulada", version = 5),
        )
        assertTrue(resolutions.none { it.kind == ConflictKind.CLOSED_BUT_CANCELLED })
        assertEquals(Authority.SERVER, resolutions.first().authority)
    }

    @Test
    fun `reassignment and cancellation are reported together`() {
        // Both happened; the technician needs to know both, not whichever we checked first.
        val resolutions = ConflictResolver.resolve(
            local(state = "cerrada_campo", assignedTo = "tecnico.a", hasCapture = true),
            server(state = "anulada", assignedTo = "tecnico.b", version = 6),
        )
        val kinds = resolutions.map { it.kind }
        assertTrue(ConflictKind.REASSIGNED_WHILE_HELD in kinds)
        assertTrue(ConflictKind.CLOSED_BUT_CANCELLED in kinds)
    }

    @Test
    fun `every resolution keeps the local capture`() {
        // The invariant, asserted across the whole matrix rather than case by case.
        val states = listOf("asignada", "en_camino", "en_sitio", "en_ejecucion", "cerrada_campo")
        val serverStates = listOf("devuelta", "anulada", "cerrada", "en_revision")
        for (localState in states) {
            for (serverState in serverStates) {
                for (reassigned in listOf(true, false)) {
                    val resolutions = ConflictResolver.resolve(
                        local(state = localState, hasCapture = true),
                        server(
                            state = serverState,
                            assignedTo = if (reassigned) "tecnico.b" else "tecnico.a",
                            version = 9,
                        ),
                    )
                    assertTrue(
                        resolutions.all { it.keepsLocalCapture },
                        "perdió lo capturado con local=$localState servidor=$serverState",
                    )
                }
            }
        }
    }

    // --- release gate (RF-322) -----------------------------------------------------
    @Test
    fun `a work order may not be released while data is pending`() {
        val outbox = Outbox.of(
            listOf(
                SyncOperation("a", OperationKind.FORM_RESPONSE, "wo-1", 0),
            ),
        )
        assertFalse(ConflictResolver.mayRelease(outbox, "wo-1"))
    }

    @Test
    fun `a work order may be released once everything arrived`() {
        val outbox = Outbox.of(
            listOf(SyncOperation("a", OperationKind.FORM_RESPONSE, "wo-1", 0)),
        ).acknowledge(listOf("a"))
        assertTrue(ConflictResolver.mayRelease(outbox, "wo-1"))
    }

    @Test
    fun `parked data also blocks release`() {
        val outbox = Outbox.of(
            listOf(SyncOperation("a", OperationKind.FORM_RESPONSE, "wo-1", 0)),
        ).park(listOf("a"), "rechazado")
        assertFalse(
            ConflictResolver.mayRelease(outbox, "wo-1"),
            "aparcado significa que un humano debe actuar, no que el dato desapareció",
        )
    }

    // --- field level ---------------------------------------------------------------
    @Test
    fun `no conflict when only one side changed a field`() {
        assertNull(
            ConflictResolver.resolveField("material", deviceChanged = true, serverChanged = false, serverReviewedByHuman = false),
        )
        assertNull(
            ConflictResolver.resolveField("material", deviceChanged = false, serverChanged = true, serverReviewedByHuman = false),
        )
    }

    @Test
    fun `the device wins a field it captured`() {
        val resolution = assertNotNull(
            ConflictResolver.resolveField("material", deviceChanged = true, serverChanged = true, serverReviewedByHuman = false),
        )
        assertEquals(Authority.DEVICE, resolution.authority)
        assertTrue(resolution.requiresUpload)
    }

    @Test
    fun `a reviewer's correction is not overwritten by a stale local value`() {
        val resolution = assertNotNull(
            ConflictResolver.resolveField("material", deviceChanged = true, serverChanged = true, serverReviewedByHuman = true),
        )
        assertEquals(Authority.SUPERVISOR, resolution.authority)
        assertFalse(resolution.requiresUpload)
        // Kept as a proposal rather than discarded: the technician saw the pole, the reviewer
        // did not, and that disagreement is worth surfacing.
        assertTrue(resolution.keepsLocalCapture)
    }
}
