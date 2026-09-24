package ec.sigec.campo.sync

/**
 * The outbox: what the device has captured and not yet delivered (RF-101 to RF-104).
 *
 * This is the highest-risk logic in the platform. A technician can spend a day in a place
 * with no signal, and everything they recorded exists only here until it reaches the server.
 * So this module has no Android dependency and no networking: it decides *what to send next*
 * and *what to do when sending fails*, and nothing else. That makes it testable on the JVM,
 * exhaustively, without a device or a server.
 *
 * Two invariants the rest of the system relies on:
 *
 *  - **Nothing is ever dropped.** An operation leaves the outbox only when the server has
 *    confirmed it. A failure moves it back to pending or parks it for a human, never away.
 *  - **Re-sending is safe.** Every operation carries a stable `id` generated on the device,
 *    and the server treats it as an idempotency key. A reply lost on the way back costs a
 *    duplicate request, never duplicate data.
 */

/** What an outbox entry is trying to deliver. */
public enum class OperationKind {
    /** A state change: arrival, start, field closure. Smallest and most urgent. */
    WORK_ORDER_TRANSITION,

    /** Form answers — the substance of the work. */
    FORM_RESPONSE,

    /** A low-resolution preview, so a supervisor can start reviewing before photos arrive. */
    PHOTO_THUMBNAIL,

    /** The full photograph. Large. */
    PHOTO_FULL,

    /** Captured audio, kept only where the area requires it as evidence. */
    AUDIO,

    /** Corrections that feed model training. Valuable, never urgent. */
    TRAINING_SAMPLE,
}

/**
 * Upload order (RF-103).
 *
 * The order is not arbitrary. On a 256 kbps link a supervisor must learn that the crew
 * closed the work order before the photographs arrive, because the state is what unblocks
 * the next step. Training data goes last because nobody is waiting for it.
 */
public enum class UploadPriority(public val rank: Int) {
    STATE_AND_DATA(0),
    THUMBNAILS(1),
    FULL_PHOTOS(2),
    AUDIO(3),
    TRAINING_DATA(4),
    ;

    public companion object {
        public fun of(kind: OperationKind): UploadPriority = when (kind) {
            OperationKind.WORK_ORDER_TRANSITION, OperationKind.FORM_RESPONSE -> STATE_AND_DATA
            OperationKind.PHOTO_THUMBNAIL -> THUMBNAILS
            OperationKind.PHOTO_FULL -> FULL_PHOTOS
            OperationKind.AUDIO -> AUDIO
            OperationKind.TRAINING_SAMPLE -> TRAINING_DATA
        }
    }
}

/** Where an operation is in its life. */
public enum class OperationState {
    PENDING,
    IN_FLIGHT,
    SENT,

    /**
     * Failed in a way a human must look at: the server rejected the content, or the retry
     * budget ran out. Never discarded — a technician's work is not ours to throw away.
     */
    PARKED,
}

/** What the network can carry right now, which decides what is worth attempting. */
public enum class NetworkQuality {
    NONE,

    /** Metered or slow: send what is small and urgent, hold the heavy payloads. */
    CONSTRAINED,

    UNMETERED,
    ;

    /** Whether a priority band may be attempted on this connection. */
    public fun allows(priority: UploadPriority): Boolean = when (this) {
        NONE -> false
        // Deliberately narrow: on a constrained link, thumbnails are the most that should
        // compete with state changes, and training data must never spend a technician's data.
        CONSTRAINED -> priority.rank <= UploadPriority.THUMBNAILS.rank
        UNMETERED -> true
    }
}

/**
 * One thing to deliver.
 *
 * @param id generated on the device and stable across retries: the server's idempotency key.
 * @param workOrderId the work order this belongs to, so a reassignment can find its data.
 * @param sizeBytes payload size, used to keep a batch within a sensible transfer budget.
 * @param attempts how many delivery attempts have been made.
 * @param notBeforeMillis earliest time a retry may be attempted, set by the backoff policy.
 */
public data class SyncOperation(
    val id: String,
    val kind: OperationKind,
    val workOrderId: String,
    val createdAtMillis: Long,
    val sizeBytes: Long = 0,
    val state: OperationState = OperationState.PENDING,
    val attempts: Int = 0,
    val notBeforeMillis: Long = 0,
    val lastError: String? = null,
) {
    val priority: UploadPriority get() = UploadPriority.of(kind)

    /** Whether this may be attempted at [nowMillis] over [network]. */
    public fun isReady(nowMillis: Long, network: NetworkQuality): Boolean =
        state == OperationState.PENDING &&
            nowMillis >= notBeforeMillis &&
            network.allows(priority)
}

