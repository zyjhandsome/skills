package example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
public class FixtureApplication {
    public static void main(String[] args) {
        SpringApplication.run(FixtureApplication.class, args);
    }
}

@RestController
class FixtureController {
    @GetMapping("/public/ping")
    String ping() {
        return "ok";
    }

    @GetMapping("/owners/1")
    String owner() {
        return "Lin";
    }

    @GetMapping("/admin/stats")
    String admin() {
        return "secret";
    }
}

@Configuration
@EnableWebSecurity
class FixtureSecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        // GET-only API fixture; keep the framework CSRF default. Do not turn CSRF off for form/session apps.
        return http
            .httpBasic(Customizer.withDefaults())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .build();
    }

    @Bean
    UserDetailsService users() {
        return new InMemoryUserDetailsManager(
            User.withUsername("user").password("{noop}user").roles("USER").build(),
            User.withUsername("admin").password("{noop}admin").roles("ADMIN").build());
    }
}
