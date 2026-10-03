package ec.sigec.campo.field

import java.security.SecureRandom
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** RF-003: «en modo avión, tras reiniciar el teléfono, el usuario entra con PIN o huella y ve sus OT». */
class OfflineSessionTest {
    private val policy = SessionPolicy()
    private val day = SessionPolicy.DAY
    private val t0 = 1_790_000_000_000L
    private val pin = PinHash.create("4826", SecureRandom())

    private fun session(loginAt: Long = t0, seen: Long = t0, attempts: Int = 0) =
        OfflineSession("kc|tecnico", loginAt, seen, pin, attempts)

    @Test
    fun `rf 003 within seven days the pin unlocks after a reboot`() {
        val (_, unlocked) = SessionGate.tryPin(session(), "4826", t0 + 6 * day, policy)
        assertTrue(unlocked)
    }

    @Test
    fun `rf 003 on the eighth day a correct pin is still not enough`() {
        val now = t0 + 7 * day + 1
        assertEquals(SessionVerdict.ONLINE_LOGIN_REQUIRED, SessionGate.evaluate(session(), now, policy))
        assertFalse(SessionGate.tryPin(session(), "4826", now, policy).second)
    }

    @Test
    fun `the parameter changes the window`() {
        val three = SessionPolicy(maxOfflineDays = 3)
        assertEquals(SessionVerdict.ONLINE_LOGIN_REQUIRED, SessionGate.evaluate(session(), t0 + 4 * day, three))
        assertFailsWith<IllegalArgumentException> { SessionPolicy(maxOfflineDays = 0) }
    }

    @Test
    fun `a wrong pin counts and enough of them lock until an online login`() {
        var current = session()
        repeat(policy.maxPinAttempts) { current = SessionGate.tryPin(current, "0000", t0 + day, policy).first }
        assertEquals(SessionVerdict.LOCKED_OUT, SessionGate.evaluate(current, t0 + day, policy))
        assertFalse(SessionGate.tryPin(current, "4826", t0 + day, policy).second)
        val relogged = SessionGate.onlineLogin(current, t0 + day)
        assertTrue(SessionGate.tryPin(relogged, "4826", t0 + day + 1, policy).second)
    }

    @Test
    fun `a right pin resets the wrong attempts`() {
        val (after, _) = SessionGate.tryPin(session(attempts = 3), "4826", t0 + day, policy)
        assertEquals(0, after.failedAttempts)
    }

    @Test
    fun `setting the clock back a week is suspect, an hour is not`() {
        val seen = session(seen = t0 + 3 * day)
        assertEquals(SessionVerdict.CLOCK_SUSPECT, SessionGate.evaluate(seen, t0 - 4 * day, policy))
        assertEquals(SessionVerdict.UNLOCK_ALLOWED, SessionGate.evaluate(seen, t0 + 3 * day - SessionPolicy.HOUR, policy))
    }

    @Test
    fun `every attempt raises the high-water mark so the clock cannot be walked back later`() {
        val (after, _) = SessionGate.tryPin(session(), "4826", t0 + 5 * day, policy)
        assertEquals(t0 + 5 * day, after.highWaterMillis)
    }

    @Test
    fun `biometrics obey the same window as the pin`() {
        assertTrue(SessionGate.biometricUnlock(session(), t0 + day, policy).second)
        assertFalse(SessionGate.biometricUnlock(session(), t0 + 8 * day, policy).second)
    }

    @Test
    fun `a wiped phone and a phone without pin never unlock offline`() {
        assertEquals(SessionVerdict.WIPED, SessionGate.evaluate(session().copy(wiped = true), t0, policy))
        assertEquals(SessionVerdict.NO_PIN, SessionGate.evaluate(session().copy(pin = null), t0, policy))
    }

    @Test
    fun `days left is what the warning banner shows`() {
        assertEquals(7, SessionGate.daysLeft(session(), t0, policy))
        assertEquals(1, SessionGate.daysLeft(session(), t0 + 6 * day + 1, policy))
        assertEquals(0, SessionGate.daysLeft(session(), t0 + 8 * day, policy))
    }

    @Test
    fun `the pin is stored only as a salted hash and survives a restore`() {
        val restored = PinHash.restore(pin.salt, pin.hash, pin.iterations)
        assertTrue(restored.matches("4826"))
        assertFalse(restored.matches("4827"))
        val other = PinHash.create("4826", SecureRandom())
        assertFalse(other.salt.contentEquals(pin.salt), "the same pin must not hash the same twice")
    }

    @Test
    fun `trivial and malformed pins are refused`() {
        for (bad in listOf("1111", "1234", "9876", "123", "123456789", "12a4")) {
            assertFailsWith<IllegalArgumentException>(bad) { PinHash.create(bad) }
        }
    }
}
