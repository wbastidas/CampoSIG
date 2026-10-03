plugins {
    kotlin("jvm")
}

// The field logic of the app — session, day inbox, guided flow, times, evidence, position — as a
// plain Kotlin/JVM module, for the same reason `core:sync` is one (ADR-010): the decisions that
// make or break a day in the field are tested on the JVM, in CI, without an SDK, an emulator or a
// device. The Android layer (Compose screens, CameraX, ExifInterface, BiometricPrompt, Room)
// renders and persists; it does not decide.

dependencies {
    implementation(project(":core:sync"))
    testImplementation(kotlin("test"))
    // Test-only, to read the corpora under `forms/contract/` shared with the backend (Apache-2.0).
    testImplementation("com.google.code.gson:gson:2.11.0")
}

tasks.test {
    useJUnitPlatform()
    testLogging { events("passed", "failed", "skipped") }
}
