package ec.sigec.campo.field

import java.time.Instant

/**
 * Automatic times per transition, and their justified correction (RF-047), on the phone.
 *
 * The phone is where the time happens: «en sitio» is the moment the crew got there, not the moment
 * a server heard about it hours later. Each transition records the phone's clock once, the first
 * time — a resumed job does not restart its clock — and a correction sits beside the original
 * without replacing it. The server keeps the same three clocks (`work_order_milestone`) and refuses
 * the same corrections, so what the phone accepts the server accepts.
 */
public enum class Milestone(public val wire: String) {
    EN_ROUTE("en_camino"),
    ON_SITE("en_sitio"),
    STARTED("inicio"),
    FINISHED("fin"),
    ;

    public companion object {
        /** The state that marks each milestone, as the server names states. */
        private val BY_STATE = mapOf(
            "en_camino" to EN_ROUTE,
            "en_sitio" to ON_SITE,
            "en_ejecucion" to STARTED,
            "cerrada_campo" to FINISHED,
        )

        public fun ofState(state: String): Milestone? = BY_STATE[state]
    }
}

public data class MilestoneTime(
    val milestone: Milestone,
    val deviceMillis: Long,
    val correctedMillis: Long? = null,
    val correctionReason: String? = null,
) {
    val effectiveMillis: Long get() = correctedMillis ?: deviceMillis
}

public class TimeLogException(message: String) : IllegalArgumentException(message)

public class TimeLog private constructor(private val times: Map<Milestone, MilestoneTime>) {
    public companion object {
        public fun empty(): TimeLog = TimeLog(emptyMap())

        /** A few minutes of slack for the phone's own clock, the same the server allows. */
        public const val FUTURE_SLACK_MILLIS: Long = 5 * 60 * 1000L
    }

    public fun all(): List<MilestoneTime> = Milestone.entries.mapNotNull { times[it] }

    public fun of(milestone: Milestone): MilestoneTime? = times[milestone]

    /** A transition happened at [nowMillis]: record its milestone if it is the first time. */
    public fun onTransition(targetState: String, nowMillis: Long): TimeLog {
        val milestone = Milestone.ofState(targetState) ?: return this
        if (milestone in times) return this
        return TimeLog(times + (milestone to MilestoneTime(milestone, nowMillis)))
    }

    /**
     * Correct a milestone's time. The original stays; the reason is required.
     *
     * @throws TimeLogException with the sentence the technician reads, for the same cases the
     *   server refuses: no reason, a milestone not reached yet, or a time in the future.
     */
    public fun correct(milestone: Milestone, correctedMillis: Long, reason: String, nowMillis: Long): TimeLog {
        if (reason.isBlank()) throw TimeLogException("corregir un tiempo exige el motivo")
        val current = times[milestone]
            ?: throw TimeLogException("la OT todavía no pasó por «${milestone.wire}»: no hay tiempo que corregir")
        if (correctedMillis > nowMillis + FUTURE_SLACK_MILLIS) {
            throw TimeLogException("la hora corregida no puede estar en el futuro")
        }
        val fixed = current.copy(correctedMillis = correctedMillis, correctionReason = reason.trim().take(500))
        return TimeLog(times + (milestone to fixed))
    }

    /** The payload of the `transition` operation: the target and the phone's time. */
    public fun transitionPayload(targetState: String, nowMillis: Long, reason: String? = null): Map<String, Any?> =
        buildMap {
            put("target", targetState)
            put("occurred_at", Instant.ofEpochMilli(nowMillis).toString())
            if (reason != null) put("reason", reason)
        }

    /** The payload of the `time_correction` operation for a corrected milestone. */
    public fun correctionPayload(milestone: Milestone): Map<String, Any?> {
        val time = times[milestone] ?: throw TimeLogException("no hay tiempo de «${milestone.wire}»")
        val corrected = time.correctedMillis ?: throw TimeLogException("«${milestone.wire}» no fue corregido")
        return mapOf(
            "milestone" to milestone.wire,
            "corrected_time" to Instant.ofEpochMilli(corrected).toString(),
            "reason" to time.correctionReason,
        )
    }
}
