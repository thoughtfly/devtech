---
title: "Building Custom Spring Boot Starters: When and How"
date: 2026-08-04
tags: [Spring Boot, Auto-Configuration, Starters, Java]
categories: [Java]
cover: "https://images.unsplash.com/photo-1611366364438-f516bd3ce3fa?w=1200&q=80&fit=crop&fm=webp"
description: Learn when to build custom Spring Boot starters and how to create them step-by-step with auto-configuration, custom properties, and conditional beans.
---

## Introduction

Spring Boot has revolutionized Java development by simplifying configuration and dependency management. One of its most powerful features is the starter mechanism—a set of convenient dependency descriptors that bring in the right libraries and auto-configure them. But what happens when you have a cross-cutting concern that you want to share across multiple projects? Or when you find yourself repeating the same configuration in every new service? The answer lies in building your own custom Spring Boot starter.

In this post, we'll dive deep into when you should build a custom starter and how to create one from scratch. You'll learn about auto-configuration, conditional annotations, custom properties, and how to package everything into a reusable module. By the end, you'll have a solid understanding of how to create a production-ready starter that saves time and enforces consistency across your ecosystem.

## Why Build a Custom Starter?

Before we jump into the how, let's first understand the when. A custom starter is a great fit when you have:

- **Shared infrastructure**: Multiple services need the same logging, security, or messaging configuration.
- **Reusable business logic**: You have a library that requires specific setup, and you want to eliminate boilerplate.
- **Consistency enforcement**: You want to ensure every service follows the same configuration standards.
- **Reduced onboarding time**: New developers can get a service up and running with minimal configuration.

On the flip side, avoid building a starter if:
- The logic is only used in one project.
- The configuration is trivial (a few lines in `application.yml`).
- You don't have a stable API yet—starters are contracts, and breaking changes are costly.

## Anatomy of a Spring Boot Starter

A Spring Boot starter typically consists of two parts:
1. **The autoconfigure module**: Contains the auto-configuration classes.
2. **The starter module**: Contains the dependency management (usually a POM file) that pulls in the autoconfigure module and any required libraries.

In practice, you can combine them into a single module, but splitting them is a best practice, especially if you want to expose the autoconfigure module separately for more flexibility.

## Step-by-Step: Building a Custom Starter

Let's build a simple starter that provides a `GreetingService` and auto-configures it based on properties. We'll call it `greeting-spring-boot-starter`.

### Step 1: Create the Project Structure

We'll use Maven for simplicity. Create a multi-module project with two modules: `greeting-spring-boot-autoconfigure` and `greeting-spring-boot-starter`.

```
greeting-starter-parent/
  pom.xml
  greeting-spring-boot-autoconfigure/
    pom.xml
    src/main/java/...
    src/main/resources/META-INF/spring.factories
  greeting-spring-boot-starter/
    pom.xml
```

### Step 2: Define the Service and Properties

In the autoconfigure module, create the service class and a properties class.

```java
// GreetingService.java
public class GreetingService {
    private final String prefix;
    private final String suffix;

    public GreetingService(String prefix, String suffix) {
        this.prefix = prefix;
        this.suffix = suffix;
    }

    public String greet(String name) {
        return prefix + " " + name + " " + suffix;
    }
}
```

```java
// GreetingProperties.java
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "greeting")
public class GreetingProperties {
    private String prefix = "Hello";
    private String suffix = "!";

    // getters and setters
}
```

### Step 3: Create the Auto-Configuration Class

Now, create the auto-configuration class that creates the `GreetingService` bean when certain conditions are met.

```java
// GreetingAutoConfiguration.java
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConditionalOnClass(GreetingService.class)
@EnableConfigurationProperties(GreetingProperties.class)
public class GreetingAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    @ConditionalOnProperty(prefix = "greeting", name = "enabled", havingValue = "true", matchIfMissing = true)
    public GreetingService greetingService(GreetingProperties properties) {
        return new GreetingService(properties.getPrefix(), properties.getSuffix());
    }
}
```

### Step 4: Register the Auto-Configuration

Spring Boot discovers auto-configurations via the `spring.factories` file. Create `src/main/resources/META-INF/spring.factories` in the autoconfigure module:

```
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
com.example.greeting.GreetingAutoConfiguration
```

For Spring Boot 2.7 and later, you can also use the new `AutoConfiguration.imports` file. Place it in `META-INF/spring/`:

```
com.example.greeting.GreetingAutoConfiguration
```

### Step 5: Create the Starter Module

The starter module is just a POM that depends on the autoconfigure module and any other required dependencies. In our case, we don't need extra dependencies, but we'll include the autoconfigure module.

```xml
<!-- greeting-spring-boot-starter/pom.xml -->
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>greeting-spring-boot-starter</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>

  <dependencies>
    <dependency>
      <groupId>com.example</groupId>
      <artifactId>greeting-spring-boot-autoconfigure</artifactId>
      <version>1.0.0</version>
    </dependency>
  </dependencies>
</project>
```

