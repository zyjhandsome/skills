"""Lock fixture teaching invariants. These do not compile or migrate Java."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent / "fixtures"


def read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


class FixtureInvariantTests(unittest.TestCase):
    def test_mvc_stays_boot_34_with_four_http_contracts(self):
        pom = read("maven-mvc-3.4", "pom.xml")
        test = read("maven-mvc-3.4", "src", "test", "java", "example", "FixtureContractTest.java")
        self.assertIn("<version>3.4.0</version>", pom)
        self.assertIn("spring-boot-starter-web", pom)
        self.assertNotIn("spring-boot-starter-security", pom)
        self.assertNotIn("spring-boot-starter-data-jpa", pom)
        for needle in ("preservesJsonTypesDateAndExplicitNull", "missingOwnerRemains404",
                       "rejectsInvalidBody", "acceptsValidBody"):
            self.assertIn(needle, test)

    def test_security_keeps_allow_and_deny_and_forbids_global_permit(self):
        pom = read("maven-security-3.4", "pom.xml")
        app = read("maven-security-3.4", "src", "main", "java", "example", "FixtureApplication.java")
        test = read("maven-security-3.4", "src", "test", "java", "example", "FixtureSecurityTest.java")
        self.assertIn("<version>3.4.0</version>", pom)
        self.assertIn("spring-boot-starter-security", pom)
        self.assertIn("anyRequest().authenticated()", app)
        self.assertNotIn(".csrf(", app)
        self.assertNotIn("permitAll()", app.split("anyRequest")[-1])
        self.assertIn("isUnauthorized()", test)
        self.assertIn("isForbidden()", test)
        self.assertIn("httpBasic(\"user\", \"user\")", test)
        self.assertIn("httpBasic(\"admin\", \"admin\")", test)
        self.assertNotIn("spring.security.user", app + test)
        self.assertNotIn("security=false", app.lower() + test.lower())

    def test_jpa_registers_osiv_lazy_graph_and_legacy_jackson_key(self):
        pom = read("maven-jpa-3.4", "pom.xml")
        app = read("maven-jpa-3.4", "src", "main", "java", "example", "FixtureApplication.java")
        props = read("maven-jpa-3.4", "src", "main", "resources", "application.properties")
        test = read("maven-jpa-3.4", "src", "test", "java", "example", "FixtureJpaTest.java")
        self.assertIn("<version>3.4.0</version>", pom)
        self.assertIn("spring-boot-starter-data-jpa", pom)
        self.assertIn("org.springframework.orm.hibernate5.support.OpenSessionInViewFilter", app)
        self.assertIn("setSessionFactory", app)
        self.assertIn("getCurrentSession()", app)
        self.assertIn("FetchType.LAZY", app)
        self.assertIn("owner.pets", app)
        self.assertIn("spring.jpa.open-in-view=false", props)
        self.assertIn("hibernate.current_session_context_class=org.springframework.orm.hibernate5.SpringSessionContext", props)
        self.assertIn("spring.jackson.serialization.write-dates-as-timestamps=true", props)
        self.assertIn("lazyPetsAreReadableOnRequest", test)
        self.assertIn("$.birthday[0]", test)

    def test_gradle_version_owner_is_catalog_not_root(self):
        root = read("gradle-catalog-3.4", "build.gradle.kts")
        catalog = read("gradle-catalog-3.4", "gradle", "libs.versions.toml")
        service = read("gradle-catalog-3.4", "service", "build.gradle.kts")
        convention = read("gradle-catalog-3.4", "buildSrc", "src", "main", "kotlin",
                          "example.boot-conventions.gradle.kts")
        settings = read("gradle-catalog-3.4", "settings.gradle.kts")
        self.assertIn('spring-boot = "3.4.0"', catalog)
        self.assertIn('id = "org.springframework.boot"', catalog)
        self.assertIn('include("service")', settings)
        self.assertIn("alias(libs.plugins.springframework.boot)", service)
        self.assertIn('id("example.boot-conventions")', service)
        self.assertNotIn("3.4.0", root)
        self.assertNotIn("springframework.boot", root)
        self.assertNotIn("id(\"org.openrewrite", root)
        self.assertNotIn("id(\"org.springframework.boot", root)
        self.assertNotIn("3.4.0", convention)
        self.assertNotIn("org.springframework.boot", convention)

    def test_managed_parent_still_shows_core_override_trap(self):
        parent = read("managed-parent", "parent", "pom.xml")
        app = read("managed-parent", "app", "pom.xml")
        self.assertIn("<version>3.5.14</version>", parent)
        self.assertIn("<spring-boot.version>4.0.7</spring-boot.version>", app)
        self.assertIn("explicit-management", app)
        self.assertIn("spring-boot-starter-webmvc", app)


if __name__ == "__main__":
    unittest.main()
