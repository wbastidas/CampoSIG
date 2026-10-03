package ec.sigec.campo.field

import ec.sigec.campo.sync.OperationKind
import ec.sigec.campo.sync.Outbox
import ec.sigec.campo.sync.SyncOperation
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** RF-040: «bandeja de OT del día con orden por prioridad y distancia, estados y contador de pendientes». */
class InboxTest {
    private val here = GeoPoint(-2.170, -79.900)
    private val now = 1_790_000_000_000L

    private fun item(id: String, priority: String, lat: Double, state: String = "descargada", sla: Long? = null) =
        InboxItem(id, "OT-$id", state, priority, GeoPoint(lat, -79.900), sla)

    @Test
    fun `rf 040 priority first, then the nearest`() {
        val rows = InboxOrdering.build(
            listOf(item("far-high", "alta", -2.300), item("near-low", "baja", -2.171), item("near-high", "alta", -2.172)),
            Outbox.empty(),
            here,
            now,
        ).rows
        assertEquals(listOf("near-high", "far-high", "near-low"), rows.map { it.item.workOrderId })
    }

    @Test
    fun `an overdue order goes before an on-time one of the same priority`() {
        val rows = InboxOrdering.build(
            listOf(item("near", "media", -2.171), item("late", "media", -2.300, sla = now - 1)),
            Outbox.empty(),
            here,
            now,
        ).rows
        assertEquals("late", rows.first().item.workOrderId)
        assertTrue(rows.first().overdue)
    }

    @Test
    fun `without a fix the order is still stable`() {
        val items = listOf(item("b", "media", -2.2), item("a", "media", -2.3))
        val first = InboxOrdering.build(items, Outbox.empty(), null, now).rows.map { it.item.code }
        val second = InboxOrdering.build(items.reversed(), Outbox.empty(), null, now).rows.map { it.item.code }
        assertEquals(listOf("OT-a", "OT-b"), first)
        assertEquals(first, second)
    }

    @Test
    fun `finished and office-held orders leave the day's list`() {
        val rows = InboxOrdering.build(
            listOf(item("open", "media", -2.2), item("done", "media", -2.2, state = "cerrada_campo"), item("x", "media", -2.2, state = "anulada")),
            Outbox.empty(),
            here,
            now,
        ).rows
        assertEquals(listOf("open"), rows.map { it.item.workOrderId })
    }

    @Test
    fun `the pending counter comes from the outbox, per order and in total`() {
        val outbox = Outbox.empty().enqueueAll(
            listOf(
                SyncOperation("1", OperationKind.FORM_RESPONSE, "open", now),
                SyncOperation("2", OperationKind.PHOTO_FULL, "open", now),
                SyncOperation("3", OperationKind.PHOTO_FULL, "other", now),
            ),
        ).park(listOf("3"), "rechazada")
        val inbox = InboxOrdering.build(listOf(item("open", "media", -2.2)), outbox, here, now)
        assertEquals(2, inbox.rows.single().pendingUploads)
        assertEquals(3, inbox.pendingUploads)
        assertEquals(1, inbox.parked)
    }

    @Test
    fun `distance is haversine and close to the truth`() {
        // One hundredth of a degree of latitude is about 1.11 km anywhere.
        val meters = InboxOrdering.distanceMeters(GeoPoint(-2.17, -79.9), GeoPoint(-2.18, -79.9))
        assertTrue(meters in 1100.0..1125.0, "$meters")
    }
}
