package example;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityManagerFactory;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.servlet.Filter;
import org.hibernate.SessionFactory;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.orm.hibernate5.support.OpenSessionInViewFilter;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Repository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@SpringBootApplication
public class FixtureApplication {
    public static void main(String[] args) {
        SpringApplication.run(FixtureApplication.class, args);
    }

    @Bean
    SessionFactory sessionFactory(EntityManagerFactory emf) {
        return emf.unwrap(SessionFactory.class);
    }

    @Bean
    FilterRegistrationBean<Filter> openSessionInView(SessionFactory sessionFactory) {
        OpenSessionInViewFilter filter = new OpenSessionInViewFilter();
        filter.setSessionFactory(sessionFactory);
        FilterRegistrationBean<Filter> bean = new FilterRegistrationBean<>(filter);
        bean.setName("openSessionInViewFilter");
        bean.addUrlPatterns("/*");
        return bean;
    }

    @Bean
    ApplicationRunner seed(OwnerRepository owners) {
        return args -> {
            if (owners.count() > 0) {
                return;
            }
            Owner owner = new Owner();
            owner.name = "Lin";
            owner.birthday = LocalDate.of(2000, 1, 2);
            Pet pet = new Pet();
            pet.name = "Neko";
            pet.owner = owner;
            owner.pets.add(pet);
            owners.save(owner);
        };
    }
}

@Entity
class Owner {
    @Id @GeneratedValue
    Long id;
    String name;
    LocalDate birthday;
    @OneToMany(mappedBy = "owner", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    List<Pet> pets = new ArrayList<>();
}

@Entity
class Pet {
    @Id @GeneratedValue
    Long id;
    String name;
    @ManyToOne(fetch = FetchType.LAZY)
    Owner owner;
}

@Repository
interface OwnerRepository extends JpaRepository<Owner, Long> {}

@RestController
class OwnerController {
    private final SessionFactory sessionFactory;

    OwnerController(SessionFactory sessionFactory) {
        this.sessionFactory = sessionFactory;
    }

    @GetMapping("/owners/{id}")
    Map<String, Object> owner(@PathVariable long id) {
        Owner owner = sessionFactory.getCurrentSession().get(Owner.class, id);
        if (owner == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }
        return Map.of(
            "id", owner.id,
            "name", owner.name,
            "birthday", owner.birthday,
            "pets", owner.pets.stream().map(pet -> pet.name).toList());
    }
}
