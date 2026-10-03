package ec.sigec.campo.field

import java.io.ByteArrayInputStream
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class EvidenceTest {
    private val meta = CaptureMetadata(
        workOrderCode = "OT-2026-0001",
        userSub = "kc|tecnico",
        deviceModel = "Pixel 8a",
        capturedAtMillis = 1_790_000_000_000L,
        latitude = -2.170_5,
        longitude = -79.900_25,
        accuracyMeters = 4.5,
        altitudeMeters = 12.3,
        headingDegrees = -90.0,
    )

    @Test
    fun `rf 073 the hash is sha-256 of the original, streaming or not`() {
        val bytes = "foto-antes-original".toByteArray()
        assertEquals(64, EvidenceHash.of(bytes).length)
        assertEquals(EvidenceHash.of(bytes), EvidenceHash.of(ByteArrayInputStream(bytes)))
        assertEquals("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", EvidenceHash.of(ByteArray(0)))
    }

    @Test
    fun `rf 074 no gallery for before and after, and a gallery photo never counts`() {
        assertFalse(GalleryPolicy.galleryAllowed(EvidenceStage.BEFORE))
        assertFalse(GalleryPolicy.galleryAllowed(EvidenceStage.AFTER))
        assertTrue(GalleryPolicy.galleryAllowed(EvidenceStage.NOT_APPLICABLE))
        assertFalse(GalleryPolicy.countsAsEvidence(EvidenceSource.GALLERY))
        assertFalse(GalleryPolicy.countsAsEvidence(EvidenceSource.CAMERA, altered = true))
        assertTrue(GalleryPolicy.countsAsEvidence(EvidenceSource.CAMERA))
        assertEquals("no verificada (galería)", GalleryPolicy.label(EvidenceSource.GALLERY))
    }

    private fun image(width: Int, height: Int, pixel: (Int, Int) -> Int) =
        IntArray(width * height) { pixel(it % width, it / width) }

    @Test
    fun `rf 075 a sharp checkerboard passes and a flat grey is blurry`() {
        val sharp = ImageQuality.assess(image(40, 40) { x, y -> if ((x + y) % 2 == 0) 40 else 200 }, 40, 40)
        assertTrue(sharp.acceptable, sharp.warnings.toString())
        val flat = ImageQuality.assess(image(40, 40) { _, _ -> 128 }, 40, 40)
        assertEquals(listOf("La foto parece borrosa. ¿Desea repetirla?"), flat.warnings)
    }

    @Test
    fun `rf 075 dark and burnt photos are flagged`() {
        val dark = ImageQuality.assess(image(40, 40) { x, y -> if ((x + y) % 2 == 0) 0 else 60 }, 40, 40)
        assertTrue("La foto está muy oscura. ¿Desea repetirla?" in dark.warnings)
        val burnt = ImageQuality.assess(image(40, 40) { x, _ -> if (x < 25) 255 else 80 + x }, 40, 40)
        assertTrue("La foto está sobreexpuesta. ¿Desea repetirla?" in burnt.warnings)
    }

    @Test
    fun `rf 071 exif carries the gps, the time in ecuador, the person and the device`() {
        val tags = ExifTags.of(meta)
        assertEquals("2026:09:21 09:13:20", tags["DateTimeOriginal"])
        assertEquals("-05:00", tags["OffsetTimeOriginal"])
        assertEquals("S", tags["GPSLatitudeRef"])
        assertEquals("W", tags["GPSLongitudeRef"])
        assertEquals("2/1,10/1,138000/10000", tags["GPSLatitude"])
        assertEquals("1230/100", tags["GPSAltitude"])
        assertEquals("0", tags["GPSAltitudeRef"])
        assertEquals("27000/100", tags["GPSImgDirection"])
        assertEquals("Pixel 8a", tags["Model"])
        assertEquals("kc|tecnico", tags["Artist"])
        assertEquals("OT OT-2026-0001", tags["ImageDescription"])
    }

    @Test
    fun `without a fix there are no gps tags rather than zeros`() {
        val tags = ExifTags.of(meta.copy(latitude = null, longitude = null, altitudeMeters = null))
        assertFalse(tags.keys.any { it.startsWith("GPSLat") || it.startsWith("GPSAlt") })
    }

    @Test
    fun `rf 072 the watermark says what was configured, in ecuador's time`() {
        assertEquals(
            listOf("OT OT-2026-0001", "21/09/2026 09:13", "-2.17050, -79.90025", "kc|tecnico"),
            Watermark.lines(meta),
        )
        assertEquals(listOf("OT OT-2026-0001"), Watermark.lines(meta, WatermarkConfig(showDateTime = false, showCoordinates = false, showUser = false)))
    }

    @Test
    fun `rf 072 legible on light and dark - the box darkens over bright backgrounds`() {
        val bright = Watermark.style(230.0)
        val dark = Watermark.style(20.0)
        assertEquals(0xFFFFFFFFL, bright.textArgb)
        assertTrue((bright.boxArgb ushr 24) > (dark.boxArgb ushr 24))
        assertEquals(0xFF000000L, dark.outlineArgb)
    }
}