/**
 * Retry schedule: exponential with a cap, plus deterministic jitter.
 *
 * Jitter matters more here than in most systems. A crew that regains signal as it drives
 * back into town brings a dozen phones onto the network within the same minute; without
 * jitter they would all retry in lockstep and beat on the server together.
 *
 * @param maxAttempts after this many failures an operation is parked for a human, not dropped.
 */
public class RetryPolicy(
    private val baseDelayMillis: Long = 30_000,
    private val maxDelayMillis: Long = 6 * 60 * 60 * 1000,
    public val maxAttempts: Int = 12,
) {
    init {
        require(baseDelayMillis > 0) { "baseDelayMillis debe ser positivo" }
        require(maxDelayMillis >= baseDelayMillis) { "maxDelayMillis no puede ser menor que el base" }
        require(maxAttempts > 0) { "maxAttempts debe ser positivo" }
    }

    /** Delay before attempt number [attempts] (1 means the first retry). */
    public fun delayFor(attempts: Int): Long {
        require(attempts >= 1) { "attempts debe ser al menos 1" }
        // Shift rather than pow, and capped before overflow can happen.
        val exponent = (attempts - 1).coerceAtMost(30)
        val raw = baseDelayMillis shl exponent
        val capped = if (raw <= 0 || raw > maxDelayMillis) maxDelayMillis else raw
        return capped + jitterFor(attempts, capped)
    }

    /**
     * Jitter derived from the attempt count, so it is reproducible in tests.
     *
     * A real deployment mixes in the device id; the shape of the spread is what matters, and
     * a deterministic function keeps the behaviour assertable.
     */
    private fun jitterFor(attempts: Int, capped: Long): Long {
        val span = capped / 4
        if (span <= 0) return 0
        return (attempts.toLong() * 7919) % span
    }

    public fun hasBudgetLeft(attempts: Int): Boolean = attempts < maxAttempts
}

/** A batch chosen for one delivery attempt. */
public data class SyncBatch(
    val operations: List<SyncOperation>,
    /** Why the batch stops where it does, so the caller can log something useful. */
    val reason: BatchReason,
) {
    val totalBytes: Long get() = operations.sumOf { it.sizeBytes }
    val isEmpty: Boolean get() = operations.isEmpty()
}

public enum class BatchReason {
    /** Everything ready fitted in the batch. */
    ALL_READY,

    /** The count limit was reached. */
    COUNT_LIMIT,

    /** The transfer budget was reached. */
    SIZE_LIMIT,

    /** Nothing is ready: empty outbox, everything backing off, or no usable network. */
    NOTHING_READY,
}

/**
 * The outbox itself: immutable state plus pure transitions.
 *
 * Immutable on purpose. Sync runs from a background worker that the system can kill at any
 * moment, so every change produces a new state that the caller persists atomically. There is
 * no half-applied mutation to recover from.
 */
