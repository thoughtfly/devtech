---
title: "Building Reactive Microservices with Spring WebFlux"
date: 2026-06-25
tags: [Spring WebFlux, Reactive Programming, Microservices, Java, Reactor]
categories: [Java]
cover:
description: Building Reactive Microservices with Spring WebFlux
---

---
title: "Building Reactive Microservices with Spring WebFlux"
date: 2025-01-15
tags: ["Spring WebFlux", "Reactive Programming", "Microservices", "Java", "Reactor"]
categories: ["Java"]
---

# Building Reactive Microservices with Spring WebFlux

In the modern era of cloud-native applications, traditional blocking I/O models are increasingly becoming a bottleneck. Every thread waiting for a database query, an HTTP call, or a file read represents wasted resources. Spring WebFlux, introduced in Spring 5, offers a paradigm shift: a fully non-blocking, reactive stack built on Project Reactor. This post dives deep into building reactive microservices with Spring WebFlux, covering architecture, practical implementation, testing, and common pitfalls.

## Why Reactive? The Performance Imperative

Before we jump into code, let's understand the "why." Traditional Spring MVC uses a thread-per-request model. Under load, this leads to thread pool exhaustion, context switching overhead, and ultimately, degraded throughput. Reactive systems, on the other hand, use a small, fixed number of threads and rely on event-driven, asynchronous processing.

Consider a microservice that calls three downstream services. With blocking I/O, each request ties up a thread for the entire duration. With WebFlux, the thread is freed while waiting for responses, allowing it to handle other requests. This results in better resource utilization and higher concurrency with fewer threads.

## Spring WebFlux Architecture

Spring WebFlux supports two programming models:

- **Annotation-based**: Similar to Spring MVC, using `@RestController`, `@RequestMapping`, etc.
- **Functional endpoints**: A more explicit, lambda-based routing DSL.

Both models are built on top of Reactor's `Flux` (for 0..N elements) and `Mono` (for 0..1 elements). The key is that these types are **reactive** — they don't block; instead, they notify subscribers when data is available.

### Core Dependencies

To get started, add the WebFlux starter to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
<dependency>
    <groupId>reactor-test</groupId>
    <artifactId>reactor-test</artifactId>
    <scope>test</scope>
</dependency>
```

## Building a Reactive REST API

Let's build a simple user management service. We'll use an embedded MongoDB with the reactive Spring Data MongoDB driver.

### Domain Model

```java
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document
public class User {
    @Id
    private String id;
    private String name;
    private String email;
    // constructors, getters, setters
}
```

### Reactive Repository

Spring Data provides reactive repositories that return `Flux` and `Mono`:

```java
import org.springframework.data.mongodb.repository.ReactiveMongoRepository;
import reactor.core.publisher.Flux;

public interface UserRepository extends ReactiveMongoRepository<User, String> {
    Flux<User> findByName(String name);
}
```

### Controller with WebFlux

```java
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/users")
public class UserController {

    private final UserRepository repository;

    public UserController(UserRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public Flux<User> getAllUsers() {
        return repository.findAll();
    }

    @GetMapping("/{id}")
    public Mono<User> getUserById(@PathVariable String id) {
        return repository.findById(id);
    }

    @PostMapping
    public Mono<User> createUser(@RequestBody User user) {
        return repository.save(user);
    }

    @DeleteMapping("/{id}")
    public Mono<Void> deleteUser(@PathVariable String id) {
        return repository.deleteById(id);
    }
}
```

Notice that the return types are `Flux` and `Mono`. The framework handles subscription and backpressure automatically.

## Reactive Communication Between Services

Microservices often need to talk to each other. With WebFlux, you use `WebClient` — a non-blocking HTTP client.

### Configuring WebClient

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .baseUrl("http://localhost:8081")
                .build();
    }
}
```

### Making Reactive Calls

```java
import reactor.core.publisher.Mono;

@Service
public class UserService {

    private final WebClient webClient;

    public UserService(WebClient webClient) {
        this.webClient = webClient;
    }

    public Mono<User> getUserFromRemote(String id) {
        return webClient.get()
                .uri("/users/{id}", id)
                .retrieve()
                .bodyToMono(User.class);
    }

    public Flux<User> getAllUsersFromRemote() {
        return webClient.get()
                .uri("/users")
                .retrieve()
                .bodyToFlux(User.class);
    }
}
```

`WebClient` is fully reactive. It doesn't block while waiting for the response, freeing the thread to handle other requests.

## Functional Endpoints: An Alternative Approach

For more explicit control, you can use the functional programming model:

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.ServerResponse;

import static org.springframework.web.reactive.function.server.RequestPredicates.*;
import static org.springframework.web.reactive.function.server.RouterFunctions.route;

@Configuration
public class UserRouter {

