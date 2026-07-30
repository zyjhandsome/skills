# Common GAV → GitHub Mapping

Quick lookup for changelog hosts. Verify the repo still publishes the artifact
before citing. Inspired by [Jodu1005/java-dependency-upgrade](https://github.com/Jodu1005/java-dependency-upgrade) `references/common_deps.md`, extended for upgrade-analysis hotspots.

| groupId | artifactId (examples) | GitHub |
|---|---|---|
| org.springframework.boot | spring-boot-starter-parent, spring-boot-dependencies | https://github.com/spring-projects/spring-boot |
| org.springframework | spring-core, spring-framework-bom | https://github.com/spring-projects/spring-framework |
| org.springframework.security | spring-security-bom | https://github.com/spring-projects/spring-security |
| org.springframework.cloud | spring-cloud-dependencies | https://github.com/spring-cloud |
| com.netflix.eureka | eureka-client, eureka-core (`1.x` / `2.0.x` line) | https://github.com/Netflix/eureka |
| org.springframework.cloud | spring-cloud-starter-netflix-eureka-client, spring-cloud-netflix-eureka-client (`4.x` / release-train line) | https://github.com/spring-cloud/spring-cloud-netflix |
| com.fasterxml.jackson.core | jackson-databind, jackson-core | https://github.com/FasterXML/jackson-databind |
| com.fasterxml.jackson | jackson-bom | https://github.com/FasterXML/jackson-bom |
| io.netty | netty-handler, netty-codec-*, netty-common | https://github.com/netty/netty |
| org.apache.lucene | lucene-core, lucene-queryparser, lucene-* | https://github.com/apache/lucene |
| commons-lang | commons-lang (2.x) | https://github.com/apache/commons-lang |
| org.apache.commons | commons-lang3 (3.x) | https://github.com/apache/commons-lang |
| org.apache.commons | commons-collections4 | https://github.com/apache/commons-collections |
| commons-io | commons-io | https://github.com/apache/commons-io |
| com.google.guava | guava | https://github.com/google/guava |
| org.projectlombok | lombok | https://github.com/projectlombok/lombok |
| org.hibernate.orm | hibernate-core | https://github.com/hibernate/hibernate-orm |
| org.mybatis | mybatis | https://github.com/mybatis/mybatis-3 |
| com.baomidou | mybatis-plus-boot-starter | https://github.com/baomidou/mybatis-plus |
| org.apache.tomcat.embed | tomcat-embed-core | https://github.com/apache/tomcat |
| org.eclipse.jetty | jetty-server | https://github.com/jetty/jetty.project |
| io.undertow | undertow-core | https://github.com/undertow-io/undertow |
| org.apache.logging.log4j | log4j-core | https://github.com/apache/logging-log4j2 |
| ch.qos.logback | logback-classic | https://github.com/qos-ch/logback |
| org.slf4j | slf4j-api | https://github.com/qos-ch/slf4j |
| org.junit.jupiter | junit-jupiter | https://github.com/junit-team/junit5 |
| org.mockito | mockito-core | https://github.com/mockito/mockito |
| org.apache.kafka | kafka-clients | https://github.com/apache/kafka |
| com.rabbitmq | amqp-client | https://github.com/rabbitmq/rabbitmq-java-client |
| cn.hutool | hutool-all | https://github.com/dromara/hutool |
| com.alibaba.fastjson2 | fastjson2 | https://github.com/alibaba/fastjson2 |
| com.squareup.okhttp3 | okhttp | https://github.com/square/okhttp |
| io.micrometer | micrometer-core | https://github.com/micrometer-metrics/micrometer |

## Notes

- `commons-lang` 2.x (`commons-lang:commons-lang`) and `commons-lang3` are **different artifacts** and a MAJOR migration (package rename).
- Netty and Jackson are often **Boot-BOM owned**; check owner before recommending a pin.
- `eureka-client` is ambiguous by name. A `1.x` / `2.0.x` version string means
  `com.netflix.eureka:eureka-client`; a `4.x` string means the Spring Cloud
  Netflix artifact. There is **no** `org.springframework.cloud.netflix` groupId on
  Maven Central — resolve the real groupId from the project graph before citing a
  changelog. Spring Cloud–side versions must be checked against the release train,
  not Maven Central “latest” alone.
- A family can **split or rename artifacts across minor lines** (e.g. Netty 4.2
  introduced `netty-codec-base` / `netty-codec-compression`, which do not exist on
  4.1). Verify per-member existence at the exact target before analyzing further.
