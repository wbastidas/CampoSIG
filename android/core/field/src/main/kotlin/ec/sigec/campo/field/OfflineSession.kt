package ec.sigec.campo.field

import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * Working offline after an online login (RF-003).
 *
 * «Tras un login en línea, permite trabajar hasta N días sin red (parámetro, por defecto 7) con PIN
 * o biometría. En modo avión, tras reiniciar el teléfono, el usuario entra con PIN o huella y ve sus
 * OT.» The online login proves who the person is; the PIN or fingerprint only proves it is still
 * the same person holding the phone, so it is trusted for a bounded time and no longer.
 *
 * The clock is the weak point: a phone whose date is set back would stretch seven days forever. So
 * the session keeps the latest time it has ever seen and refuses to go backwards past a tolerance —
 * a clock that moved back an hour for a time-zone change is fine, one that moved back a week is
 * somebody extending their session, and either way the answer is «conéctese una vez».
 */
public data class SessionPolicy(
    val maxOfflineDays: Int = 7,
    val maxPinAttempts: Int = 5,
    /** How far back the clock may move (a time-zone change, an NTP correction) before it is suspect. */
    val clockRollbackToleranceMillis: Long = 2 * HOUR,
) {
    init {
        require(maxOfflineDays in 1..30) { "maxOfflineDays va de 1 a 30" }
        require(maxPinAttempts in 3..10) { "maxPinAttempts va de 3 a 10" }
    }

    public companion object {
        public const val HOUR: Long = 60 * 60 * 1000L
        public const val DAY: Long = 24 * HOUR
    }
}

/** What the phone keeps between reboots, encrypted with the rest of the local database (RF-100). */
public data class OfflineSession(
    val userSub: String,
    val lastOnlineLoginMillis: Long,
    /** The latest time this session has seen, online or not: the floor the clock may not go under. */
    val highWaterMillis: Long,
    val pin: PinHash?,
    val failedAttempts: Int = 0,
    /** Set when the server told this phone to wipe itself (RF-004): nothing unlocks it again. */
    val wiped: Boolean = false,
)

public enum class SessionVerdict {
    /** Unlock with PIN or fingerprint; the inbox opens. */
    UNLOCK_ALLOWED,

    /** Seven days (or the parameter) without an online login: one is needed before anything else. */
    ONLINE_LOGIN_REQUIRED,

    /** Too many wrong PINs: only an online login resets it. */
    LOCKED_OUT,

    /** The clock went back further than a time-zone change can explain. */
    CLOCK_SUSPECT,

    /** No PIN was ever set: the first online login sets one. */
    NO_PIN,

    /** The device was blocked and wiped (RF-004). */
    WIPED,
}

public object SessionGate {
    /** May this phone be unlocked offline now? Checked before showing the PIN pad, after a reboot. */
    public fun evaluate(session: OfflineSession, nowMillis: Long, policy: SessionPolicy): SessionVerdict = when {
        session.wiped -> SessionVerdict.WIPED
        session.pin == null -> SessionVerdict.NO_PIN
        nowMillis < session.highWaterMillis - policy.clockRollbackToleranceMillis ->
            SessionVerdict.CLOCK_SUSPECT
        session.failedAttempts >= policy.maxPinAttempts -> SessionVerdict.LOCKED_OUT
        nowMillis - session.lastOnlineLoginMillis > policy.maxOfflineDays * SessionPolicy.DAY ->
            SessionVerdict.ONLINE_LOGIN_REQUIRED
        else -> SessionVerdict.UNLOCK_ALLOWED
    }

    /** The days left before an online login is needed, for the banner that warns ahead of time. */
    public fun daysLeft(session: OfflineSession, nowMillis: Long, policy: SessionPolicy): Int {
        val left = policy.maxOfflineDays * SessionPolicy.DAY - (nowMillis - session.lastOnlineLoginMillis)
        return if (left <= 0) 0 else ((left + SessionPolicy.DAY - 1) / SessionPolicy.DAY).toInt()
    }

