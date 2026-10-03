package ec.sigec.campo.sync

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Tests for the retry schedule. */
class RetryPolicyTest {

    @Test
    fun `delay grows with each attempt`() {
        val policy = RetryPolicy(baseDelayMillis = 1000, maxDelayMillis = 1_000_000)
        val first = policy.delayFor(1)
        val second = policy.delayFor(2)
        val third = policy.delayFor(3)
        assertTrue(first < second, "el segundo reintento debe esperar más")
        assertTrue(second < third, "el tercero más aún")
    }

    @Test
    fun `delay is capped`() {
        val policy = RetryPolicy(baseDelayMillis = 1000, maxDelayMillis = 10_000)
        // Cap plus jitter, and jitter is a quarter of the cap at most.
        assertTrue(policy.delayFor(30) <= 10_000 + 2_500)
    }

    @Test
    fun `a very high attempt count does not overflow`() {
        // A shift by more than 62 would wrap to a negative delay and retry instantly, forever.
        val policy = RetryPolicy(baseDelayMillis = 1000, maxDelayMillis = 10_000)
        assertTrue(policy.delayFor(1000) > 0, "el retardo nunca debe volverse negativo")
    }

    @Test
    fun `jitter spreads retries that would otherwise collide`() {
        // A crew driving back into town brings a dozen phones online in the same minute.
        // Without jitter they would all retry in lockstep.
        val policy = RetryPolicy(baseDelayMillis = 60_000, maxDelayMillis = 3_600_000)
        val delays = (1..8).map { policy.delayFor(it) }
        assertEquals(delays.size, delays.distinct().size, "los retardos deben diferir entre sí")
    }

    @Test
    fun `budget runs out after maxAttempts`() {
        val policy = RetryPolicy(maxAttempts = 3)
        assertTrue(policy.hasBudgetLeft(2))
        assertFalse(policy.hasBudgetLeft(3))
        assertFalse(policy.hasBudgetLeft(4))
    }

    @Test
    fun `attempt zero is rejected`() {
        assertFailsWith<IllegalArgumentException> { RetryPolicy().delayFor(0) }
    }

    @Test
    fun `nonsensical configuration is rejected at construction`() {
        assertFailsWith<IllegalArgumentException> { RetryPolicy(baseDelayMillis = 0) }
        assertFailsWith<IllegalArgumentException> {
            RetryPolicy(baseDelayMillis = 1000, maxDelayMillis = 500)
        }
        assertFailsWith<IllegalArgumentException> { RetryPolicy(maxAttempts = 0) }
    }
}