    @Bean
    public RouterFunction<ServerResponse> userRoutes(UserHandler handler) {
        return route(GET("/users"), handler::getAllUsers)
                .andRoute(GET("/users/{id}"), handler::getUserById)
                .andRoute(POST("/users"), handler::createUser);
    }
}

@Component
public class UserHandler {

    private final UserRepository repository;

    public UserHandler(UserRepository repository) {
        this.repository = repository;
    }

    public Mono<ServerResponse> getAllUsers(ServerRequest request) {
        return ServerResponse.ok().body(repository.findAll(), User.class);
    }

    public Mono<ServerResponse> getUserById(ServerRequest request) {
        return repository.findById(request.pathVariable("id"))
                .flatMap(user -> ServerResponse.ok().bodyValue(user))
                .switchIfEmpty(ServerResponse.notFound().build());
    }

    public Mono<ServerResponse> createUser(ServerRequest request) {
        return request.bodyToMono(User.class)
                .flatMap(repository::save)
                .flatMap(user -> ServerResponse.ok().bodyValue(user));
    }
}
```

Functional endpoints are great for fine-grained control over error handling and request processing.

## Error Handling in Reactive Streams

Error handling in reactive programming is different from traditional try-catch. You use operators like `onErrorReturn`, `onErrorResume`, and `onErrorMap`.

```java
@GetMapping("/{id}")
public Mono<User> getUserById(@PathVariable String id) {
    return repository.findById(id)
            .switchIfEmpty(Mono.error(new UserNotFoundException(id)))
            .onErrorMap(DataIntegrityViolationException.class, 
                e -> new BadRequestException("Invalid data"));
}
```

For global error handling, implement `ErrorWebExceptionHandler`:

```java
@Component
public class GlobalErrorHandler implements ErrorWebExceptionHandler {

    @Override
    public Mono<Void> handle(ServerWebExchange exchange, Throwable ex) {
        ServerHttpResponse response = exchange.getResponse();
        if (ex instanceof UserNotFoundException) {
            response.setStatusCode(HttpStatus.NOT_FOUND);
        } else {
            response.setStatusCode(HttpStatus.INTERNAL_SERVER_ERROR);
        }
        return response.writeWith(
            Mono.just(response.bufferFactory()
                .wrap(ex.getMessage().getBytes())));
    }
}
```

## Backpressure and Resilience

Backpressure is a core concept in reactive systems — it's the ability of the consumer to signal the producer to slow down. Reactor handles this automatically, but you can customize it.

```java
Flux.range(1, 1000)
    .onBackpressureBuffer(100, BufferOverflowStrategy.DROP_LATEST)
    .subscribe(System.out::println);
```

For resilience, combine WebFlux with Resilience4j:

```java
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;

@Service
public class ResilientUserService {

    private final WebClient webClient;

    @CircuitBreaker(name = "userService", fallbackMethod = "fallback")
    public Mono<User> getUser(String id) {
        return webClient.get()
                .uri("/users/{id}", id)
                .retrieve()
                .bodyToMono(User.class);
    }

    public Mono<User> fallback(String id, Throwable t) {
        return Mono.just(new User(id, "default", "default@example.com"));
    }
}
```

## Testing Reactive Microservices

Testing reactive code requires `StepVerifier` from reactor-test:

```java
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import reactor.test.StepVerifier;

@SpringBootTest
class UserControllerTest {

