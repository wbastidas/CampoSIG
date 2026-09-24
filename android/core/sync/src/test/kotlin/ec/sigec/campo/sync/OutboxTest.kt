package ec.sigec.campo.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Tests for the outbox (RF-101 to RF-104).
 *
 * The outbox holds work that exists nowhere else until it reaches the server, so these tests
 * are written to attack the ways it could lose something rather than to confirm it works.
 */
class OutboxTest {

    private val now = 1_700_000_000_000L

    private fun op(
        id: String,
        kind: OperationKind = OperationKind.FORM_RESPONSE,
        workOrderId: String = "wo-1",
        createdAt: Long = now,
        sizeBytes: Long = 1024,
    ) = SyncOperation(
        id = id,
        kind = kind,
        workOrderId = workOrderId,
        createdAtMillis = createdAt,
        sizeBytes = sizeBytes,
    )

    // --- enqueue ------------------------------------------------------------------
    @Test
    fun `enqueue adds an operation`() {
        val outbox = Outbox.empty().enqueue(op("a"))
        assertEquals(1, outbox.size)
        assertNotNull(outbox.find("a"))
    }

    @Test
    fun `enqueuing the same id twice does not duplicate`() {
        // The capture layer may retry a local save after a crash; that must not produce two
        // entries for one photograph.
        val outbox = Outbox.empty().enqueue(op("a")).enqueue(op("a"))
        assertEquals(1, outbox.size)
    }

    @Test
    fun `outbox is immutable`() {
        val original = Outbox.empty().enqueue(op("a"))
        original.enqueue(op("b"))
        assertEquals(1, original.size, "enqueue no debe mutar el outbox original")
    }

