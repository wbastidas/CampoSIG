// Android project. Note that `core:sync` is deliberately a plain Kotlin/JVM module with no
// Android dependencies: the offline sync engine is the highest-risk logic in the whole
// platform, and keeping it platform-agnostic means it is unit-tested on the JVM rather than
// only on a device. The Android layer (Room, Compose, WorkManager) wraps it.
//
// No Esri artifacts, ever: the app carries no proprietary component and no per-device
// licence (ADR-003). CI fails the build if one appears.

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        // google() is added here when the Android modules land; core:sync does not need it.
    }
}

rootProject.name = "sigec-campo"

include(":core:sync")
