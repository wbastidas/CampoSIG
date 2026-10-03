plugins {
    kotlin("jvm")
}

// No toolchain pin: the module compiles on whatever JDK the environment provides and
// targets Java 17 bytecode, which is Android's level. Pinning a toolchain would force a
// download that a locked-down build machine may not be able to make.

dependencies {
    // Deliberately minimal. No Android, no networking library, no serialisation framework:
    // this module is pure decision logic, so its tests need no device and no server.
    testImplementation(kotlin("test"))

    // Test-only, and only to read `forms/contract/validation-cases.json` — the corpus the
    // backend, the web and this module all run so their validation cannot drift (I5). It never
    // reaches the APK, so the module's runtime stays free of serialisation frameworks and the
    // app carries nothing new. Apache-2.0, which rule 10 allows.
    testImplementation("com.google.code.gson:gson:2.11.0")
}

tasks.test {
    useJUnitPlatform()
    testLogging { events("passed", "failed", "skipped") }
}
