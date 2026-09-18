package example;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class FixtureJpaTest {
    @Autowired MockMvc mvc;

    @Test void lazyPetsAreReadableOnRequest() throws Exception {
        mvc.perform(get("/owners/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("Lin"))
            .andExpect(jsonPath("$.pets[0]").value("Neko"));
    }

    @Test void dateFollowsLegacyTimestampSetting() throws Exception {
        mvc.perform(get("/owners/1").accept(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.birthday[0]").value(2000))
            .andExpect(jsonPath("$.birthday[1]").value(1))
            .andExpect(jsonPath("$.birthday[2]").value(2));
    }
}
