package ec.sigec.campo.field

import java.time.Instant
import java.time.ZoneId

/**
 * When the phone reports its position (RF-107): «cada N minutos durante la jornada, parámetro, con
 * consentimiento y solo en horario laboral».
 *
 * The rules arrive in the package's capture policy (`position_report_minutes`, `workday_start`,
 * `workday_end`, `workdays`, `require_position_consent`). The server judges every report by the same
 * rules (`policy.service.within_workday`), and `forms/contract/workday-cases.json` is what keeps the
 * two from disagreeing — a phone that reported what the server then refuses would spend battery and
 * data for nothing.
 */
public data class PositionPolicy(
    val reportMinutes: Int = 15,
    val workdayStart: String = "07:00",
    val workdayEnd: String = "17:00",
    val workdays: String = "1,2,3,4,5",
    val requireConsent: Boolean = true,
) {
    public companion object {
        /** From the package manifest's flat policy map (`EffectivePolicy.for_device`). */
        public fun fromManifest(values: Map<String, Any?>): PositionPolicy {
            val defaults = PositionPolicy()
            return PositionPolicy(
                reportMinutes = (values["position_report_minutes"] as? Number)?.toInt() ?: defaults.reportMinutes,
                workdayStart = values["workday_start"] as? String ?: defaults.workdayStart,
                workdayEnd = values["workday_end"] as? String ?: defaults.workdayEnd,
                workdays = values["workdays"] as? String ?: defaults.workdays,
                requireConsent = values["require_position_consent"] as? Boolean ?: defaults.requireConsent,
            )
        }
    }
}

public object WorkdayRule {
    private val ZONE: ZoneId = ZoneId.of("America/Guayaquil")

    /** Same semantics as the server's `within_workday`, case for case. */
    public fun within(policy: PositionPolicy, atMillis: Long): Boolean {
        val local = Instant.ofEpochMilli(atMillis).atZone(ZONE)
        val days = parseDays(policy.workdays)
        val start = minutes(policy.workdayStart)
        val end = minutes(policy.workdayEnd)
        val now = local.hour * 60 + local.minute
        return when {
            start < end -> local.dayOfWeek.value in days && now in start until end
            now >= start -> local.dayOfWeek.value in days
            now < end -> local.minusDays(1).dayOfWeek.value in days
            else -> false
        }
    }

    public fun parseDays(value: String): Set<Int> =
        value.split(",").map { it.trim() }.filter { it.isNotEmpty() }.map { it.toInt() }.toSet()

    private fun minutes(clock: String): Int {
        val (hours, mins) = clock.split(":").map { it.toInt() }
        return hours * 60 + mins
    }
}

public enum class ReportDecision {
    REPORT_NOW,

    /** Inside the day, but the last report is younger than the interval. */
    WAIT,

    /** Outside the working day: nothing is sent, nothing is captured. */
    OFF_HOURS,

    /** The person has not accepted reporting (or withdrew it). */
    NO_CONSENT,
}

public object PositionSchedule {
    /**
     * Whether to take and send a fix now. Consent first, then the day, then the interval — the same
     * order the server refuses in, so the reason shown on the phone is the reason the server gives.
     */
    public fun decide(policy: PositionPolicy, consented: Boolean, lastReportMillis: Long?, nowMillis: Long): ReportDecision =
        when {
            policy.requireConsent && !consented -> ReportDecision.NO_CONSENT
            !WorkdayRule.within(policy, nowMillis) -> ReportDecision.OFF_HOURS
            lastReportMillis != null && nowMillis - lastReportMillis < policy.reportMinutes * 60_000L ->
                ReportDecision.WAIT
            else -> ReportDecision.REPORT_NOW
        }

    /**
     * When to wake up next, for the scheduler: the end of the interval inside the day, or the next
     * minute the day opens. Null when it will never open (no consent): the scheduler stops instead of
     * waking a phone every few minutes to learn it still may not report.
     */
    public fun nextWakeMillis(policy: PositionPolicy, consented: Boolean, lastReportMillis: Long?, nowMillis: Long): Long? {
        if (policy.requireConsent && !consented) return null
        val step = 60_000L
        var candidate = when (decide(policy, consented, lastReportMillis, nowMillis)) {
            ReportDecision.REPORT_NOW -> return nowMillis
            ReportDecision.WAIT -> lastReportMillis!! + policy.reportMinutes * 60_000L
            else -> nowMillis + step
        }
        // A week of minutes is the longest a working day can be away; beyond that the policy has no
        // working day at all and the scheduler stops.
        val limit = nowMillis + 8L * 24 * 60 * step
        while (candidate <= limit) {
            if (WorkdayRule.within(policy, candidate)) return candidate
            candidate += step
        }
        return null
    }
}
