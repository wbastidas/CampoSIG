package ec.sigec.campo.field

import ec.sigec.campo.sync.NetworkQuality
import ec.sigec.campo.sync.OperationKind
import ec.sigec.campo.sync.Outbox
import ec.sigec.campo.sync.RetryPolicy
import ec.sigec.campo.sync.SyncOperation
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class UploadsTest {
    private val now = 1_790_000_000_000L
    private val mb = 1024L * 1024

    private fun capture(policy: SendPolicy = SendPolicy()): Outbox =
        policy.enqueueCapture(Outbox.empty(), "foto-1", "ot-1", now, thumbnailBytes = 40_000, fullBytes = 4 * mb)

    @Test
    fun `rf 076 on mobile data with wifi-only, the thumbnail goes and the full photo waits`() {
        val policy = SendPolicy(uploadOnMetered = false)
        val batch = capture(policy).nextBatch(now, NetworkQuality.CONSTRAINED, admits = policy.admits(NetworkQuality.CONSTRAINED, 0))
        assertEquals(listOf("foto-1:miniatura"), batch.operations.map { it.id })
    }

    @Test
    fun `rf 076 an area that allows mobile data sends the full photo, under its daily cap`() {
        val policy = SendPolicy(uploadOnMetered = true, meteredLimitMb = 10)
        val sent = capture(policy).nextBatch(now, NetworkQuality.CONSTRAINED, admits = policy.admits(NetworkQuality.CONSTRAINED, 0))
        assertEquals(listOf("foto-1:miniatura", "foto-1:completa"), sent.operations.map { it.id })
        val capped = capture(policy).nextBatch(now, NetworkQuality.CONSTRAINED, admits = policy.admits(NetworkQuality.CONSTRAINED, 8 * mb))
        assertEquals(listOf("foto-1:miniatura"), capped.operations.map { it.id })
    }

    @Test
    fun `on wifi everything goes, and training data never spends mobile data`() {
        val policy = SendPolicy(uploadOnMetered = true)
        val outbox = capture(policy).enqueue(SyncOperation("entrenamiento", OperationKind.TRAINING_SAMPLE, "ot-1", now, 1_000))
        val metered = outbox.nextBatch(now, NetworkQuality.CONSTRAINED, admits = policy.admits(NetworkQuality.CONSTRAINED, 0))
        assertTrue("entrenamiento" !in metered.operations.map { it.id })
        val wifi = outbox.nextBatch(now, NetworkQuality.UNMETERED, admits = policy.admits(NetworkQuality.UNMETERED, 0))
        assertEquals(3, wifi.operations.size)
    }

    @Test
    fun `the photo is downscaled off wifi when the policy asks`() {
        assertEquals(1280, SendPolicy(photoMaxEdgePx = 1600).targetEdgePx(NetworkQuality.CONSTRAINED))
        assertEquals(1600, SendPolicy(photoMaxEdgePx = 1600).targetEdgePx(NetworkQuality.UNMETERED))
        assertEquals(1600, SendPolicy(downscaleOnMetered = false).targetEdgePx(NetworkQuality.CONSTRAINED))
    }

    @Test
    fun `the send policy is read from the package manifest`() {
        val policy = SendPolicy.fromManifest(mapOf("upload_on_metered" to true, "metered_upload_limit_mb" to 50.0, "photo_max_edge_px" to 2048.0))
        assertEquals(SendPolicy(uploadOnMetered = true, meteredLimitMb = 50, photoMaxEdgePx = 2048), policy)
    }

    @Test
    fun `rf 104 cut at half, the resume plan starts where the storage says`() {
        val plan = ResumableUpload.plan(totalBytes = 20 * mb, partSize = 5 * mb, uploadedParts = setOf(1, 2))
        assertEquals(listOf(3, 4), plan.remaining.map { it.partNumber })
        assertEquals(10 * mb, plan.remaining.first().offset)
        assertEquals(50, plan.percent)
    }

    @Test
    fun `the last part is the remainder, and a part lost in the middle is redone alone`() {
        val plan = ResumableUpload.plan(totalBytes = 12 * mb, partSize = 5 * mb, uploadedParts = setOf(1, 3))
        assertEquals(listOf(PartRange(2, 5 * mb, 5 * mb)), plan.remaining)
        assertEquals(true, ResumableUpload.plan(12 * mb, 5 * mb, setOf(1, 2, 3)).complete)
        assertEquals(2 * mb, ResumableUpload.plan(12 * mb, 5 * mb, emptySet()).remaining.last().length)
    }

    @Test
    fun `rf 106 the badge puts errors first, then no network, then pending`() {
        val outbox = Outbox.empty().enqueueAll(
            listOf(SyncOperation("a", OperationKind.FORM_RESPONSE, "ot-1", now), SyncOperation("b", OperationKind.PHOTO_FULL, "ot-1", now)),
        )
        assertEquals(SyncBadge.PENDING, SyncStatus.of(outbox, NetworkQuality.UNMETERED, now - 60_000, now).badge)
        assertEquals(SyncBadge.OFFLINE, SyncStatus.of(outbox, NetworkQuality.NONE, now - 60_000, now).badge)
        val parked = outbox.park(listOf("b"), "rechazada")
        val indicator = SyncStatus.of(parked, NetworkQuality.NONE, now - 60_000, now)
        assertEquals(SyncBadge.ERRORS, indicator.badge)
        assertEquals("1 por enviar · 1 con error · sincronizado hace 1 min", indicator.detail)
        assertEquals(SyncBadge.UP_TO_DATE, SyncStatus.of(Outbox.empty(), NetworkQuality.UNMETERED, now, now).badge)
        assertEquals(SyncBadge.STALE, SyncStatus.of(Outbox.empty(), NetworkQuality.UNMETERED, null, now).badge)
    }

    @Test
    fun `rf 106 forcing a sync skips the backoff but not a parked operation`() {
        val outbox = Outbox.empty(RetryPolicy())
            .enqueueAll(listOf(SyncOperation("a", OperationKind.FORM_RESPONSE, "ot-1", now), SyncOperation("b", OperationKind.FORM_RESPONSE, "ot-1", now)))
            .retryLater(listOf("a"), now, "sin señal")
            .park(listOf("b"), "rechazada")
        assertTrue(outbox.nextBatch(now, NetworkQuality.UNMETERED).operations.isEmpty())
        val forced = SyncStatus.force(outbox)
        assertEquals(listOf("a"), forced.nextBatch(now, NetworkQuality.UNMETERED).operations.map { it.id })
    }
}
