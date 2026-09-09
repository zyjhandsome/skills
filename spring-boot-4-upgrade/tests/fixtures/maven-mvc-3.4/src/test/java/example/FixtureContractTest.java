package example;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class FixtureContractTest {
    @Autowired MockMvc mvc;

    @Test void preservesJsonTypesDateAndExplicitNull() throws Exception {
        mvc.perform(get("/owners/1"))
            .andExpect(status().isOk())
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andExpect(jsonPath("$.id").value(1))
            .andExpect(jsonPath("$.name").value("Lin"))
            .andExpect(jsonPath("$.birthday").value("2000-01-02"))
            .andExpect(jsonPath("$.nickname").hasJsonPath())
            .andExpect(jsonPath("$.nickname").value(nullValue()));
    }

    @Test void missingOwnerRemains404() throws Exception {
        mvc.perform(get("/owners/99")).andExpect(status().isNotFound());
    }

    @Test void rejectsInvalidBody() throws Exception {
        mvc.perform(post("/owners").contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"\"}"))
            .andExpect(status().isBadRequest());
    }

    @Test void acceptsValidBody() throws Exception {
        mvc.perform(post("/owners").contentType(MediaType.APPLICATION_JSON).content("{\"name\":\"Chen\"}"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Chen"));
    }
}
