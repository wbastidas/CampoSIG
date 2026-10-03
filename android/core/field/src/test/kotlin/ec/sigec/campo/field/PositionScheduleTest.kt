package ec.sigec.campo.field

import com.google.gson.Gson
import java.io.File
import java.time.Instant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

/**
 * RF-107 on the phone. The workday corpus is shared with the server
 * (`backend/tests/unit/test_rf107_workday_contract.py`): the phone decides when to report and the
 * server what to keep, and they must agree on every case.
 */
class PositionScheduleTest {
    private data class Case(val id: String, val start: String, val end: String, val days: String, val at: String, val inside: Boolean)

    private data class Corpus(val cases: List<Case>)

    private val corpus: Corpus by lazy {
        val root = File(System.getProperty("user.dir")).parentFile.parentFile.parentFile
        Gson().fromJson(File(root, "forms/contract/workday-cases.json").readText(), Corpus::class.java)
    }

    private val thursday10 = Instant.parse("2026-09-24T15:00:00Z").toEpochMilli()

    @Test
    fun `rf 107 the phone agrees with the server on the workday corpus`() {
        val wrong = corpus.cases.filter {
            WorkdayRule.within(PositionPolicy(workdayStart = it.start, workdayEnd = it.end, workdays = it.days), Instant.parse(it.at).toEpochMilli()) != it.inside
        }.map { it.id }
        assertEquals(emptyList(), wrong)
    }

    @Test
    fun `consent first, then the day, then the interval`() {
        val policy = PositionPolicy(reportMinutes = 15)
        assertEquals(ReportDecision.NO_CONSENT, PositionSchedule.decide(policy, false, null, thursday10))
        assertEquals(ReportDecision.OFF_HOURS, PositionSchedule.decide(policy, true, null, Instant.parse("2026-09-26T15:00:00Z").toEpochMilli()))
        assertEquals(ReportDecision.WAIT, PositionSchedule.decide(policy, true, thursday10 - 5 * 60_000, thursday10))
        assertEquals(ReportDecision.REPORT_NOW, PositionSchedule.decide(policy, true, thursday10 - 15 * 60_000, thursday10))
        assertEquals(ReportDecision.REPORT_NOW, PositionSchedule.decide(PositionPolicy(requireConsent = false), false, null, thursday10))
    }

    @Test
    fun `the next wake is the end of the interval or the opening of the next day`() {
        val policy = PositionPolicy(reportMinutes = 15)
        assertEquals(thursday10 + 10 * 60_000, PositionSchedule.nextWakeMillis(policy, true, thursday10 - 5 * 60_000, thursday10))
        val fridayEvening = Instant.parse("2026-09-25T23:00:00Z").toEpochMilli() // 18:00 local
        assertEquals(Instant.parse("2026-09-28T12:00:00Z").toEpochMilli(), PositionSchedule.nextWakeMillis(policy, true, null, fridayEvening))
        assertNull(PositionSchedule.nextWakeMillis(policy, false, null, thursday10))
    }

    @Test
    fun `the policy is read from the package manifest`() {
        val policy = PositionPolicy.fromManifest(
            mapOf("position_report_minutes" to 30.0, "workday_end" to "18:00", "require_position_consent" to false),
        )
        assertEquals(PositionPolicy(reportMinutes = 30, workdayEnd = "18:00", requireConsent = false), policy)
    }
}
