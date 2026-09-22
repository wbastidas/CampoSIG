/**
 * Conditional requirements, one third of a three-platform contract (I5, SRS 7.2).
 *
 * The same subset of JSON Logic the backend evaluates in `app/forms/rules.py` and the phone
 * evaluates in `core:sync`. Agreement is not achieved by writing the algorithm carefully three
 * times — that produces three algorithms that match on the cases somebody thought of. It is
 * achieved by `forms/contract/validation-cases.json`, which all three test suites run.
 *
 * Two JavaScript-specific traps the corpus pins down, and both would be invisible in review:
 *
 * * **Falsy is not empty.** `if (!value)` treats `0` and `false` as blanks, so a measured 0 Ω
 *   and a "was it sign-posted? no" would both be reported as unanswered.
 * * **`==` coerces.** `11 == '11'` is true, so a rule would fire here and not on the server.
 *   Every comparison below is type-aware for that reason.
 */

/** A rule as the block library declares it. Values come from JSON, hence `unknown`. */
export interface FormRule {
  when?: unknown;
  require?: unknown;
  message?: unknown;
  blocks_execution?: boolean;
}

export interface MissingRequirement {
  field: string;
  /** The rule's own message when it has one. Presentation: the contract is the field. */
  message: string | null;
}

export type Answers = Record<string, unknown>;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Whether a value counts as an answer.
 *
 * Deliberately not `Boolean(value)`: zero is a measurement, `false` is a reply, and a field
 * holding a space reads as empty both on screen and on paper.
 */
export function isAnswered(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === 'boolean' || typeof value === 'number') return true;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (isPlainObject(value)) return Object.keys(value).length > 0;
  return true;
}

/** Resolve an operand: `{var: 'x'}` reads an answer, anything else is a literal. */
export function resolve(token: unknown, answers: Answers): unknown {
  if (isPlainObject(token) && 'var' in token) {
    const name = token.var;
    return typeof name === 'string' ? answers[name] : undefined;
  }
  return token;
}

/**
 * Equality that does not coerce across types.
 *
 * `11` and `'11'` are different values, and a boolean is never 0 or 1 — otherwise "was it
 * sign-posted?" would match a count.
 */
function same(left: unknown, right: unknown): boolean {
  if (typeof left !== typeof right) return false;
  return left === right;
}

function operandPair(operands: unknown): [unknown, unknown] | null {
  if (!Array.isArray(operands) || operands.length !== 2) return null;
  return [operands[0], operands[1]];
}

/** Evaluate one condition. Anything unrecognised is `false`, never a thrown error. */
export function evaluateCondition(condition: unknown, answers: Answers): boolean {
  if (!isPlainObject(condition) || Object.keys(condition).length === 0) return false;

  if ('==' in condition) {
    const pair = operandPair(condition['==']);
    return pair !== null && same(resolve(pair[0], answers), resolve(pair[1], answers));
  }

  if ('!=' in condition) {
    const pair = operandPair(condition['!=']);
    return pair !== null && !same(resolve(pair[0], answers), resolve(pair[1], answers));
  }

  if ('in' in condition) {
    const pair = operandPair(condition['in']);
    if (pair === null) return false;
    const needle = resolve(pair[0], answers);
    const haystack = resolve(pair[1], answers);
    if (typeof haystack === 'string') {
      // JSON Logic defines `in` over a string as substring containment.
      return typeof needle === 'string' && haystack.includes(needle);
    }
    if (Array.isArray(haystack)) return haystack.some((item) => same(needle, item));
    // Neither a list nor a string: false, not an exception. A badly written rule must not stop a
    // technician from sending a day's work.
    return false;
  }

  if ('and' in condition) {
    const parts = condition.and;
    if (!Array.isArray(parts) || parts.length === 0) return false;
    return parts.every((part) => evaluateCondition(part, answers));
  }

  if ('or' in condition) {
    const parts = condition.or;
    if (!Array.isArray(parts) || parts.length === 0) return false;
    return parts.some((part) => evaluateCondition(part, answers));
  }

  return false;
}

/**
 * Fields the rules demand and the answers do not supply, in the rules' own order.
 *
 * Deduplicated: two rules may demand the same field, and telling the crew twice about one empty
 * box is a defect of the platform, not a fact about their work. The order is the rules' order, so
 * the list a technician reads does not shuffle between the phone and the web.
 */
export function missingRequirements(rules: unknown, answers: Answers): MissingRequirement[] {
  if (!Array.isArray(rules)) return [];
  const found: MissingRequirement[] = [];
  const seen = new Set<string>();

  for (const rule of rules) {
    if (!isPlainObject(rule)) continue;
    const required = rule.require;
    if (!Array.isArray(required) || required.length === 0) continue;
    if (!evaluateCondition(rule.when, answers)) continue;
    const message = typeof rule.message === 'string' && rule.message ? rule.message : null;
    for (const field of required) {
      const key = String(field);
      if (seen.has(key) || isAnswered(answers[key])) continue;
      seen.add(key);
      found.push({ field: key, message });
    }
  }
  return found;
}

/** The messages a technician reads, which is what a screen shows. */
export function requirementMessages(rules: unknown, answers: Answers): string[] {
  return missingRequirements(rules, answers).map(
    (missing) => missing.message ?? `${missing.field}: es obligatorio en este caso`,
  );
}
