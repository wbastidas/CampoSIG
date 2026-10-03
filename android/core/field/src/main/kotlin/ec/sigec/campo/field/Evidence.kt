package ec.sigec.campo.field

import java.io.InputStream
import java.security.MessageDigest
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs

/**
 * Evidence at the moment of capture (RF-071 to RF-075, RF-046).
 *
 * The Android layer owns the camera, the file and `ExifInterface`; this owns every decision about
 * them, so the decisions run in CI: the hash, whether a picture may count, whether it is too blurry,
 * which EXIF tags carry which value, and what the watermark says.
 */
public enum class EvidenceStage(public val wire: String) {
    BEFORE("antes"),
    DURING("durante"),
    AFTER("despues"),
    NOT_APPLICABLE("no_aplica"),
}

public enum class EvidenceSource(public val wire: String) {
    CAMERA("camara"),
    GALLERY("galeria"),
}

/** RF-073: SHA-256 of the original, at capture, before anything (watermark, resize) touches it. */
public object EvidenceHash {
    public fun of(bytes: ByteArray): String = hex(MessageDigest.getInstance("SHA-256").digest(bytes))

    /** Streaming, for a 12 MP photograph that should not be held in memory twice. */
    public fun of(stream: InputStream): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(64 * 1024)
        while (true) {
            val read = stream.read(buffer)
            if (read < 0) break
            digest.update(buffer, 0, read)
        }
        return hex(digest.digest())
    }

    private fun hex(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it) }
}

/**
 * RF-074: «bloqueo de fotos desde la galería para evidencias obligatorias (solo cámara en vivo); se
 * permite galería para adjuntos opcionales, marcados como "no verificados"».
 */
public object GalleryPolicy {
    private val MANDATORY_STAGES = setOf(EvidenceStage.BEFORE, EvidenceStage.AFTER)

    /** Whether the picker may offer the gallery at all for this slot. */
    public fun galleryAllowed(stage: EvidenceStage): Boolean = stage !in MANDATORY_STAGES

    /** Whether a captured item counts toward the BEFORE/AFTER minimums. Mirrors the server. */
    public fun countsAsEvidence(source: EvidenceSource, altered: Boolean = false): Boolean =
        source == EvidenceSource.CAMERA && !altered

    /** The label a gallery attachment carries everywhere it is shown. */
    public fun label(source: EvidenceSource): String? =
        if (source == EvidenceSource.GALLERY) "no verificada (galería)" else null
}

/**
 * RF-075: «control de calidad de imagen al capturar: desenfoque, subexposición o sobreexposición;
 * se sugiere repetir. Una foto borrosa (varianza del Laplaciano < umbral) muestra una advertencia.»
 *
 * Works on a grayscale downscale (the Android layer hands a 0–255 luminance array, typically
 * 320 px wide), because the decision does not need 12 megapixels and the phone has a battery.
 */
public data class QualityThresholds(
    val minLaplacianVariance: Double = 100.0,
    val minMeanLuminance: Double = 50.0,
    val maxMeanLuminance: Double = 205.0,
    /** More than this share of pixels burnt to 255 is overexposed whatever the mean says. */
    val maxClippedShare: Double = 0.25,
)

public data class QualityReport(
    val laplacianVariance: Double,
    val meanLuminance: Double,
    val clippedShare: Double,
    val warnings: List<String>,
) {
    val acceptable: Boolean get() = warnings.isEmpty()
}

public object ImageQuality {
    public fun assess(luma: IntArray, width: Int, height: Int, thresholds: QualityThresholds = QualityThresholds()): QualityReport {
        require(width >= 3 && height >= 3 && luma.size == width * height) { "imagen de ${width}x$height inválida" }
        var sum = 0.0
        var clipped = 0
        for (value in luma) {
            sum += value
            if (value >= 250) clipped++
        }
        val mean = sum / luma.size
        val variance = laplacianVariance(luma, width, height)
        val clippedShare = clipped.toDouble() / luma.size
        val warnings = buildList {
            if (variance < thresholds.minLaplacianVariance) add("La foto parece borrosa. ¿Desea repetirla?")
            if (mean < thresholds.minMeanLuminance) add("La foto está muy oscura. ¿Desea repetirla?")
            if (mean > thresholds.maxMeanLuminance || clippedShare > thresholds.maxClippedShare) {
                add("La foto está sobreexpuesta. ¿Desea repetirla?")
            }
        }
        return QualityReport(variance, mean, clippedShare, warnings)
    }

    /** Variance of the 4-neighbour Laplacian over the interior pixels: low means few edges, blurry. */
    public fun laplacianVariance(luma: IntArray, width: Int, height: Int): Double {
        var sum = 0.0
        var sumSquares = 0.0
        var count = 0
        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                val i = y * width + x
                val value = (luma[i - width] + luma[i + width] + luma[i - 1] + luma[i + 1] - 4 * luma[i]).toDouble()
                sum += value
                sumSquares += value * value
                count++
            }
        }
        val mean = sum / count
        return sumSquares / count - mean * mean
    }
}

