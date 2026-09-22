package ec.sigec.campo.sync

/**
 * Conditional requirements, one third of a three-platform contract (I5, SRS 7.2).
 *
 * The same subset of JSON Logic the backend evaluates in `app/forms/rules.py` and the web in
 * `src/forms/rules.ts`. Agreement is not achieved by writing the algorithm carefully three
 * times — that produces three algorithms that match on the cases somebody thought of. It is
 * achieved by `forms/contract/validation-cases.json`, which all three test suites run.
 *
 * The failure it prevents is expensive in the field and runs both ways. If the phone accepts a
 * capture the server later rejects, the crew's work comes back the next day and nobody knows
 * why. If the phone demands a field the server does not, the crew cannot close the work order
 * with the network down — which is the situation this whole product exists for.
 *
 * It lives in `core:sync` rather than in the Android layer for the reason ADR-010 gives: this is
 * a decision, so it belongs where it can be tested on the JVM without a device. The renderer
 * calls it; it contains no UI.
 *
 * Rules and answers arrive as plain maps, deliberately. This module carries no serialisation
 * framework, and a rule is data that came off the network — typing it into a sealed hierarchy
 * would mean parsing it twice and disagreeing with the other two platforms about the edges.
 */

/** One field a rule demanded and the answers do not supply. */
public data class MissingRequirement(
    public val field: String,
    /** The rule's own message when it has one. Presentation: the contract is the field. */
    public val message: String? = null,
)

/**
 * Whether a value counts as an answer.
 *
 * Three cases worth naming, because each is a way all three implementations get it wrong at once:
 * **zero is an answer** (a measured 0 Ω is a result), **false is an answer** ("was it
 * sign-posted? no" is a reply), and **whitespace is not** (a field holding a space reads as empty
 * on the screen and on paper).
 */
public fun isAnswered(value: Any?): Boolean =
    when (value) {
        null -> false
        is Boolean, is Number -> true
        is String -> value.isNotBlank()
        is Collection<*> -> value.isNotEmpty()
        is Map<*, *> -> value.isNotEmpty()
        else -> true
    }

/** Resolve an operand: `{"var": "x"}` reads an answer, anything else is a literal. */
public fun resolveOperand(token: Any?, answers: Map<String, Any?>): Any? {
    if (token is Map<*, *> && token.containsKey("var")) {
        val name = token["var"]
        return if (name is String) answers[name] else null
    }
    return token
}

/**
 * Equality that does not coerce across types.
 *
 * `11` and `"11"` are different values, and a boolean is never 0 or 1 — otherwise "was it
 * sign-posted?" would match a count. Numbers compare by value so an integer literal in the rule
 * and a double from the wire agree, which is the one coercion the contract does want.
 */
private fun same(left: Any?, right: Any?): Boolean {
    if (left is Boolean || right is Boolean) return left is Boolean && right is Boolean && left == right
    if (left is String || right is String) return left is String && right is String && left == right
    if (left is Number && right is Number) return left.toDouble() == right.toDouble()
    return left == right
}

private fun operandPair(operands: Any?): Pair<Any?, Any?>? {
    val list = operands as? List<*> ?: return null
    if (list.size != 2) return null
    return list[0] to list[1]
}

/** Evaluate one condition. Anything unrecognised is `false`, never a thrown error. */
public fun evaluateCondition(condition: Any?, answers: Map<String, Any?>): Boolean {
    val map = condition as? Map<*, *> ?: return false
    if (map.isEmpty()) return false

    if (map.containsKey("==")) {
        val pair = operandPair(map["=="]) ?: return false
        return same(resolveOperand(pair.first, answers), resolveOperand(pair.second, answers))
    }

    if (map.containsKey("!=")) {
        val pair = operandPair(map["!="]) ?: return false
        return !same(resolveOperand(pair.first, answers), resolveOperand(pair.second, answers))
    }

    if (map.containsKey("in")) {
        val pair = operandPair(map["in"]) ?: return false
        val needle = resolveOperand(pair.first, answers)
        val haystack = resolveOperand(pair.second, answers)
        return when (haystack) {
            // JSON Logic defines `in` over a string as substring containment.
            is String -> needle is String && haystack.contains(needle)
            is Collection<*> -> haystack.any { same(needle, it) }
            // Neither a list nor a string: false, not an exception. A badly written rule must not
            // stop a technician from sending a day's work.
            else -> false
        }
    }

    if (map.containsKey("and")) {
        val parts = map["and"] as? List<*> ?: return false
        return parts.isNotEmpty() && parts.all { evaluateCondition(it, answers) }
    }

    if (map.containsKey("or")) {
        val parts = map["or"] as? List<*> ?: return false
        return parts.isNotEmpty() && parts.any { evaluateCondition(it, answers) }
    }

    return false
}

/**
 * Fields the rules demand and the answers do not supply, in the rules' own order.
 *
 * Deduplicated: two rules may demand the same field, and telling the crew twice about one empty
 * box is a defect of the platform, not a fact about their work. The order is the rules' order, so
 * the list a technician reads does not shuffle between the phone and the web.
 */
public fun missingRequirements(
    rules: List<*>?,
    answers: Map<String, Any?>,
): List<MissingRequirement> {
    if (rules == null) return emptyList()
    val found = mutableListOf<MissingRequirement>()
    val seen = mutableSetOf<String>()

    for (rule in rules) {
        val map = rule as? Map<*, *> ?: continue
        val required = map["require"] as? List<*> ?: continue
        if (required.isEmpty()) continue
        if (!evaluateCondition(map["when"], answers)) continue
        val message = (map["message"] as? String)?.takeIf { it.isNotEmpty() }
        for (field in required) {
            val key = field?.toString() ?: continue
            if (key in seen || isAnswered(answers[key])) continue
            seen += key
            found += MissingRequirement(field = key, message = message)
        }
    }
    return found
}

/** The messages a technician reads, which is what the renderer shows under the field. */
public fun requirementMessages(rules: List<*>?, answers: Map<String, Any?>): List<String> =
    missingRequirements(rules, answers).map {
        it.message ?: "${it.field}: es obligatorio en este caso"
    }
