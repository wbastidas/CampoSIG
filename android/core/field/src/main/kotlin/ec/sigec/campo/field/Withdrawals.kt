package ec.sigec.campo.field

import ec.sigec.campo.sync.Authority
import ec.sigec.campo.sync.ConflictResolver
import ec.sigec.campo.sync.LocalWorkOrderState
import ec.sigec.campo.sync.Outbox
import ec.sigec.campo.sync.Resolution
import ec.sigec.campo.sync.ServerWorkOrderState

/**
 * What the phone does with the pull's `withdrawn` list (RF-023, RF-321, RF-322).
 *
 * The server says which orders this phone held and no longer should — reassigned, or out of the
 * field states — with their current owner, state and version. The phone must let them go, and must
 * not lose an afternoon of capture doing it: an order with anything still in the outbox is held
 * until it is delivered, then released. The decision about *who* is right is `ConflictResolver`'s;
 * this turns its resolutions into what to do with the local copy.
 */
public data class Withdrawal(
    val workOrderId: String,
    val state: String,
    val assignedUserSub: String?,
    val version: Int,
    /** `reasignada` or `cambio_de_estado`, for the message only. */
    val reason: String,
) {
    public fun asServerState(): ServerWorkOrderState = ServerWorkOrderState(workOrderId, state, assignedUserSub, version)
}

public enum class ReleaseAction {
    /** Nothing pending: remove it from the phone now. */
    RELEASE_NOW,

    /** Capture still in the outbox: keep it read-only until delivered, then release. */
    HOLD_UNTIL_DELIVERED,

    /** Worked in the field and cancelled at the office: keep it and flag it for a supervisor. */
    HOLD_FOR_SUPERVISOR,

    /** The phone never had it locally (already released, or a fresh install): nothing to do. */
    NOTHING,
}

public data class ReleasePlan(
    val workOrderId: String,
    val action: ReleaseAction,
    val resolutions: List<Resolution>,
    val message: String,
)

public object WithdrawalPlanner {
    public fun plan(withdrawals: List<Withdrawal>, local: Map<String, LocalWorkOrderState>, outbox: Outbox): List<ReleasePlan> =
        withdrawals.map { withdrawal ->
            val held = local[withdrawal.workOrderId]
                ?: return@map ReleasePlan(withdrawal.workOrderId, ReleaseAction.NOTHING, emptyList(), "")
            val pending = !ConflictResolver.mayRelease(outbox, withdrawal.workOrderId)
            // The outbox is the truth about undelivered capture, whatever the cached flag says.
            val resolutions = ConflictResolver.resolve(held.copy(hasUnsyncedCapture = pending), withdrawal.asServerState())
            val action = when {
                resolutions.any { it.authority == Authority.SUPERVISOR } -> ReleaseAction.HOLD_FOR_SUPERVISOR
                pending -> ReleaseAction.HOLD_UNTIL_DELIVERED
                else -> ReleaseAction.RELEASE_NOW
            }
            val message = resolutions.firstOrNull()?.message ?: when (withdrawal.reason) {
                "reasignada" -> "La OT fue reasignada a otro responsable."
                else -> "La OT ya no está en campo (estado «${withdrawal.state}»)."
            }
            ReleasePlan(withdrawal.workOrderId, action, resolutions, message)
        }
}