That's it! You now have a working custom starter. When a project includes this starter, it will automatically get a `GreetingService` bean unless it defines its own or disables it via properties.

## Advanced Configuration Techniques

### Conditional Annotations

Spring Boot provides a rich set of conditional annotations. Let's explore some common ones:

- `@ConditionalOnClass` / `@ConditionalOnMissingClass`: Checks for the presence/absence of classes on the classpath.
- `@ConditionalOnBean` / `@ConditionalOnMissingBean`: Checks for the presence/absence of beans.
- `@ConditionalOnProperty`: Checks if a property is set to a certain value.
- `@ConditionalOnWebApplication` / `@ConditionalOnNotWebApplication`: Checks the application type.
- `@ConditionalOnExpression`: SpEL expression evaluation.

Use these to make your starter flexible and avoid conflicts with user-defined beans.

### Ordering Auto-Configurations

If your starter depends on other auto-configurations, you can control the order using `@AutoConfigureBefore`, `@AutoConfigureAfter`, and `@AutoConfigureOrder`. For example:

```java
@AutoConfigureAfter(DataSourceAutoConfiguration.class)
public class MyStarterAutoConfiguration {
}
```

### Custom Properties with Validation

You can add validation to your properties class using JSR-303 annotations. For example:

```java
import javax.validation.constraints.NotEmpty;

@ConfigurationProperties(prefix = "greeting")
@Validated
public class GreetingProperties {
    @NotEmpty
    private String prefix;
    // ...
}
```

This ensures that misconfigured properties fail fast at startup.

### Providing Defaults and Overriding

Always provide sensible defaults in your properties class. Users can override them via `application.yml` or environment variables. For example:

```yaml
greeting:
  prefix: "Hi"
  suffix: "!"
  enabled: true
```

### Auto-Configuration Metadata

To get IDE support for your properties, you can generate metadata. Add the dependency `spring-boot-configuration-processor` as an optional dependency in your autoconfigure module:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-configuration-processor</artifactId>
  <optional>true</optional>
</dependency>
```

This will generate `spring-configuration-metadata.json` at compile time, enabling autocomplete in IntelliJ and Eclipse.

## Testing Your Starter

Testing is crucial. You should write integration tests that verify the auto-configuration works in different scenarios. Use `@SpringBootTest` with a minimal application context.

```java
@SpringBootTest(classes = GreetingAutoConfiguration.class)
class GreetingAutoConfigurationTest {

    @Autowired
    private GreetingService greetingService;

    @Test
    void testGreeting() {
        assertEquals("Hello World!", greetingService.greet("World"));
    }
}
```

You can also test conditional behavior by setting properties via `@TestPropertySource`.

## Best Practices

- **Keep the starter thin**: The starter should only contain dependencies and a reference to the autoconfigure module. Put all logic in the autoconfigure module.
- **Use `@ConditionalOnMissingBean`**: Always allow users to override your beans.
- **Provide clear documentation**: Include a README with usage examples and all available properties.
- **Version your starter**: Use Semantic Versioning; breaking changes should bump the major version.
- **Avoid circular dependencies**: If your starter depends on other starters, be careful with auto-configuration order.
- **Don't over-engineer**: Start with a simple starter and iterate as needs grow.

## Real-World Example: A Simple Logging Starter

Let's say you want to standardize logging across services. You could create a starter that automatically configures a `LoggingAspect` for method execution time. Here's a snippet:

```java
@Aspect
@Component
public class LoggingAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();
        Object proceed = joinPoint.proceed();
        long executionTime = System.currentTimeMillis() - start;
        System.out.println(joinPoint.getSignature() + " executed in " + executionTime + "ms");
        return proceed;
    }
}
```

In your auto-configuration, you'd conditionally enable the aspect based on a property like `logging.aspect.enabled`.

## Conclusion

Custom Spring Boot starters are a powerful way to encapsulate configuration and promote consistency across your organization. By following the steps outlined above, you can create a starter that is easy to use, flexible, and robust. Remember to test thoroughly, document well, and version carefully. Happy coding!

## Key Takeaways

- **When to build**: Build a starter when you have shared infrastructure, reusable logic, or a need for consistency across multiple projects. Avoid over-engineering for single-use cases.
- **Anatomy**: A starter typically consists of an autoconfigure module and a starter module (POM). Keep them separate for flexibility.
- **Auto-configuration**: Use `@Configuration` and conditional annotations like `@ConditionalOnClass`, `@ConditionalOnMissingBean`, and `@ConditionalOnProperty` to make your starter smart.
- **Registration**: Register your auto-configuration via `spring.factories` or the newer `AutoConfiguration.imports` file.
- **Properties**: Use `@ConfigurationProperties` with defaults and optional validation. Generate metadata for IDE support.
- **Testing**: Write integration tests to verify behavior under different configurations.
- **Best practices**: Always allow overrides, keep the starter thin, document thoroughly, and version with care.