    /** A successful online login: the offline window restarts and wrong attempts are forgotten. */
    public fun onlineLogin(session: OfflineSession, nowMillis: Long): OfflineSession = session.copy(
        lastOnlineLoginMillis = nowMillis,
        highWaterMillis = maxOf(session.highWaterMillis, nowMillis),
        failedAttempts = 0,
    )

    /**
     * Try a PIN offline. A right PIN only unlocks when [evaluate] allows it — a correct PIN on the
     * eighth day is still the eighth day.
     *
     * @return the updated session and whether it unlocked.
     */
    public fun tryPin(
        session: OfflineSession,
        candidate: String,
        nowMillis: Long,
        policy: SessionPolicy,
    ): Pair<OfflineSession, Boolean> {
        val seen = session.copy(highWaterMillis = maxOf(session.highWaterMillis, nowMillis))
        if (evaluate(session, nowMillis, policy) != SessionVerdict.UNLOCK_ALLOWED) return seen to false
        val pin = session.pin ?: return seen to false
        return if (pin.matches(candidate)) {
            seen.copy(failedAttempts = 0) to true
        } else {
            seen.copy(failedAttempts = session.failedAttempts + 1) to false
        }
    }

    /**
     * A fingerprint the platform's biometric prompt accepted. The platform proves the finger; this
     * decides whether a finger is enough right now, by the same rule as a PIN.
     */
    public fun biometricUnlock(session: OfflineSession, nowMillis: Long, policy: SessionPolicy): Pair<OfflineSession, Boolean> {
        val seen = session.copy(highWaterMillis = maxOf(session.highWaterMillis, nowMillis))
        return seen to (evaluate(session, nowMillis, policy) == SessionVerdict.UNLOCK_ALLOWED)
    }
}

/**
 * A PIN, stored only as a salted PBKDF2 hash. `javax.crypto` is in the JDK and in Android, so the
 * same code runs in both and no library enters the APK.
 */
public class PinHash private constructor(
    public val salt: ByteArray,
    public val hash: ByteArray,
    public val iterations: Int,
) {
    public fun matches(candidate: String): Boolean =
        MessageDigest.isEqual(derive(candidate, salt, iterations), hash)

    public companion object {
        private const val DEFAULT_ITERATIONS = 120_000
        private const val KEY_BITS = 256
        private val PIN_SHAPE = Regex("[0-9]{4,8}")

        /** @throws IllegalArgumentException for a PIN that is not 4 to 8 digits, or a trivial one. */
        public fun create(pin: String, random: SecureRandom = SecureRandom()): PinHash {
            require(PIN_SHAPE.matches(pin)) { "el PIN son de 4 a 8 dígitos" }
            require(!isTrivial(pin)) { "el PIN no puede ser una secuencia ni un dígito repetido" }
            val salt = ByteArray(16).also(random::nextBytes)
            return PinHash(salt, derive(pin, salt, DEFAULT_ITERATIONS), DEFAULT_ITERATIONS)
        }

        public fun restore(salt: ByteArray, hash: ByteArray, iterations: Int): PinHash =
            PinHash(salt.copyOf(), hash.copyOf(), iterations)

        /** 0000, 1111, 1234, 4321: the PINs anyone tries first. */
        public fun isTrivial(pin: String): Boolean {
            if (pin.toSet().size == 1) return true
            val steps = pin.zipWithNext { a, b -> b - a }.toSet()
            return steps == setOf(1) || steps == setOf(-1)
        }

        private fun derive(pin: String, salt: ByteArray, iterations: Int): ByteArray {
            val spec = PBEKeySpec(pin.toCharArray(), salt, iterations, KEY_BITS)
            try {
                return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
            } finally {
                spec.clearPassword()
            }
        }
    }
}