    // --- priority order (RF-103) ---------------------------------------------------
    @Test
    fun `state changes are sent before photographs`() {
        // On a slow link a supervisor must learn the crew closed the order before the photos
        // arrive, because the state is what unblocks the next step.
        val outbox = Outbox.of(
            listOf(
                op("photo", OperationKind.PHOTO_FULL),
                op("state", OperationKind.WORK_ORDER_TRANSITION),
            ),
        )
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED)
        assertEquals(listOf("state", "photo"), batch.operations.map { it.id })
    }

    @Test
    fun `full priority order is respected`() {
        val outbox = Outbox.of(
            listOf(
                op("training", OperationKind.TRAINING_SAMPLE),
                op("audio", OperationKind.AUDIO),
                op("full", OperationKind.PHOTO_FULL),
                op("thumb", OperationKind.PHOTO_THUMBNAIL),
                op("form", OperationKind.FORM_RESPONSE),
            ),
        )
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED)
        assertEquals(listOf("form", "thumb", "full", "audio", "training"), batch.operations.map { it.id })
    }

    @Test
    fun `within a priority band the oldest goes first`() {
        val outbox = Outbox.of(
            listOf(
                op("later", OperationKind.PHOTO_FULL, createdAt = now + 5_000),
                op("earlier", OperationKind.PHOTO_FULL, createdAt = now),
            ),
        )
        val batch = outbox.nextBatch(now + 10_000, NetworkQuality.UNMETERED)
        assertEquals(listOf("earlier", "later"), batch.operations.map { it.id })
    }

    // --- network constraints -------------------------------------------------------
    @Test
    fun `nothing is attempted without a network`() {
        val outbox = Outbox.of(listOf(op("a")))
        val batch = outbox.nextBatch(now, NetworkQuality.NONE)
        assertTrue(batch.isEmpty)
        assertEquals(BatchReason.NOTHING_READY, batch.reason)
    }

    @Test
    fun `a constrained link carries state and thumbnails only`() {
        val outbox = Outbox.of(
            listOf(
                op("form", OperationKind.FORM_RESPONSE),
                op("thumb", OperationKind.PHOTO_THUMBNAIL),
                op("full", OperationKind.PHOTO_FULL),
                op("training", OperationKind.TRAINING_SAMPLE),
            ),
        )
        val batch = outbox.nextBatch(now, NetworkQuality.CONSTRAINED)
        assertEquals(listOf("form", "thumb"), batch.operations.map { it.id })
    }

    @Test
    fun `training data never spends metered data`() {
        val outbox = Outbox.of(listOf(op("training", OperationKind.TRAINING_SAMPLE)))
        assertTrue(outbox.nextBatch(now, NetworkQuality.CONSTRAINED).isEmpty)
        assertFalse(outbox.nextBatch(now, NetworkQuality.UNMETERED).isEmpty)
    }

    // --- batch limits --------------------------------------------------------------
    @Test
    fun `batch respects the count limit`() {
        val outbox = Outbox.of((1..10).map { op("op-$it") })
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED, maxOperations = 3)
        assertEquals(3, batch.operations.size)
        assertEquals(BatchReason.COUNT_LIMIT, batch.reason)
    }

    @Test
    fun `batch respects the transfer budget`() {
        val outbox = Outbox.of((1..5).map { op("op-$it", sizeBytes = 1000) })
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED, maxBytes = 2500)
        assertEquals(2, batch.operations.size)
        assertEquals(BatchReason.SIZE_LIMIT, batch.reason)
        assertTrue(batch.totalBytes <= 2500)
    }

    @Test
    fun `an oversized payload still goes, alone`() {
        // Otherwise one huge photograph would block everything queued behind it forever.
        val outbox = Outbox.of(listOf(op("huge", sizeBytes = 50_000_000)))
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED, maxBytes = 1000)
        assertEquals(listOf("huge"), batch.operations.map { it.id })
    }

    @Test
    fun `reason says everything fitted`() {
        val outbox = Outbox.of(listOf(op("a"), op("b")))
        assertEquals(BatchReason.ALL_READY, outbox.nextBatch(now, NetworkQuality.UNMETERED).reason)
    }

    // --- delivery outcomes ---------------------------------------------------------
    @Test
    fun `acknowledged operations leave the outbox`() {
        val outbox = Outbox.of(listOf(op("a"), op("b"))).acknowledge(listOf("a"))
        assertEquals(1, outbox.size)
        assertNull(outbox.find("a"))
    }

    @Test
    fun `acknowledging an unknown id is harmless`() {
        // It means an earlier reply was lost and the server is confirming a cleared delivery.
        val outbox = Outbox.of(listOf(op("a"))).acknowledge(listOf("desconocido"))
        assertEquals(1, outbox.size)
    }

    @Test
    fun `in-flight operations are not picked again`() {
        val outbox = Outbox.of(listOf(op("a"), op("b"))).markInFlight(listOf("a"))
        val batch = outbox.nextBatch(now, NetworkQuality.UNMETERED)
        assertEquals(listOf("b"), batch.operations.map { it.id })
    }

    @Test
    fun `a retryable failure returns to pending with a backoff`() {
        val outbox = Outbox.of(listOf(op("a"))).retryLater(listOf("a"), now, "timeout")
        val operation = assertNotNull(outbox.find("a"))
        assertEquals(OperationState.PENDING, operation.state)
        assertEquals(1, operation.attempts)
        assertTrue(operation.notBeforeMillis > now, "debe esperar antes de reintentar")
        assertEquals("timeout", operation.lastError)
    }

    @Test
    fun `an operation in backoff is not attempted early`() {
        val outbox = Outbox.of(listOf(op("a"))).retryLater(listOf("a"), now, "timeout")
        assertTrue(outbox.nextBatch(now + 1000, NetworkQuality.UNMETERED).isEmpty)
        val later = assertNotNull(outbox.find("a")).notBeforeMillis
        assertFalse(outbox.nextBatch(later, NetworkQuality.UNMETERED).isEmpty)
    }

    @Test
    fun `nothing is ever discarded when retries run out`() {
        // The core promise: a technician's work is not ours to throw away.
        val policy = RetryPolicy(maxAttempts = 2)
        var outbox = Outbox.of(listOf(op("a")), policy)
        repeat(3) { outbox = outbox.retryLater(listOf("a"), now, "sin señal") }
        val operation = assertNotNull(outbox.find("a"))
        assertEquals(OperationState.PARKED, operation.state)
        assertEquals(1, outbox.parked().size)
    }

    @Test
    fun `a rejected payload parks immediately without burning the budget`() {
        val outbox = Outbox.of(listOf(op("a"))).park(listOf("a"), "esquema inválido")
        val operation = assertNotNull(outbox.find("a"))
        assertEquals(OperationState.PARKED, operation.state)
        assertEquals(0, operation.attempts, "un rechazo de contenido no consume reintentos")
    }

    @Test
    fun `parked operations are not attempted`() {
        val outbox = Outbox.of(listOf(op("a"))).park(listOf("a"), "rechazado")
        assertTrue(outbox.nextBatch(now, NetworkQuality.UNMETERED).isEmpty)
    }

    @Test
    fun `a human can requeue a parked operation`() {
        val outbox = Outbox.of(listOf(op("a")))
            .park(listOf("a"), "rechazado")
            .requeue(listOf("a"))
        val operation = assertNotNull(outbox.find("a"))
        assertEquals(OperationState.PENDING, operation.state)
        assertEquals(0, operation.attempts)
        assertNull(operation.lastError)
    }

    @Test
    fun `requeue leaves non-parked operations alone`() {
        val outbox = Outbox.of(listOf(op("a"))).requeue(listOf("a"))
        assertEquals(OperationState.PENDING, assertNotNull(outbox.find("a")).state)
    }

    // --- RF-322: release only when everything arrived ------------------------------
    @Test
    fun `a work order with pending data is not fully delivered`() {
        val outbox = Outbox.of(listOf(op("a", workOrderId = "wo-1")))
        assertFalse(outbox.isFullyDelivered("wo-1"))
    }

    @Test
    fun `a work order becomes fully delivered once acknowledged`() {
        val outbox = Outbox.of(listOf(op("a", workOrderId = "wo-1"))).acknowledge(listOf("a"))
        assertTrue(outbox.isFullyDelivered("wo-1"))
    }

    @Test
    fun `parked data still counts as undelivered`() {
        // Parked means a human must act, not that the data is gone. Releasing the work order
        // here would lose it.
        val outbox = Outbox.of(listOf(op("a", workOrderId = "wo-1"))).park(listOf("a"), "x")
        assertFalse(outbox.isFullyDelivered("wo-1"))
    }

    @Test
    fun `one work order's pending data does not block another`() {
        val outbox = Outbox.of(listOf(op("a", workOrderId = "wo-1")))
        assertTrue(outbox.isFullyDelivered("wo-2"))
    }

    @Test
    fun `pendingFor lists what a handover would still owe`() {
        val outbox = Outbox.of(
            listOf(
                op("a", workOrderId = "wo-1"),
                op("b", workOrderId = "wo-1"),
                op("c", workOrderId = "wo-2"),
            ),
        )
        assertEquals(2, outbox.pendingFor("wo-1").size)
    }

    // --- counts --------------------------------------------------------------------
    @Test
    fun `countByState reports the sync indicator's numbers`() {
        val outbox = Outbox.of(listOf(op("a"), op("b"), op("c")))
            .markInFlight(listOf("a"))
            .park(listOf("b"), "rechazado")
        assertEquals(1, outbox.countByState(OperationState.PENDING))
        assertEquals(1, outbox.countByState(OperationState.IN_FLIGHT))
        assertEquals(1, outbox.countByState(OperationState.PARKED))
    }
}
