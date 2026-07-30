---
title: "Migrating from Spring Boot 2.x to 3.x: A Complete Checklist"
date: 2026-07-30
tags: [Spring Boot, Java, Migration, Jakarta EE, Spring Security]
categories: [Java]
cover: "https://images.unsplash.com/photo-1762340915700-356b34475448?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3wxMDEwOTUyfDB8MXxyYW5kb218fHx8fHx8fHwxNzg1NDA2ODU0fA&ixlib=rb-4.1.0&q=80&w=1080"
description: A practical guide for migrating Spring Boot 2.x apps to 3.x, covering Java 17, Jakarta EE, Spring Security 6, and configuration changes with a step-by-step c...
---

# Migrating from Spring Boot 2.x to 3.x: A Complete Checklist

Spring Boot 3.0 is a major milestone—the first version built on top of Spring Framework 6 and requiring Java 17 as the baseline. It brings Jakarta EE 9+, a revamped security model, native image support via GraalVM, and many performance improvements. But migrating a production application from 2.x to 3.x is not a trivial task. I've recently completed this migration for a mid-sized microservices system, and this post distills everything you need to know into a clear, actionable checklist.

## Why Migrate?

Before diving into the how, let's talk about the why. Spring Boot 2.x will reach its end of life in November 2023 (for 2.7) and November 2025 (for 2.6 LTS). Beyond security patches, you miss out on:

- **Java 17 features**: Records, sealed classes, pattern matching, and better performance.
- **Virtual threads support**: Spring Boot 3.2+ integrates with Project Loom for lightweight concurrency.
- **GraalVM native images**: Compile your app to a native binary for instant startup and lower memory.
- **Improved observability**: Micrometer 1.10+ with better tracing and metrics.
- **Jakarta EE 10**: Future-proof your codebase as Java EE is fully replaced.

## Prerequisites

- **Java 17 or later**: Spring Boot 3 requires Java 17 as a minimum. Make sure your CI/CD pipelines and local environments are updated.
- **Gradle 7.5+ or Maven 3.5+**: Older build tools may not work with the new build plugins.
- **Spring Boot 2.7.x**: The recommended starting point. If you're on an older 2.x version, first upgrade to 2.7.x to minimize breaking changes.
- **A comprehensive test suite**: Unit, integration, and end-to-end tests are your safety net.

## Step 1: Update Your Build Configuration

### Maven

Update your `pom.xml` to change the parent version and add the Spring Boot 3 BOM if needed:

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
    <relativePath/>
</parent>
```

If you use a custom parent, add the BOM:

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>3.2.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

Also update the `maven-compiler-plugin` to target Java 17:

```xml
<properties>
    <java.version>17</java.version>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
</properties>
```

### Gradle

For Gradle, update your `build.gradle`:

```groovy
plugins {
    id 'org.springframework.boot' version '3.2.0'
    id 'io.spring.dependency-management' version '1.1.4'
    id 'java'
}

group = 'com.example'
version = '0.0.1-SNAPSHOT'
sourceCompatibility = '17'

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    // ...
}
```

If you use Kotlin, ensure you're on Kotlin 1.8+.

## Step 2: Migrate from Java EE to Jakarta EE

This is the most impactful change. Spring Boot 3 replaces the `javax.*` namespace with `jakarta.*`. The migration involves:

- **Servlet**: `javax.servlet` → `jakarta.servlet`
- **Persistence**: `javax.persistence` → `jakarta.persistence`
- **Validation**: `javax.validation` → `jakarta.validation`
- **Annotations**: `javax.annotation` → `jakarta.annotation`

### How to Migrate

1. **Use a tool**: The OpenRewrite project provides automated recipes. Add this to your `pom.xml`:

```xml
<plugin>
    <groupId>org.openrewrite.maven</groupId>
    <artifactId>rewrite-maven-plugin</artifactId>
    <version>5.6.1</version>
    <configuration>
        <activeRecipes>
            <recipe>org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0</recipe>
        </activeRecipes>
    </configuration>