/** RF-071: what the capture knows about itself. */
public data class CaptureMetadata(
    val workOrderCode: String,
    val userSub: String,
    val deviceModel: String,
    val capturedAtMillis: Long,
    val latitude: Double?,
    val longitude: Double?,
    val accuracyMeters: Double? = null,
    val altitudeMeters: Double? = null,
    val headingDegrees: Double? = null,
)

/**
 * RF-071: «se escriben en EXIF y en la base local». The tag names are `ExifInterface`'s, and the
 * values are already in EXIF's text forms (rationals for GPS), so the Android layer only copies.
 */
public object ExifTags {
    private val EXIF_TIME = DateTimeFormatter.ofPattern("yyyy:MM:dd HH:mm:ss", Locale.ROOT)

    public fun of(meta: CaptureMetadata, zone: ZoneId = ECUADOR): Map<String, String> = buildMap {
        val local = Instant.ofEpochMilli(meta.capturedAtMillis).atZone(zone)
        put("DateTimeOriginal", EXIF_TIME.format(local))
        put("OffsetTimeOriginal", local.offset.id.let { if (it == "Z") "+00:00" else it })
        put("Model", meta.deviceModel)
        put("Artist", meta.userSub)
        put("ImageDescription", "OT ${meta.workOrderCode}")
        if (meta.latitude != null && meta.longitude != null) {
            put("GPSLatitude", dms(meta.latitude))
            put("GPSLatitudeRef", if (meta.latitude < 0) "S" else "N")
            put("GPSLongitude", dms(meta.longitude))
            put("GPSLongitudeRef", if (meta.longitude < 0) "W" else "E")
        }
        meta.altitudeMeters?.let {
            put("GPSAltitude", rational(abs(it)))
            put("GPSAltitudeRef", if (it < 0) "1" else "0")
        }
        meta.headingDegrees?.let {
            put("GPSImgDirection", rational(((it % 360) + 360) % 360))
            put("GPSImgDirectionRef", "T")
        }
        meta.accuracyMeters?.let { put("GPSHPositioningError", rational(it)) }
    }

    /** Degrees as EXIF's «d/1,m/1,s/10000». */
    public fun dms(value: Double): String {
        val absolute = abs(value)
        val degrees = absolute.toInt()
        val minutesFull = (absolute - degrees) * 60
        val minutes = minutesFull.toInt()
        val seconds = Math.round((minutesFull - minutes) * 60 * 10_000)
        return "$degrees/1,$minutes/1,$seconds/10000"
    }

    private fun rational(value: Double): String = "${Math.round(value * 100)}/100"
}

/**
 * RF-072: «marca de agua visible configurable (N.º OT, fecha y hora, coordenadas, usuario) sobre una
 * copia de la imagen; el original sin marca se conserva. La marca es legible en fondo claro y oscuro.»
 */
public data class WatermarkConfig(
    val showWorkOrder: Boolean = true,
    val showDateTime: Boolean = true,
    val showCoordinates: Boolean = true,
    val showUser: Boolean = true,
)

public data class WatermarkStyle(val textArgb: Long, val boxArgb: Long, val outlineArgb: Long)

public object Watermark {
    private val STAMP = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm", Locale.forLanguageTag("es-EC"))

    public fun lines(meta: CaptureMetadata, config: WatermarkConfig = WatermarkConfig(), zone: ZoneId = ECUADOR): List<String> =
        buildList {
            if (config.showWorkOrder) add("OT ${meta.workOrderCode}")
            if (config.showDateTime) add(STAMP.format(Instant.ofEpochMilli(meta.capturedAtMillis).atZone(zone)))
            if (config.showCoordinates && meta.latitude != null && meta.longitude != null) {
                add("%.5f, %.5f".format(Locale.ROOT, meta.latitude, meta.longitude))
            }
            if (config.showUser) add(meta.userSub)
        }

    /**
     * Legible on light and dark: white text with a dark outline, on a translucent box whose opacity
     * rises with the brightness under it. Readable on snow, on night sky and on a white pole alike —
     * one style, so a reviewer never has to guess which version they are looking at.
     */
    public fun style(regionMeanLuminance: Double): WatermarkStyle {
        val alpha = when {
            regionMeanLuminance > 170 -> 0xB3L
            regionMeanLuminance > 85 -> 0x8CL
            else -> 0x59L
        }
        return WatermarkStyle(textArgb = 0xFFFFFFFFL, boxArgb = (alpha shl 24), outlineArgb = 0xFF000000L)
    }
}

internal val ECUADOR: ZoneId = ZoneId.of("America/Guayaquil")
