package ec.sigec.campo.field

import ec.sigec.campo.sync.NetworkQuality
import ec.sigec.campo.sync.OperationKind
import ec.sigec.campo.sync.OperationState
import ec.sigec.campo.sync.Outbox
import ec.sigec.campo.sync.SyncOperation
import ec.sigec.campo.sync.UploadPriority

/**
 * RF-076: «compresión y política de envío: miniatura inmediata, imagen completa al tener Wi-Fi o
 * datos según el parámetro. Con datos móviles y el parámetro "solo Wi-Fi", la imagen completa queda
 * en cola.»
 *
 * The parameter is the area's capture policy (RF-151): `upload_on_metered`, a daily cap
 * (`metered_upload_limit_mb`), and whether to downscale off Wi-Fi. The outbox's own rule holds full
 * photographs on any metered link; this lets an area that decided otherwise send them, under its cap.
 */
public data class SendPolicy(
    val uploadOnMetered: Boolean = false,
    /** Null: no cap. */
    val meteredLimitMb: Int? = null,
    val downscaleOnMetered: Boolean = true,
    val photoMaxEdgePx: Int = 1600,
    val photoQuality: Int = 80,
) {
    public companion object {
        /** The long edge a photograph is reduced to off Wi-Fi when the policy asks for it. */
        public const val METERED_EDGE_PX: Int = 1280

        public fun fromManifest(values: Map<String, Any?>): SendPolicy {
            val defaults = SendPolicy()
            return SendPolicy(
                uploadOnMetered = values["upload_on_metered"] as? Boolean ?: defaults.uploadOnMetered,
                meteredLimitMb = (values["metered_upload_limit_mb"] as? Number)?.toInt(),
                downscaleOnMetered = values["downscale_on_metered"] as? Boolean ?: defaults.downscaleOnMetered,
                photoMaxEdgePx = (values["photo_max_edge_px"] as? Number)?.toInt() ?: defaults.photoMaxEdgePx,
                photoQuality = (values["photo_quality"] as? Number)?.toInt() ?: defaults.photoQuality,
            )
        }
    }

    /**
     * The admission rule for [Outbox.nextBatch] on this connection, given what was already sent over
     * mobile data today. Training data never spends a technician's data, whatever the policy says.
     */
    public fun admits(network: NetworkQuality, meteredBytesToday: Long): (SyncOperation) -> Boolean = { operation ->
        val rank = operation.priority.rank
        when (network) {
            NetworkQuality.NONE -> false
            NetworkQuality.UNMETERED -> true
            NetworkQuality.CONSTRAINED -> when {
                rank <= UploadPriority.THUMBNAILS.rank -> true
                operation.priority == UploadPriority.TRAINING_DATA -> false
                !uploadOnMetered -> false
                meteredLimitMb == null -> true
                else -> meteredBytesToday + operation.sizeBytes <= meteredLimitMb.toLong() * 1024 * 1024
            }
        }
    }

    /** The long edge to encode a full photograph at, for this connection. */
    public fun targetEdgePx(network: NetworkQuality): Int =
        if (network == NetworkQuality.CONSTRAINED && downscaleOnMetered) minOf(photoMaxEdgePx, METERED_EDGE_PX) else photoMaxEdgePx

    /** What a capture enqueues: the thumbnail always, now; the full photograph to wait its turn. */
    public fun enqueueCapture(outbox: Outbox, id: String, workOrderId: String, nowMillis: Long, thumbnailBytes: Long, fullBytes: Long): Outbox =
        outbox.enqueueAll(
            listOf(
                SyncOperation("$id:miniatura", OperationKind.PHOTO_THUMBNAIL, workOrderId, nowMillis, thumbnailBytes),
                SyncOperation("$id:completa", OperationKind.PHOTO_FULL, workOrderId, nowMillis, fullBytes),
            ),
        )
}

/**
 * RF-104: «cortar la red al 50 % y reanudar no reinicia la subida desde cero.» The server opens an
 * upload by parts and, after a cut, says which parts the storage holds; this works out what is left
 * and which bytes of the file each remaining part is.
 */
public data class PartRange(val partNumber: Int, val offset: Long, val length: Long)

public data class ResumePlan(val remaining: List<PartRange>, val uploadedBytes: Long, val totalBytes: Long) {
    val percent: Int get() = if (totalBytes == 0L) 100 else (uploadedBytes * 100 / totalBytes).toInt()
    val complete: Boolean get() = remaining.isEmpty()
}

public object ResumableUpload {
    public fun plan(totalBytes: Long, partSize: Long, uploadedParts: Set<Int>): ResumePlan {
        require(totalBytes > 0 && partSize > 0) { "tamaños inválidos" }
        val count = ((totalBytes + partSize - 1) / partSize).toInt()
        val all = (1..count).map { number ->
            val offset = (number - 1) * partSize
            PartRange(number, offset, minOf(partSize, totalBytes - offset))
        }
        val done = all.filter { it.partNumber in uploadedParts }
        return ResumePlan(all.filter { it.partNumber !in uploadedParts }, done.sumOf { it.length }, totalBytes)
    }
}

/**
 * RF-106: «indicador de sincronización en la app (pendientes, último sync, errores) y "forzar sync".
 * Visible en todas las pantallas principales.» One state for the badge, so every screen shows the
 * same thing, worded for the technician.
 */
public enum class SyncBadge(public val label: String) {
    UP_TO_DATE("Al día"),
    PENDING("Pendiente de enviar"),
    ERRORS("Hay envíos que revisar"),
    OFFLINE("Sin conexión"),
    STALE("Hace mucho que no sincroniza"),
}

public data class SyncIndicator(
    val badge: SyncBadge,
    val pending: Int,
    val parked: Int,
    val minutesSinceSync: Long?,
    val detail: String,
)

public object SyncStatus {
    /** Past this, a phone that has not spoken to the server is worth a warning even if it holds nothing. */
    public const val STALE_AFTER_MINUTES: Long = 4 * 60

    public fun of(outbox: Outbox, network: NetworkQuality, lastSyncMillis: Long?, nowMillis: Long): SyncIndicator {
        val pending = outbox.operations().count { it.state != OperationState.PARKED }
        val parked = outbox.countByState(OperationState.PARKED)
        val minutes = lastSyncMillis?.let { (nowMillis - it) / 60_000 }
        // Errors first: a parked operation is captured work nobody has seen, and it never clears alone.
        val badge = when {
            parked > 0 -> SyncBadge.ERRORS
            network == NetworkQuality.NONE -> SyncBadge.OFFLINE
            minutes == null || minutes > STALE_AFTER_MINUTES -> SyncBadge.STALE
            pending > 0 -> SyncBadge.PENDING
            else -> SyncBadge.UP_TO_DATE
        }
        val since = when {
            minutes == null -> "nunca ha sincronizado"
            minutes < 1 -> "sincronizado hace menos de un minuto"
            minutes < 60 -> "sincronizado hace $minutes min"
            else -> "sincronizado hace ${minutes / 60} h"
        }
        val detail = buildList {
            if (pending > 0) add("$pending por enviar")
            if (parked > 0) add("$parked con error")
            add(since)
        }.joinToString(" · ")
        return SyncIndicator(badge, pending, parked, minutes, detail)
    }

    /** «Forzar sync»: what was waiting out a backoff goes now; parked operations wait for a person. */
    public fun force(outbox: Outbox): Outbox = outbox.expedite()
}
