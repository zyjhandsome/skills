package example;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class FixtureSecurityTest {
    @Autowired MockMvc mvc;

    @Test void publicPingAllowsAnonymous() throws Exception {
        mvc.perform(get("/public/ping")).andExpect(status().isOk()).andExpect(content().string("ok"));
    }

    @Test void ownerRejectsAnonymous() throws Exception {
        mvc.perform(get("/owners/1")).andExpect(status().isUnauthorized());
    }

    @Test void ownerAllowsUser() throws Exception {
        mvc.perform(get("/owners/1").with(httpBasic("user", "user")))
            .andExpect(status().isOk()).andExpect(content().string("Lin"));
    }

    @Test void adminRejectsUser() throws Exception {
        mvc.perform(get("/admin/stats").with(httpBasic("user", "user")))
            .andExpect(status().isForbidden());
    }

    @Test void adminAllowsAdmin() throws Exception {
        mvc.perform(get("/admin/stats").with(httpBasic("admin", "admin")))
            .andExpect(status().isOk()).andExpect(content().string("secret"));
    }
}
