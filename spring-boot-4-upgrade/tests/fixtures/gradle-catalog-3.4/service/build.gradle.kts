plugins {
    alias(libs.plugins.springframework.boot)
    alias(libs.plugins.spring.dependency.management)
    id("example.boot-conventions")
}

group = "example"
version = "1.0.0"

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
