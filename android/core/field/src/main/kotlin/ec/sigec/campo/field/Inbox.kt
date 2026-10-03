package ec.sigec.campo.field

import ec.sigec.campo.sync.OperationState
import ec.sigec.campo.sync.Outbox
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The day's inbox (RF-040): «bandeja de OT del día con orden por prioridad y distancia, estados y
 * contador de pendientes de sincronizar. Lista navegable en modo avión.»
 *
 * Everything it needs is on the phone: the orders the last pull delivered, the outbox, and the last
 * GPS fix. Nothing here asks the network, which is what «navegable en modo avión» means.
 */
public data class GeoPoint(val latitude: Double, val longitude: Double)

public data class InboxItem(
    val workOrderId: String,
    val code: String?,
    val state: String,
    /** `critica`, `alta`, `media` or `baja`, as the server sends it. */
    val priority: String,
    val location: GeoPoint?,
    val slaDueMillis: Long? = null,
)

public data class InboxRow(
    val item: InboxItem,
    /** Straight-line distance from the last fix; null without a fix or without a location. */
    val distanceMeters: Double?,
    /** Operations for this order still waiting to reach the server. */
    val pendingUploads: Int,
    val overdue: Boolean,
)

public data class DayInbox(val rows: List<InboxRow>, val pendingUploads: Int, val parked: Int)

public object InboxOrdering {
    private val PRIORITY_RANK = mapOf("critica" to 0, "alta" to 1, "media" to 2, "baja" to 3)

    /** States that leave the day's list: the field's part is done, or the office took it back. */
    private val OFF_THE_LIST = setOf("cerrada_campo", "sincronizada", "en_revision", "aprobada", "cerrada", "anulada")

    /**
     * Priority first, then the nearest. Within the same priority an overdue order goes before an
     * on-time one, and a tie on everything falls back to the code so the list does not reshuffle
     * between two refreshes — a list that moves under the technician's thumb is a wrong tap.
     */
    public fun build(items: List<InboxItem>, outbox: Outbox, here: GeoPoint?, nowMillis: Long): DayInbox {
        // Acknowledged operations leave the outbox, so what is in it is, by definition, pending.
        val pending = outbox.operations()
        val perOrder = pending.groupingBy { it.workOrderId }.eachCount()
        val rows = items
            .filter { it.state !in OFF_THE_LIST }
            .map { item ->
                InboxRow(
                    item = item,
                    distanceMeters = if (here != null && item.location != null) distanceMeters(here, item.location) else null,
                    pendingUploads = perOrder[item.workOrderId] ?: 0,
                    overdue = item.slaDueMillis != null && item.slaDueMillis < nowMillis,
                )
            }
            .sortedWith(
                compareBy<InboxRow> { PRIORITY_RANK[it.item.priority] ?: PRIORITY_RANK.size }
                    .thenBy { if (it.overdue) 0 else 1 }
                    .thenBy { it.distanceMeters ?: Double.MAX_VALUE }
                    .thenBy { it.item.code ?: it.item.workOrderId },
            )
        return DayInbox(
            rows = rows,
            pendingUploads = pending.size,
            parked = outbox.countByState(OperationState.PARKED),
        )
    }

    /** Haversine, which is plenty at the scale of a concession: the error is metres, not streets. */
    public fun distanceMeters(a: GeoPoint, b: GeoPoint): Double {
        val radius = 6_371_000.0
        val dLat = Math.toRadians(b.latitude - a.latitude)
        val dLon = Math.toRadians(b.longitude - a.longitude)
        val h = sin(dLat / 2).pow(2) +
            cos(Math.toRadians(a.latitude)) * cos(Math.toRadians(b.latitude)) * sin(dLon / 2).pow(2)
        return 2 * radius * asin(sqrt(h))
    }
}
