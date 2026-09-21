package ec.sigec.campo.sync

/**
 * Conflict resolution between device and server (RF-105, RF-322).
 *
 * The situation this exists for: a technician works a whole afternoon offline while, back at
 * the office, a planner reassigns the work order to somebody else. Both sides are right about
 * different things, and the rule that settles it is:
 *
 *  - the **server** is authoritative on who the work belongs to and on its administrative
 *    state, because that is a planning decision made with information the device never had;
 *  - the **device** is authoritative on what it captured, because it was there and nobody
 *    else saw it.
 *
 * What must never happen is losing the capture. A reassignment that discards an afternoon of
 * a technician's work is worse than any planning inconsistency it was meant to fix, and it is
 * the fastest way to lose a field team's trust in the system.
 */

/** Who wins a particular disagreement. */
public enum class Authority {
    SERVER,
    DEVICE,

    /** Neither can decide alone: a human has to look (RF-105). */
    SUPERVISOR,
}

/** The kinds of disagreement sync can encounter. */
public enum class ConflictKind {
    /** The server assigned the work order to someone else while the device held it. */
    REASSIGNED_WHILE_HELD,

    /** The server moved the administrative state (returned, cancelled) under the device. */
    ADMIN_STATE_CHANGED,

    /** Both sides changed the same form field. */
    FIELD_EDITED_ON_BOTH_SIDES,

    /** The device closed the work order in the field; the server had cancelled it. */
    CLOSED_BUT_CANCELLED,
}

/**
 * A resolution: who wins, and what the device must do about it.
 *
 * @param keepsLocalCapture whether the device retains what it captured. This is the field to
 *   look at in a review: it must be true for every resolution that is not a cancellation
 *   already reconciled by a human.
 */
public data class Resolution(
    val kind: ConflictKind,
    val authority: Authority,
    val keepsLocalCapture: Boolean,
    val requiresUpload: Boolean,
    val message: String,
)

/** State the device knows about a work order. */
public data class LocalWorkOrderState(
    val workOrderId: String,
    val state: String,
    val assignedUserSub: String?,
    val hasUnsyncedCapture: Boolean,
    /** Server version the device last saw, for detecting concurrent change. */
    val baseVersion: Int,
)

/** State the server holds for the same work order. */
public data class ServerWorkOrderState(
    val workOrderId: String,
    val state: String,
    val assignedUserSub: String?,
    val version: Int,
)

public object ConflictResolver {

    /** States that mean the work order is finished administratively. */
    private val TERMINAL = setOf("cerrada", "anulada")

    /** States a device reaches by working: reaching them means capture happened. */
    private val FIELD_PROGRESS = setOf("en_ejecucion", "cerrada_campo", "en_sitio", "en_camino")

    /**
     * Resolve the difference between what the device holds and what the server holds.
     *
     * @return the resolutions to apply, in order. Empty when the two agree.
     */
    public fun resolve(
        local: LocalWorkOrderState,
        server: ServerWorkOrderState,
    ): List<Resolution> {
        require(local.workOrderId == server.workOrderId) {
            "no se pueden comparar OT distintas: ${local.workOrderId} y ${server.workOrderId}"
        }

        val resolutions = mutableListOf<Resolution>()

        if (server.version == local.baseVersion) {
            // Nothing changed server-side while the device was away.
            return resolutions
        }

        val reassigned = server.assignedUserSub != local.assignedUserSub
        if (reassigned) {
            resolutions += Resolution(
                kind = ConflictKind.REASSIGNED_WHILE_HELD,
                authority = Authority.SERVER,
                // The reassignment stands, and the capture is uploaded before the device
                // lets the work order go. That is the whole point of RF-322.
                keepsLocalCapture = true,
                requiresUpload = local.hasUnsyncedCapture,
                message = if (local.hasUnsyncedCapture) {
                    "La OT fue reasignada. Se subirá lo que ya capturó antes de liberarla."
                } else {
                    "La OT fue reasignada a otro responsable."
                },
            )
        }

        if (server.state in TERMINAL && local.state in FIELD_PROGRESS) {
            // Both sides acted. Neither can decide alone: the server cancelled work that the
            // technician had in fact carried out, and somebody has to reconcile that.
            resolutions += Resolution(
                kind = ConflictKind.CLOSED_BUT_CANCELLED,
                authority = Authority.SUPERVISOR,
                keepsLocalCapture = true,
                requiresUpload = local.hasUnsyncedCapture,
                message = "La OT fue ${server.state} en el servidor pero se trabajó en campo. " +
                    "Se envía a revisión del supervisor sin descartar lo capturado.",
            )
        } else if (server.state != local.state && !reassigned) {
            resolutions += Resolution(
                kind = ConflictKind.ADMIN_STATE_CHANGED,
                authority = Authority.SERVER,
                keepsLocalCapture = true,
                requiresUpload = local.hasUnsyncedCapture,
                message = "El estado administrativo cambió en el servidor a '${server.state}'.",
            )
        }

        return resolutions
    }

    /**
     * Whether the device may release a work order.
     *
     * False while anything captured for it is still undelivered. This is the check that stops
     * a reassignment from costing a technician their afternoon (RF-322).
     */
    public fun mayRelease(outbox: Outbox, workOrderId: String): Boolean =
        outbox.isFullyDelivered(workOrderId)

    /**
     * Resolve a field-level disagreement.
     *
     * The device wins on captured values: it was there. The exception is a value a human
     * already reviewed on the server — overwriting a supervisor's correction with a stale
     * local value would undo a decision made with more information.
     */
    public fun resolveField(
        fieldKey: String,
        deviceChanged: Boolean,
        serverChanged: Boolean,
        serverReviewedByHuman: Boolean,
    ): Resolution? {
        if (!deviceChanged || !serverChanged) return null
        return if (serverReviewedByHuman) {
            Resolution(
                kind = ConflictKind.FIELD_EDITED_ON_BOTH_SIDES,
                authority = Authority.SUPERVISOR,
                keepsLocalCapture = true,
                requiresUpload = false,
                message = "El campo '$fieldKey' fue corregido por un revisor; " +
                    "su valor local se conserva como propuesta.",
            )
        } else {
            Resolution(
                kind = ConflictKind.FIELD_EDITED_ON_BOTH_SIDES,
                authority = Authority.DEVICE,
                keepsLocalCapture = true,
                requiresUpload = true,
                message = "El campo '$fieldKey' se capturó en campo y prevalece.",
            )
        }
    }
}
