package example;

import java.time.LocalDate;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
public class FixtureApplication {
    public static void main(String[] args) {
        SpringApplication.run(FixtureApplication.class, args);
    }
}

@RestController
class FixtureController {
    record Owner(long id, String name, LocalDate birthday, String nickname) {}
    record CreateOwner(@NotBlank String name) {}

    @GetMapping("/owners/{id}")
    Owner owner(@PathVariable long id) {
        if (id != 1) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }
        return new Owner(1, "Lin", LocalDate.of(2000, 1, 2), null);
    }

    @PostMapping("/owners")
    Owner create(@Valid @RequestBody CreateOwner request) {
        return new Owner(2, request.name(), LocalDate.of(2000, 1, 2), null);
    }
}