    @Autowired
    private UserController controller;

    @Test
    void testGetAllUsers() {
        StepVerifier.create(controller.getAllUsers())
                .expectNextCount(3)
                .verifyComplete();
    }

    @Test
    void testCreateUser() {
        User user = new User(null, "John", "john@example.com");
        StepVerifier.create(controller.createUser(user))
                .expectNextMatches(u -> u.getName().equals("John"))
                .verifyComplete();
    }
}
```

For integration testing with `WebTestClient`:

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class UserIntegrationTest {

    @Autowired
    private WebTestClient webTestClient;

    @Test
    void testGetUser() {
        webTestClient.get().uri("/users/1")
                .exchange()
                .expectStatus().isOk()
                .expectBody(User.class)
                .consumeWith(user -> {
                    assertThat(user.getResponseBody().getName()).isEqualTo("John");
                });
    }
}
```

## Common Pitfalls and How to Avoid Them

### 1. Blocking Calls in Reactive Chains

This is the #1 mistake. Never call `.block()` inside a reactive pipeline:

```java
// WRONG: blocks the reactive thread
return repository.findById(id)
        .map(user -> {
            String result = someBlockingService.call(); // blocks!
            return user;
        });

// RIGHT: use flatMap with a Mono
return repository.findById(id)
        .flatMap(user -> Mono.fromCallable(() -> someBlockingService.call())
                .subscribeOn(Schedulers.boundedElastic()));
```

### 2. Forgetting to Subscribe

Reactive streams are lazy — nothing happens until you subscribe. In a WebFlux controller, the framework handles subscription, but in standalone code, you must subscribe:

```java
repository.findAll().subscribe(System.out::println);
```

### 3. Mixing Reactive and Blocking Databases

If your database driver is blocking (e.g., JDBC), it will block the event loop. Use reactive drivers like `r2dbc` for relational databases, or `spring-data-mongodb-reactive`, `spring-data-cassandra-reactive`, etc.

### 4. Ignoring Backpressure

While Reactor handles backpressure, badly designed consumers can cause `OutOfMemoryError`. Use `limitRate()` to control demand:

```java
repository.findAll()
        .limitRate(10) // request 10 elements at a time
        .subscribe();
```

## Performance Tuning

- **Thread model**: WebFlux runs on Netty by default. Tune `reactor.netty.ioWorkerCount` and `reactor.netty.ioSelectCount`.
- **Database connection pool**: Use reactive connection pools like `r2dbc-pool`.
- **Serialization**: Jackson is the default, but for high throughput, consider `kryo` or protocol buffers.

Example `application.yml` configuration:

```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://localhost:5432/mydb
    pool:
      initial-size: 5
      max-size: 20
server:
  netty:
    connection-timeout: 5000
```

## When to Use WebFlux vs WebMVC

WebFlux is not always the answer. Use it when:
- You have high concurrency requirements (thousands of concurrent connections)
- You're building streaming services or long-lived connections (SSE, WebSockets)
- Your entire stack is reactive (database, messaging, etc.)

Stick with WebMVC when:
- You have a simple CRUD app with low traffic
- Your team is unfamiliar with reactive programming
- You rely on blocking libraries (e.g., JDBC, JPA)

## Key Takeaways

- Spring WebFlux provides a fully non-blocking, reactive stack for building microservices, leveraging Project Reactor's `Mono` and `Flux`.
- Use `WebClient` for reactive inter-service communication — never `RestTemplate` in a reactive context.
- Always avoid blocking calls within reactive pipelines; use `subscribeOn` with a dedicated scheduler for blocking operations.
- Functional endpoints offer more explicit control compared to annotation-based controllers.
- Test reactive code with `StepVerifier` and `WebTestClient` to verify asynchronous behavior.
- Combine WebFlux with resilience patterns (circuit breakers, retries) to build robust microservices.
- Choose WebFlux when you need high concurrency and have a fully reactive stack; prefer WebMVC for simpler, blocking scenarios.