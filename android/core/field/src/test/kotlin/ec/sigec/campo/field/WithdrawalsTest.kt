package ec.sigec.campo.field

import ec.sigec.campo.sync.LocalWorkOrderState
import ec.sigec.campo.sync.OperationKind
import ec.sigec.campo.sync.Outbox
import ec.sigec.campo.sync.SyncOperation
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** RF-023, RF-321, RF-322: the pull's `withdrawn`, applied without losing an afternoon of capture. */
class WithdrawalsTest {
    private fun local(id: String, state: String = "en_ejecucion") = LocalWorkOrderState(id, state, "kc|yo", false, baseVersion = 3)

    @Test
    fun `rf 023 a reassigned order with nothing pending is released now`() {
        val plan = WithdrawalPlanner.plan(
            listOf(Withdrawal("ot-1", "asignada", "kc|otro", 4, "reasignada")),
            mapOf("ot-1" to local("ot-1", state = "descargada")),
            Outbox.empty(),
        ).single()
        assertEquals(ReleaseAction.RELEASE_NOW, plan.action)
        assertEquals("La OT fue reasignada a otro responsable.", plan.message)
    }

    @Test
    fun `rf 322 a reassigned order with capture still in the outbox is held until delivered`() {
        val outbox = Outbox.empty().enqueue(SyncOperation("op", OperationKind.FORM_RESPONSE, "ot-1", 0))
        val plan = WithdrawalPlanner.plan(
            listOf(Withdrawal("ot-1", "asignada", "kc|otro", 4, "reasignada")),
            mapOf("ot-1" to local("ot-1")),
            outbox,
        ).single()
        assertEquals(ReleaseAction.HOLD_UNTIL_DELIVERED, plan.action)
        assertTrue(plan.resolutions.all { it.keepsLocalCapture })
        assertTrue(plan.message.contains("Se subirá lo que ya capturó"))
    }

    @Test
    fun `worked in the field and cancelled at the office goes to a supervisor`() {
        val plan = WithdrawalPlanner.plan(
            listOf(Withdrawal("ot-1", "anulada", "kc|yo", 4, "cambio_de_estado")),
            mapOf("ot-1" to local("ot-1")),
            Outbox.empty(),
        ).single()
        assertEquals(ReleaseAction.HOLD_FOR_SUPERVISOR, plan.action)
    }

    @Test
    fun `an order the phone no longer holds needs nothing`() {
        val plan = WithdrawalPlanner.plan(listOf(Withdrawal("ot-9", "cerrada", null, 9, "cambio_de_estado")), emptyMap(), Outbox.empty())
        assertEquals(ReleaseAction.NOTHING, plan.single().action)
    }
}
