package ec.sigec.campo.field

import java.time.Instant
import java.util.UUID

/**
 * A finding reported from the field with no work order behind it (RF-049): «genera una propuesta de
 * OT con GPS y fotos (RF-013)». Validated here, offline, with the same rules the server applies to
 * the `field_finding` operation, so the technician learns now — not tomorrow — that the photograph
 * is missing.
 */
public data class FindingPhoto(val storageKey: String, val contentHash: String, val capturedAtMillis: Long? = null)

public data class FieldFindingDraft(
    val defectCode: String,
    val latitude: Double?,
    val longitude: Double?,
    val photos: List<FindingPhoto>,
    val accuracyMeters: Double? = null,
    val assetCode: String? = null,
    val assetTypeKey: String? = null,
    val feederCode: String? = null,
    val description: String? = null,
    val observedAtMillis: Long? = null,
    /** The outbox groups by this, since there is no work order to group by (`OperationKind.FIELD_FINDING`). */
    val localId: String = "hallazgo:${UUID.randomUUID()}",
) {
    /** What is still missing, in the order the screen asks for it. Empty when it can be sent. */
    public fun problems(): List<String> = buildList {
        if (defectCode.isBlank()) add("Indique qué defecto encontró")
        val lat = latitude
        val lon = longitude
        if (lat == null || lon == null || lat !in -90.0..90.0 || lon !in -180.0..180.0 || (lat == 0.0 && lon == 0.0)) {
            add("Espere a tener una posición GPS válida")
        }
        if (photos.none { it.storageKey.isNotBlank() && it.contentHash.length == 64 }) {
            add("Tome al menos una foto del hallazgo")
        }
    }

    /** The `field_finding` operation's payload, as the server reads it. */
    public fun payload(): Map<String, Any?> {
        check(problems().isEmpty()) { problems().joinToString("; ") }
        return buildMap {
            put("defect_code", defectCode)
            put("latitude", latitude)
            put("longitude", longitude)
            accuracyMeters?.let { put("accuracy_m", it) }
            assetCode?.let { put("asset_code", it) }
            assetTypeKey?.let { put("asset_type_key", it) }
            feederCode?.let { put("feeder_code", it) }
            description?.let { put("description", it) }
            observedAtMillis?.let { put("observed_at", Instant.ofEpochMilli(it).toString()) }
            put(
                "photos",
                photos.map { photo ->
                    buildMap {
                        put("storage_key", photo.storageKey)
                        put("content_hash", photo.contentHash)
                        photo.capturedAtMillis?.let { put("captured_at", Instant.ofEpochMilli(it).toString()) }
                    }
                },
            )
        }
    }
}