public class Outbox private constructor(
    private val entries: Map<String, SyncOperation>,
    private val policy: RetryPolicy,
) {
    public companion object {
        public fun empty(policy: RetryPolicy = RetryPolicy()): Outbox = Outbox(emptyMap(), policy)

        public fun of(
            operations: Iterable<SyncOperation>,
            policy: RetryPolicy = RetryPolicy(),
        ): Outbox = Outbox(operations.associateBy { it.id }, policy)
    }

    public val size: Int get() = entries.size

    public fun operations(): List<SyncOperation> = entries.values.toList()

    public fun find(id: String): SyncOperation? = entries[id]

    public fun countByState(state: OperationState): Int = entries.values.count { it.state == state }

    /** Operations parked for a human to look at. Visible, never silently dropped. */
    public fun parked(): List<SyncOperation> =
        entries.values.filter { it.state == OperationState.PARKED }

    /**
     * Add an operation.
     *
     * Enqueuing the same id twice is a no-op rather than an error: the capture layer may
     * retry a local save after a crash, and that must not produce two entries for one photo.
     */
    public fun enqueue(operation: SyncOperation): Outbox =
        if (entries.containsKey(operation.id)) this
        else Outbox(entries + (operation.id to operation), policy)

    public fun enqueueAll(operations: Iterable<SyncOperation>): Outbox =
        operations.fold(this) { outbox, operation -> outbox.enqueue(operation) }

    /**
     * Choose the next batch to attempt.
     *
     * Ordered by priority band, then oldest first within a band, so a photo taken this
     * morning is not overtaken by one taken this afternoon.
     *
     * @param maxOperations cap on batch size, so one attempt cannot run for an hour.
     * @param maxBytes transfer budget for this attempt.
     */
    public fun nextBatch(
        nowMillis: Long,
        network: NetworkQuality,
        maxOperations: Int = 50,
        maxBytes: Long = 8L * 1024 * 1024,
    ): SyncBatch {
        require(maxOperations > 0) { "maxOperations debe ser positivo" }
        require(maxBytes > 0) { "maxBytes debe ser positivo" }

        val ready = entries.values
            .filter { it.isReady(nowMillis, network) }
            .sortedWith(compareBy({ it.priority.rank }, { it.createdAtMillis }, { it.id }))

        if (ready.isEmpty()) return SyncBatch(emptyList(), BatchReason.NOTHING_READY)

        val chosen = mutableListOf<SyncOperation>()
        var bytes = 0L
        var reason = BatchReason.ALL_READY
        for (operation in ready) {
            if (chosen.size >= maxOperations) {
                reason = BatchReason.COUNT_LIMIT
                break
            }
            // A single payload larger than the whole budget still goes, alone: otherwise one
            // oversized photo would block the queue behind it forever.
            if (chosen.isNotEmpty() && bytes + operation.sizeBytes > maxBytes) {
                reason = BatchReason.SIZE_LIMIT
                break
            }
            chosen += operation
            bytes += operation.sizeBytes
        }
        return SyncBatch(chosen, reason)
    }

    /** Mark a batch as in flight, so a second worker cannot pick the same operations. */
    public fun markInFlight(ids: Collection<String>): Outbox =
        update(ids) { it.copy(state = OperationState.IN_FLIGHT) }

    /**
     * The server confirmed these. They leave the outbox.
     *
     * Acknowledging an id the outbox does not hold is fine: it means a previous reply was
     * lost and the server is confirming a delivery we already cleared.
     */
    public fun acknowledge(ids: Collection<String>): Outbox =
        Outbox(entries - ids.toSet(), policy)

    /**
     * Delivery failed in a way worth retrying — no signal, a timeout, a 5xx.
     *
     * Returns to pending with a backoff, until the retry budget runs out; then it parks for a
     * human. Either way the data stays.
     */
    public fun retryLater(ids: Collection<String>, nowMillis: Long, error: String?): Outbox =
        update(ids) { operation ->
            val attempts = operation.attempts + 1
            if (policy.hasBudgetLeft(attempts)) {
                operation.copy(
                    state = OperationState.PENDING,
                    attempts = attempts,
                    notBeforeMillis = nowMillis + policy.delayFor(attempts),
                    lastError = error,
                )
            } else {
                operation.copy(
                    state = OperationState.PARKED,
                    attempts = attempts,
                    lastError = error ?: "se agotaron los reintentos",
                )
            }
        }

    /**
     * The server rejected the content itself — a 4xx. Retrying would fail identically, so it
     * parks immediately for a human instead of burning the budget.
     */
    public fun park(ids: Collection<String>, error: String): Outbox =
        update(ids) { it.copy(state = OperationState.PARKED, lastError = error) }

    /** Return parked operations to the queue, after a human fixed whatever was wrong. */
    public fun requeue(ids: Collection<String>): Outbox =
        update(ids) { operation ->
            if (operation.state == OperationState.PARKED) {
                operation.copy(
                    state = OperationState.PENDING,
                    attempts = 0,
                    notBeforeMillis = 0,
                    lastError = null,
                )
            } else {
                operation
            }
        }

    /**
     * Whether everything captured for a work order has been delivered.
     *
     * This is what decides whether a reassignment may release the work order from a device
     * (RF-322). While this is false, the previous holder still has work nobody else has seen.
     */
    public fun isFullyDelivered(workOrderId: String): Boolean =
        entries.values.none { it.workOrderId == workOrderId }

    /** Operations still held for a work order, for the handover screen. */
    public fun pendingFor(workOrderId: String): List<SyncOperation> =
        entries.values.filter { it.workOrderId == workOrderId }

    private fun update(ids: Collection<String>, transform: (SyncOperation) -> SyncOperation): Outbox {
        val target = ids.toSet()
        if (target.isEmpty()) return this
        val updated = entries.mapValues { (id, operation) ->
            if (id in target) transform(operation) else operation
        }
        return Outbox(updated, policy)
    }
}
