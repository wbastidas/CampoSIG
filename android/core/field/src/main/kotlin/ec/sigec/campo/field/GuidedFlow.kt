package ec.sigec.campo.field

/**
 * The guided flow (RF-044): «Seguridad → Antes → Ejecución → Después → Resumen → Cierre, con
 * indicadores de completitud. No se puede cerrar la OT con pasos obligatorios incompletos (mensaje
 * que indica cuál falta).»
 *
 * Which field belongs to which step is data — the form's blocks, read from the package — and this
 * only adds up what the screen hands it: the requirements of each step and whether each is met.
 * The conditional ones come from `core:sync`'s `FormRules`, the same rules the server applies.
 */
public enum class Step(public val label: String) {
    SAFETY("Seguridad"),
    BEFORE("Antes"),
    EXECUTION("Ejecución"),
    AFTER("Después"),
    SUMMARY("Resumen"),
    CLOSURE("Cierre"),
}

public data class Requirement(
    val step: Step,
    val id: String,
    /** What the technician reads: «ATS firmado», «2 fotos ANTES», «Estado final». */
    val label: String,
    val mandatory: Boolean,
    val satisfied: Boolean,
)

public data class StepProgress(val step: Step, val done: Int, val total: Int, val missingMandatory: List<Requirement>) {
    val complete: Boolean get() = missingMandatory.isEmpty()

    /** For the indicator: 0 to 100, counting mandatory and optional alike. */
    val percent: Int get() = if (total == 0) 100 else done * 100 / total
}

public object GuidedFlow {
    public fun progress(requirements: List<Requirement>): List<StepProgress> = Step.entries.map { step ->
        val mine = requirements.filter { it.step == step }
        StepProgress(
            step = step,
            done = mine.count { it.satisfied },
            total = mine.size,
            missingMandatory = mine.filter { it.mandatory && !it.satisfied },
        )
    }

    /**
     * Why the order cannot be closed yet, naming the first thing missing in flow order; null when it
     * can. «Mensaje que indica cuál falta» — the step and the item, not «formulario incompleto».
     */
    public fun closeBlocker(requirements: List<Requirement>): String? {
        val missing = progress(requirements).flatMap { it.missingMandatory }
        val first = missing.firstOrNull() ?: return null
        val more = missing.size - 1
        val tail = if (more > 0) " (y $more más)" else ""
        return "Falta «${first.label}» en el paso ${first.step.label}$tail"
    }

    /**
     * The photo minimums as requirements of their step. Only live-camera photos that were not
     * found altered count (RF-074, RF-073) — the same rule the server applies to the same photos.
     */
    public fun photoRequirement(step: Step, minimum: Int, countable: Int): Requirement? {
        if (minimum <= 0) return null
        val stage = if (step == Step.BEFORE) "ANTES" else "DESPUÉS"
        return Requirement(
            step = step,
            id = "photos_${step.name.lowercase()}",
            label = "$minimum foto(s) $stage con la cámara ($countable de $minimum)",
            mandatory = true,
            satisfied = countable >= minimum,
        )
    }
}
