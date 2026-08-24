---
title: "Spring Boot Profiles: Mastering Environment-Specific Configuration"
date: 2026-08-09
tags: [Spring Boot, Profiles, Configuration, Java, DevOps]
categories: [Java]
cover: "https://images.unsplash.com/photo-1685558589023-3297b012d8bc?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to use Spring Boot Profiles to manage environment-specific configuration effectively. Explore YAML, properties, conditional beans, and best practices.
---

## Introduction

Every application eventually faces the same challenge: how to manage configuration across different environments. What works in your local development machine might not work in production, and vice versa. Database URLs, API keys, logging levels, and feature flags all need to change depending on where your application runs. Hardcoding these values is a recipe for disaster, and manual environment-specific builds are a maintenance nightmare.

Spring Boot Profiles provide a powerful and elegant solution to this age-old problem. They allow you to define separate configuration sets for different environments and activate them based on runtime conditions, such as a system property, an environment variable, or a command-line argument. This means you can package a single application artifact and deploy it to any environment without modifying a single line of code.

In this comprehensive guide, we will dive deep into Spring Boot Profiles. We'll start with the basics of defining and activating profiles, then move on to advanced techniques like profile-specific beans, YAML multi-document files, and testing. We'll also cover best practices to keep your configuration clean, secure, and maintainable. By the end, you'll be equipped to handle environment-specific configuration like a seasoned pro.

## Table of Contents

