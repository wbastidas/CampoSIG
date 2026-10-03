package ec.sigec.campo.field

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

/** RF-047: «una edición manual del tiempo guarda el original y el motivo». */
class TimeLogTest {
    private val t = 1_790_000_000_000L

    @Test
    fun `rf 047 transitions record their milestone once`() {
        val log = TimeLog.empty()
            .onTransition("en_camino", t)
            .onTransition("en_sitio", t + 1_000)
            .onTransition("en_ejecucion", t + 2_000)
            .onTransition("suspendida", t + 3_000)
            .onTransition("en_ejecucion", t + 9_000)
        assertEquals(listOf(Milestone.EN_ROUTE, Milestone.ON_SITE, Milestone.STARTED), log.all().map { it.milestone })
        assertEquals(t + 2_000, log.of(Milestone.STARTED)!!.deviceMillis)
    }

    @Test
    fun `a correction keeps the original beside it`() {
        val log = TimeLog.empty().onTransition("en_sitio", t).correct(Milestone.ON_SITE, t - 600_000, "llegué antes", t)
        val time = log.of(Milestone.ON_SITE)!!
        assertEquals(t, time.deviceMillis)
        assertEquals(t - 600_000, time.effectiveMillis)
        assertEquals("llegué antes", time.correctionReason)
    }

    @Test
    fun `the corrections the server refuses are refused here too`() {
        val log = TimeLog.empty().onTransition("en_sitio", t)
        assertFailsWith<TimeLogException> { log.correct(Milestone.ON_SITE, t, " ", t) }
        assertFailsWith<TimeLogException> { log.correct(Milestone.FINISHED, t, "x", t) }
        assertFailsWith<TimeLogException> { log.correct(Milestone.ON_SITE, t + 3_600_000, "x", t) }
    }

    @Test
    fun `the payloads are what the server reads`() {
        val log = TimeLog.empty().onTransition("en_sitio", t).correct(Milestone.ON_SITE, t - 60_000, "motivo", t)
        assertEquals("en_sitio", log.transitionPayload("en_sitio", t)["target"])
        assertEquals("2026-09-21T14:13:20Z", log.transitionPayload("en_sitio", t)["occurred_at"])
        assertEquals(
            mapOf("milestone" to "en_sitio", "corrected_time" to "2026-09-21T14:12:20Z", "reason" to "motivo"),
            log.correctionPayload(Milestone.ON_SITE),
        )
    }
}