</plugin>
```

Then run:

```bash
mvn rewrite:run
```

2. **Manual search-and-replace**: If you prefer a hands-on approach, use your IDE's global search and replace:
   - `javax.persistence` → `jakarta.persistence`
   - `javax.validation` → `jakarta.validation`
   - `javax.servlet` → `jakarta.servlet`
   - `javax.annotation` → `jakarta.annotation`

3. **Check third-party dependencies**: Libraries like Hibernate, Tomcat, and Jersey have Jakarta-compatible versions. Ensure you're using the correct ones:
   - Hibernate 6.1+
   - Tomcat 10+
   - Thymeleaf 3.1+

## Step 3: Update Spring Security Configuration

Spring Security 6 introduces a more declarative, component-based configuration. The old `WebSecurityConfigurerAdapter` is deprecated and removed.

### Before (Spring Boot 2.x)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .authorizeRequests()
                .antMatchers("/public/**").permitAll()
                .anyRequest().authenticated()
            .and()
            .formLogin();
    }

    @Override
    protected void configure(AuthenticationManagerBuilder auth) throws Exception {
        auth.inMemoryAuthentication()
            .withUser("user").password(passwordEncoder().encode("password")).roles("USER");
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

### After (Spring Boot 3.x)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .formLogin(Customizer.withDefaults());
        return http.build();
    }

    @Bean
    public UserDetailsService users() {
        UserDetails user = User.builder()
            .username("user")
            .password(passwordEncoder().encode("password"))
            .roles("USER")
            .build();
        return new InMemoryUserDetailsManager(user);
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

Key changes:
- `authorizeRequests()` → `authorizeHttpRequests()`
- `antMatchers()` → `requestMatchers()`
- `WebSecurityConfigurerAdapter` → `SecurityFilterChain` bean
- Authentication manager is now configured via `UserDetailsService` or `AuthenticationManager` beans

## Step 4: Update Configuration Properties

Several properties have been renamed or removed. Use the Spring Boot 3 migration guide or run your app with `--debug` to see warnings.

### Common Changes

| Old Property (2.x) | New Property (3.x) |
|-------------------|--------------------|
| `server.servlet.session.timeout` | `server.servlet.session.timeout` (unchanged, but now uses `Duration`) |
| `spring.datasource.hikari.connection-timeout` | `spring.datasource.hikari.connection-timeout` (now uses `Duration`) |
| `spring.jpa.hibernate.ddl-auto` | `spring.jpa.hibernate.ddl-auto` (unchanged) |
| `spring.mvc.servlet.load-on-startup` | Removed, use `@Order` on `WebMvcConfigurer` |
| `spring.flyway.enabled` | `spring.flyway.enabled` (unchanged) |
| `management.metrics.export.prometheus.enabled` | `management.prometheus.metrics.export.enabled` |

### Duration Format

Spring Boot 3 now expects durations in the ISO-8601 format (e.g., `PT30S` for 30 seconds) or with a suffix (`30s`). Update your `application.yml`:

```yaml
server:
  servlet:
    session:
      timeout: 30m  # or PT30M

spring:
  datasource:
    hikari:
      connection-timeout: 10s
```

## Step 5: Update Spring Data and JPA

Spring Data 2022.0+ aligns with Jakarta EE. The main changes:

- **Repository interfaces**: No change in API, but the underlying implementation uses Jakarta Persistence.
- **Query methods**: Still work the same way.
- **Pagination**: `PageRequest` now uses `org.springframework.data.domain.PageRequest` (unchanged).

### Hibernate 6

Hibernate 6 is the default. Key differences:

- **Sequence handling**: `GenerationType.AUTO` now uses `SEQUENCE` by default instead of `TABLE`. If you rely on `TABLE`, explicitly set `@GeneratedValue(strategy = GenerationType.TABLE)`.
- **Naming strategies**: The default physical naming strategy changed from `PhysicalNamingStrategyStandardImpl` to `CamelCaseToUnderscoresNamingStrategy`. This may break existing table mappings. To keep the old behavior:

```yaml
spring:
  jpa:
    hibernate:
      naming:
        physical-strategy: org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl
```

- **Boolean mapping**: Hibernate 6 maps `boolean` to `BOOLEAN` instead of `TINYINT` (for MySQL). Use `@Column(columnDefinition = "TINYINT")` if needed.

## Step 6: Update Actuator and Metrics

Spring Boot 3 uses Micrometer 1.10, which has a new `Observation` API for metrics and tracing.

### Metrics

- `CounterService` and `GaugeService` are deprecated. Use `MeterRegistry` directly.
- The `@Timed` annotation is now in `io.micrometer.core.annotation.Timed`.

### Health Indicators

Custom health indicators now implement `HealthIndicator` (same interface), but the response format changed. Ensure your custom health checks return proper statuses.

### Tracing

Spring Boot 3 integrates with Micrometer Tracing. Replace Spring Cloud Sleuth dependencies:

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
```

And configure:

```yaml
management:
  tracing:
    sampling:
      probability: 1.0
```

## Step 7: Handle Deprecations and Removals

Spring Boot 3 removes many deprecated APIs from 2.x. Watch for:

- **`spring.factories`**: Auto-configuration registration now uses `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`.
- **`RestTemplate`**: Not removed, but `WebClient` is preferred for new code.
- **`@ConfigurationProperties`**: The `locations` attribute is removed. Use `@PropertySource` instead.
- **`spring-boot-starter-web`**: Still works, but `spring-boot-starter-webflux` is recommended for reactive apps.

## Step 8: Test Thoroughly

Run your full test suite early and often. Common issues:

- **Integration tests**: Ensure test configuration uses Jakarta EE compatible libraries.
- **Mockito**: Update to Mockito 5+.
- **Testcontainers**: Use version 1.18+ for Jakarta support.
- **Spring Cloud**: If you use Spring Cloud, ensure you're on the 2022.0.x (Kilburn) release train.

### Sample Test Configuration

```java
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void testPublicEndpoint() throws Exception {
        mockMvc.perform(get("/public/health"))
            .andExpect(status().isOk());
    }
}
```

## Step 9: Check Third-Party Libraries

Update all dependencies to versions compatible with Spring Boot 3:

- **Lombok**: 1.18.28+
- **MapStruct**: 1.5.5+
- **Flyway**: 9.16+
- **Liquibase**: 4.20+
- **Swagger/OpenAPI**: springdoc-openapi v2.0+
- **Thymeleaf**: 3.1+
- **Kafka**: Spring Kafka 3.0+

## Step 10: Leverage New Features

Once migrated, take advantage of Spring Boot 3's capabilities:

- **Virtual threads**: Enable with `spring.threads.virtual.enabled=true` (Spring Boot 3.2+).
- **AOT processing**: Use `spring-boot-starter-aot` for ahead-of-time compilation.
- **Native images**: Build with GraalVM using `spring-boot:build-image`.

## Complete Migration Checklist

- [ ] Update Java to 17+
- [ ] Update Spring Boot version in build file
- [ ] Replace `javax.*` with `jakarta.*`
- [ ] Update Spring Security configuration to component-based model
- [ ] Update configuration properties (durations, renamed keys)
- [ ] Adjust Hibernate 6 mappings (sequences, naming)
- [ ] Migrate from Sleuth to Micrometer Tracing
- [ ] Replace deprecated `spring.factories` with `AutoConfiguration.imports`
- [ ] Update all third-party dependencies
- [ ] Run full test suite and fix failures
- [ ] Update CI/CD pipelines for Java 17
- [ ] Deploy to staging and monitor logs
- [ ] Enable new features (virtual threads, native images) as optional

## Key Takeaways

- **Start from Spring Boot 2.7**: This is the last 2.x version and provides the smoothest upgrade path.
- **Automate the Jakarta migration**: Use OpenRewrite or IDE search-and-replace to handle the `javax` to `jakarta` namespace change.
- **Rewrite security config**: The old `WebSecurityConfigurerAdapter` is gone; embrace the new lambda-based DSL.
- **Test early, test often**: The migration touches many layers—your test suite is your best friend.
- **Don't rush**: Plan for at least a week of migration work for a medium-sized application, including testing and validation.
- **Monitor after deployment**: Use Spring Boot 3's improved observability to catch issues in production.

Migrating to Spring Boot 3 is an investment that pays off with better performance, easier maintenance, and access to the latest Java features. Use this checklist as your roadmap, and you'll be running on the latest and greatest in no time.