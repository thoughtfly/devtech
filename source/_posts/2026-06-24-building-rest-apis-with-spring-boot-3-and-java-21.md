---
title: "Building REST APIs with Spring Boot 3 and Java 21: A Practical Guide"
date: 2026-06-24
tags: [Java, Spring Boot, REST API, Java 21]
categories: [Java, Spring Boot]
cover:
description: A comprehensive guide to building modern REST APIs with Spring Boot 3 and Java 21 features
---

Spring Boot 3 and Java 21 represent a major leap forward for backend development. With virtual threads, record patterns, and improved observability, building REST APIs has never been more productive. In this guide, we'll walk through creating a production-ready REST API from scratch.

## Project Setup

Start with Spring Initializr or your preferred build tool. Here's a minimal Maven configuration:

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.0</version>
</parent>

<properties>
    <java.version>21</java.version>
</properties>

<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
</dependencies>
```

## Leveraging Java 21 Records for DTOs

One of the most practical uses of Java 21 records is for DTOs. They eliminate boilerplate while providing immutability out of the box:

```java
public record CreateUserRequest(
    @NotBlank String username,
    @Email String email,
    @Size(min = 8) String password
) {}

public record UserResponse(
    Long id,
    String username,
    String email,
    Instant createdAt
) {}
```

## Virtual Threads for Better Throughput

Java 21 introduces virtual threads, which are lightweight threads that dramatically improve concurrency. Enable them in Spring Boot 3 with a single property:

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

This single change can improve throughput by 2-5x for I/O-bound applications without any code changes. Under the hood, Spring Boot automatically wraps each request in a virtual thread instead of a platform thread.

## Building the Controller

With records and virtual threads in place, your controller becomes clean and focused:

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Valid @RequestBody CreateUserRequest request) {
        UserResponse user = userService.createUser(request);
        return ResponseEntity.status(201).body(user);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        return ResponseEntity.of(userService.findById(id));
    }
}
```

## Error Handling with Problem Details

Spring Boot 3 supports RFC 9457 Problem Details for standardized error responses:

```java
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidationErrors(MethodArgumentNotValidException ex) {
        var problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        problem.setTitle("Validation Error");
        problem.setDetail("The request contains invalid fields");
        
        var errors = ex.getBindingResult()
            .getFieldErrors()
            .stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .toList();
        problem.setProperty("errors", errors);
        
        return problem;
    }
}
```

## Observability with Micrometer

Spring Boot 3 includes Micrometer Tracing out of the box. Enable it with:

```yaml
management:
  tracing:
    sampling:
      probability: 1.0
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
```

Add the dependency:

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
```

Now every request is automatically traced with distributed tracing, and you can visualize request flows in Grafana or Zipkin.

## Testing the API

Spring Boot 3 makes testing straightforward:

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldCreateUser() throws Exception {
        var request = """
            {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "securePass123"
            }
            """;

        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(request))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.username").value("johndoe"));
    }
}
```

## Deployment with Docker

A production-ready Dockerfile is surprisingly minimal:

```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY target/app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

Build the image with:

```bash
docker build -t my-api:latest .
docker run -p 8080:8080 my-api:latest
```

## Key Takeaways

- Java 21 records eliminate DTO boilerplate while ensuring immutability
- Virtual threads improve I/O throughput by 2-5x with zero code changes
- Spring Boot 3's Problem Details provide standardized error responses (RFC 9457)
- Micrometer Tracing gives you distributed tracing out of the box
- Docker deployment is simpler than ever with Alpine-based JRE images
- Combined, Spring Boot 3 and Java 21 make REST API development faster, safer, and more scalable than previous versions
