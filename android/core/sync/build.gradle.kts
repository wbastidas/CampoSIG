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
}

tasks.test {
    useJUnitPlatform()
    testLogging { events("passed", "failed", "skipped") }
}
