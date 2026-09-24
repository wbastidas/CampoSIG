plugins {
    kotlin("jvm") version "2.1.0" apply false
}

// Java 17 is Android's target bytecode level, so the shared module stays compatible with
// the app even though it builds on the JVM.
subprojects {
    // Java and Kotlin must agree on the target, or Gradle refuses the build. There are no
    // Java sources in core:sync, but the task still exists and still has to match.
    tasks.withType<JavaCompile>().configureEach {
        sourceCompatibility = "17"
        targetCompatibility = "17"
    }

    tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
            // Warnings are defects in this module: it runs unattended on a phone in the
            // field, where a subtle nullability slip is expensive to diagnose.
            allWarningsAsErrors.set(true)
        }
    }
}
