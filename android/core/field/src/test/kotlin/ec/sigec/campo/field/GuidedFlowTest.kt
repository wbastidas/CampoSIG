package ec.sigec.campo.field

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** RF-044: «no se puede cerrar la OT con pasos obligatorios incompletos (mensaje que indica cuál falta)». */
class GuidedFlowTest {
    private fun req(step: Step, id: String, done: Boolean, mandatory: Boolean = true) =
        Requirement(step, id, id, mandatory, done)

    @Test
    fun `rf 044 the blocker names the first missing item in flow order`() {
        val requirements = listOf(
            req(Step.CLOSURE, "Estado final", false),
            req(Step.SAFETY, "ATS firmado", false),
            req(Step.BEFORE, "Foto del poste", true),
        )
        assertEquals("Falta «ATS firmado» en el paso Seguridad (y 1 más)", GuidedFlow.closeBlocker(requirements))
    }

    @Test
    fun `an optional item never blocks the close`() {
        assertNull(GuidedFlow.closeBlocker(listOf(req(Step.SUMMARY, "Observación", false, mandatory = false))))
    }

    @Test
    fun `progress is per step, in the six steps of the flow`() {
        val progress = GuidedFlow.progress(listOf(req(Step.BEFORE, "a", true), req(Step.BEFORE, "b", false, mandatory = false)))
        assertEquals(Step.entries, progress.map { it.step })
        val before = progress.first { it.step == Step.BEFORE }
        assertEquals(50, before.percent)
        assertTrue(before.complete)
        assertEquals(100, progress.first { it.step == Step.SAFETY }.percent)
    }

    @Test
    fun `photo minimums count only countable photos`() {
        val requirement = GuidedFlow.photoRequirement(Step.BEFORE, minimum = 2, countable = 1)!!
        assertEquals(false, requirement.satisfied)
        assertEquals("2 foto(s) ANTES con la cámara (1 de 2)", requirement.label)
        assertNull(GuidedFlow.photoRequirement(Step.AFTER, minimum = 0, countable = 0))
    }
}