1. [What Are Spring Boot Profiles?](#what-are-spring-boot-profiles)
2. [Defining Profiles](#defining-profiles)
3. [Activating Profiles](#activating-profiles)
4. [Profile-Specific Configuration Files](#profile-specific-configuration-files)
5. [YAML Multi-Document Support](#yaml-multi-document-support)
6. [Profile-Specific Beans](#profile-specific-beans)
7. [Profiles with Maven and Gradle](#profiles-with-maven-and-gradle)
8. [Testing with Profiles](#testing-with-profiles)
9. [Best Practices and Pitfalls](#best-practices-and-pitfalls)
10. [Key Takeaways](#key-takeaways)

## What Are Spring Boot Profiles?

Spring Profiles are a core feature of the Spring Framework that allows you to map beans and configuration properties to specific environments. A profile is essentially a named logical grouping of configuration. When a profile is active, its associated beans and properties are enabled; when it's inactive, they are ignored.

Think of profiles as a way to create multiple variants of your application configuration without duplicating code. Instead of writing `application-dev.properties`, `application-test.properties`, and `application-prod.properties` and manually choosing which one to include at build time, you can have all of them in your classpath and activate the one you need at runtime.

## Defining Profiles

Profiles are defined using the `@Profile` annotation on beans or by using naming conventions for configuration files. The simplest way to define a profile is to create a properties or YAML file named `application-{profile}.properties` or `application-{profile}.yml`. For example:

- `application-dev.properties` for development
- `application-test.properties` for testing
- `application-prod.properties` for production

These files are automatically loaded when the corresponding profile is active. They override properties defined in the base `application.properties` or `application.yml` file.

### Example: application-dev.properties

```properties
server.port=8081
spring.datasource.url=jdbc:h2:mem:devdb
spring.datasource.username=sa
spring.datasource.password=
logging.level.org.springframework=DEBUG
```

### Example: application-prod.properties

```properties
server.port=80
spring.datasource.url=jdbc:mysql://prod-server:3306/proddb
spring.datasource.username=prod_user
spring.datasource.password=${DB_PASSWORD}
logging.level.org.springframework=ERROR
```

Notice how we use a placeholder `${DB_PASSWORD}` in the production file. This is a best practice to avoid hardcoding sensitive information. The actual value can be provided via environment variables or a secrets manager.

## Activating Profiles

Activating a profile is straightforward. There are several ways to do it, and you can even activate multiple profiles at once. Here are the most common methods:

### Using Application Properties

You can set the `spring.profiles.active` property in your main `application.properties` file:

```properties
spring.profiles.active=dev
```

However, this is often not ideal because it hardcodes the active profile. It's better to use external configuration.

### Using Command-Line Arguments

When running your Spring Boot application as a JAR, you can pass the profile as a command-line argument:

```bash
java -jar myapp.jar --spring.profiles.active=prod
```

This is the most flexible method because it allows you to change the profile without rebuilding or modifying any files.

### Using Environment Variables

You can set the `SPRING_PROFILES_ACTIVE` environment variable:

```bash
export SPRING_PROFILES_ACTIVE=prod
java -jar myapp.jar
```

This is particularly useful in containerized environments like Docker and Kubernetes, where environment variables are the standard way to pass configuration.

### Using Maven or Gradle

You can also set the active profile during the build process. For example, with Maven, you can use the `spring-boot-maven-plugin`:

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

Or you can pass it as a JVM system property:

```bash
mvn spring-boot:run -Dspring-boot.run.jvmArguments="-Dspring.profiles.active=dev"
```

### Programmatic Activation

In rare cases, you might need to activate a profile programmatically before the application context refreshes. This can be done in the main class:

```java
@SpringBootApplication
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(MyApplication.class);
        app.setAdditionalProfiles("dev");
        app.run(args);
    }
}
```

### Activating Multiple Profiles

You can activate multiple profiles by separating them with commas:

```bash
java -jar myapp.jar --spring.profiles.active=prod,cloud
```

This is useful when you have cross-cutting concerns like `cloud` or `metrics` that apply to multiple environments.

## Profile-Specific Configuration Files

As mentioned earlier, profile-specific files follow the naming convention `application-{profile}.properties` or `application-{profile}.yml`. These files are loaded in addition to the base `application.properties` file. Properties defined in profile-specific files override the base ones.

### Example Structure

```
src/main/resources/
├── application.properties
├── application-dev.properties
├── application-test.properties
└── application-prod.properties
```

### Base application.properties

```properties
spring.application.name=myapp
server.port=8080
spring.profiles.active=default
```

### application-dev.properties

```properties
server.port=8081
spring.datasource.url=jdbc:h2:mem:devdb
```

### application-prod.properties

```properties
server.port=80
spring.datasource.url=jdbc:mysql://prod-server:3306/proddb
```

When you run with `--spring.profiles.active=dev`, Spring Boot loads `application.properties` and then `application-dev.properties`. The `server.port` becomes `8081`, and the datasource URL points to the H2 in-memory database.

## YAML Multi-Document Support

YAML files offer a more concise way to define multiple profiles in a single file using the `---` separator. This is particularly useful when you have a small number of properties per profile.

### Example: application.yml

```yaml
spring:
  application:
    name: myapp

---
spring:
  config:
    activate:
      on-profile: dev
server:
  port: 8081
datasource:
  url: jdbc:h2:mem:devdb
  username: sa
  password: ""

---
spring:
  config:
    activate:
      on-profile: prod
server:
  port: 80
datasource:
  url: jdbc:mysql://prod-server:3306/proddb
  username: prod_user
  password: ${DB_PASSWORD}
```

Note: In Spring Boot 2.4+, the property to activate a profile in YAML is `spring.config.activate.on-profile` instead of the older `spring.profiles`. The old syntax still works but is deprecated.

This approach keeps all your environment configurations in one place, making it easier to see the differences at a glance. However, for large configurations, separate files are often more manageable.

## Profile-Specific Beans

Profiles are not limited to properties; they can also control which beans are created. This is done using the `@Profile` annotation on `@Component`, `@Service`, `@Repository`, or `@Bean` methods.

### Example: Different DataSource Beans

Suppose you want to use an embedded H2 database in development and a MySQL database in production. You can define two beans with different profiles:

```java
@Configuration
public class DataSourceConfig {

    @Bean
    @Profile("dev")
    public DataSource devDataSource() {
        return new EmbeddedDatabaseBuilder()
                .setType(EmbeddedDatabaseType.H2)
                .build();
    }

    @Bean
    @Profile("prod")
    public DataSource prodDataSource() {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl("jdbc:mysql://prod-server:3306/proddb");
        dataSource.setUsername("prod_user");
        dataSource.setPassword(System.getenv("DB_PASSWORD"));
        return dataSource;
    }
}
```

When the `dev` profile is active, the `devDataSource` bean is created; when `prod` is active, the `prodDataSource` bean is created. This gives you fine-grained control over your application's components.

### Using @Profile on Service Classes

You can also annotate service implementations:

```java
public interface NotificationService {
    void send(String message);
}

@Service
@Profile("dev")
public class ConsoleNotificationService implements NotificationService {
    @Override
    public void send(String message) {
        System.out.println("DEV: " + message);
    }
}

@Service
@Profile("prod")
public class EmailNotificationService implements NotificationService {
    @Override
    public void send(String message) {
        // Send email via SMTP
    }
}
```

Now, depending on the active profile, the appropriate implementation is injected.

## Profiles with Maven and Gradle

While profiles are primarily a runtime concept, you can integrate them with your build tool to automate activation during development and testing.

### Maven

You can configure the Spring Boot Maven plugin to use a specific profile when running the app:

```xml
<plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
    <configuration>
        <profiles>
            <profile>dev</profile>
        </profiles>
    </configuration>
</plugin>
```

Then, running `mvn spring-boot:run` will activate the `dev` profile by default. You can still override it with `-Dspring-boot.run.profiles=prod`.

### Gradle

Similarly, in Gradle, you can set the profile in the `bootRun` task:

```gradle
bootRun {
    systemProperty 'spring.profiles.active', 'dev'
}
```

Or you can pass it on the command line:

```bash
./gradlew bootRun --args='--spring.profiles.active=prod'
```

## Testing with Profiles

Profiles are also crucial for testing. You can use `@ActiveProfiles` to specify which profile to activate for a test class.

### Example

```java
@SpringBootTest
@ActiveProfiles("test")
class MyServiceTest {

    @Autowired
    private MyService myService;

    @Test
    void testSomething() {
        // ...
    }
}
```

This is especially useful when you have a separate test database or want to mock external services.

### Using @TestPropertySource

You can also combine profiles with `@TestPropertySource` to override specific properties:

```java
@SpringBootTest
@ActiveProfiles("test")
@TestPropertySource(properties = {"spring.datasource.url=jdbc:h2:mem:testdb"})
class MyRepositoryTest {
    // ...
}
```

## Best Practices and Pitfalls

### 1. Keep Sensitive Data Out of Code

Never hardcode passwords, API keys, or tokens in your profile files. Use environment variables or a secrets manager like HashiCorp Vault. Spring Boot supports `${ENV_VAR}` placeholders.

### 2. Use a Default Profile

Always have a `default` profile that works out of the box, ideally with an embedded database and minimal external dependencies. This makes it easy for new developers to get started.

### 3. Avoid Profile-Specific Code in Business Logic

Try to keep profile-specific logic in configuration classes and use interfaces to abstract behavior. This keeps your business logic clean and testable.

### 4. Be Careful with Profile Groups

Spring Boot 2.4 introduced profile groups, which allow you to group multiple profiles under a single logical name. For example:

```properties
spring.profiles.group.prod=proddb,prodcache
```

This can simplify activation, but use it judiciously to avoid confusion.

### 5. Test All Profiles

Make sure your CI/CD pipeline tests each profile at least once. It's common for a profile to work locally but fail in production due to missing environment variables or different resource availability.

### 6. Avoid Overusing Profiles

Profiles are powerful, but they can also lead to configuration sprawl. If you find yourself creating many profiles for minor variations, consider using property placeholders and external configuration instead.

### 7. Log Active Profiles

At startup, Spring Boot logs the active profiles. Make sure you check this log to verify that the correct profile is active in each environment.

## Key Takeaways

- **Spring Boot Profiles** allow you to manage environment-specific configuration without code duplication.
- **Define profiles** using `application-{profile}.properties` or `application-{profile}.yml` files, or with YAML multi-document support.
- **Activate profiles** via command-line arguments, environment variables, or programmatic configuration. The most flexible is `--spring.profiles.active=prod`.
- **Profile-specific beans** can be created using `@Profile` on `@Bean` methods or component classes, enabling different implementations per environment.
- **Integrate with Maven/Gradle** to streamline local development and testing.
- **Use `@ActiveProfiles`** in tests to ensure tests run against the intended configuration.
- **Follow best practices**: keep secrets out of code, use a default profile, and test all profiles in CI/CD.

By mastering Spring Boot Profiles, you can make your application truly environment-agnostic, reducing deployment risks and improving maintainability. Happy coding!