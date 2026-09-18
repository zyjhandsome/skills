package example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
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
}
