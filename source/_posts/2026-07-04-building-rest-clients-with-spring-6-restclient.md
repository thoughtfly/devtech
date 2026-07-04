---
title: "Building REST Clients with Spring 6 RestClient"
date: 2026-07-04
tags: [Spring Boot, Spring 6, RestClient, REST API, Java]
categories: [Java]
cover:
description: Learn how to build robust REST clients in Spring Boot 3.x using the new RestClient API. Step-by-step guide with code examples, error handling, and best pract...
---

# Building REST Clients with Spring 6 RestClient

Spring Framework has always been at the forefront of making REST client development simple and intuitive. With the release of Spring 6 and Spring Boot 3.x, the team introduced a new, modern HTTP client: `RestClient`. This synchronous client is designed to replace the aging `RestTemplate` and provide a fluent, functional API that aligns with the reactive `WebClient` while remaining synchronous.

In this post, I'll walk you through everything you need to know about building REST clients with Spring 6's `RestClient`—from basic setup to advanced error handling and testing.

## Why RestClient?

Before diving into code, let's understand why `RestClient` exists. `RestTemplate` has been the go-to synchronous HTTP client for Spring applications since Spring 3.0. However, it has several drawbacks:

- **Deprecated since Spring 5.0**: While still functional, it's not getting new features.
- **Verbose API**: Requires manual handling of headers, parameters, and body serialization.
- **Error-prone**: Exceptions are unchecked, leading to less predictable error handling.
- **Tight coupling**: Hard to mock and test in isolation.

`RestClient` addresses all these issues by providing:

- A fluent, builder-based API
- Built-in support for JSON/XML serialization via `HttpMessageConverter`
- Clear separation of request preparation and response handling
- First-class error handling with `StatusHandler`
- Easy integration with Spring's testing utilities

## Setting Up RestClient

To use `RestClient`, you need Spring Boot 3.x (which ships with Spring 6). Add the following dependency to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

That's it. The `RestClient` is part of `spring-web`, which is included transitively.

### Creating a RestClient Bean

While you can create `RestClient` instances on the fly, it's better to define a bean for consistent configuration:

```java
@Configuration
public class RestClientConfig {

    @Bean
    public RestClient restClient(RestClient.Builder builder) {
        return builder
            .baseUrl("https://api.example.com")
            .defaultHeader("Accept", "application/json")
            .defaultHeader("User-Agent", "MyApp/1.0")
            .build();
    }
}
```

Spring Boot automatically provides a `RestClient.Builder` bean pre-configured with sensible defaults (like Jackson for JSON, connection timeouts, etc.). You can customize it further using `RestClientCustomizer` beans or application properties.

## Making GET Requests

Let's start with the most common operation—fetching data via GET.

### Simple GET with Response Body

```java
@Service
public class UserService {

    private final RestClient restClient;

    public UserService(RestClient restClient) {
        this.restClient = restClient;
    }

    public User getUserById(Long id) {
        return restClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .body(User.class);
    }
}
```

This is clean and readable. The URI template `{id}` is automatically expanded, and the response body is deserialized to `User` using Jackson.

### GET with Query Parameters

```java
public List<User> searchUsers(String name, int page) {
    return restClient.get()
        .uri(uriBuilder -> uriBuilder
            .path("/users/search")
            .queryParam("name", name)
            .queryParam("page", page)
            .build())
        .retrieve()
        .body(new ParameterizedTypeReference<List<User>>() {});
}
```

Notice the use of `ParameterizedTypeReference` to handle generic types like `List<User>`. This avoids unchecked casts.

## Making POST Requests

Creating resources is just as straightforward:

```java
public User createUser(User newUser) {
    return restClient.post()
        .uri("/users")
        .contentType(MediaType.APPLICATION_JSON)
        .body(newUser)
        .retrieve()
        .body(User.class);
}
```

The `.body()` method accepts any object; Jackson serializes it automatically. You can also send `MultiValueMap` for form data or raw strings.

### POST with Custom Headers

```java
public User createUserWithAuth(User newUser, String token) {
    return restClient.post()
        .uri("/users")
        .header("Authorization", "Bearer " + token)
        .body(newUser)
        .retrieve()
        .body(User.class);
}
```

## PUT and DELETE Requests

### Updating a Resource (PUT)

```java
public User updateUser(Long id, User updatedUser) {
    return restClient.put()
        .uri("/users/{id}", id)
        .body(updatedUser)
        .retrieve()
        .body(User.class);
}
```

### Deleting a Resource

```java
public void deleteUser(Long id) {
    restClient.delete()
        .uri("/users/{id}", id)
        .retrieve()
        .toBodilessEntity();
}
```

`toBodilessEntity()` returns a `ResponseEntity<Void>`, which is useful when you don't expect a response body.

## Error Handling with StatusHandler

One of the biggest improvements over `RestTemplate` is the declarative error handling. Instead of catching `HttpClientErrorException` or `HttpServerErrorException`, you can define handlers for specific HTTP status codes:

```java
public User getUserByIdSafe(Long id) {
    return restClient.get()
        .uri("/users/{id}", id)
        .retrieve()
        .onStatus(status -> status == HttpStatus.NOT_FOUND, (request, response) -> {
            throw new UserNotFoundException("User not found: " + id);
        })
        .onStatus(HttpStatus::is5xxServerError, (request, response) -> {
            throw new ExternalServiceException("Server error from user service");
        })
        .body(User.class);
}
```

You can also define a default error handler:

```java
.onStatus(HttpStatus::isError, (request, response) -> {
    // Log the error, then throw a generic exception
    throw new RestClientException("HTTP " + response.getStatusCode());
})
```

This pattern makes error handling predictable and testable.

## Working with ResponseEntity

Sometimes you need access to the full HTTP response, including headers and status code:

```java
public ResponseEntity<User> getUserWithResponse(Long id) {
    return restClient.get()
        .uri("/users/{id}", id)
        .retrieve()
        .toEntity(User.class);
}
```

This returns a `ResponseEntity<User>` containing status, headers, and body.

## Exchange Methods for Advanced Scenarios

If you need to intercept or modify the response before deserialization (e.g., to handle streaming or custom parsing), use the `exchange` method:

```java
public String getRawResponse(Long id) {
    return restClient.get()
        .uri("/users/{id}", id)
        .exchange((request, response) -> {
            // Read raw response body as string
            return new String(response.getBody().readAllBytes(), StandardCharsets.UTF_8);
        });
}
```

This gives you full control over the `ClientHttpResponse`.

## Timeouts and Connection Management

You can configure timeouts globally via application properties:

```yaml
spring:
  restclient:
    connect-timeout: 5s
    read-timeout: 10s
```

Or programmatically using a `RestClientCustomizer`:

```java
@Bean
public RestClientCustomizer customizer() {
    return builder -> builder
        .requestFactory(new JdkClientHttpRequestFactory(
            HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build()
        ));
}
```

## Testing RestClient

Spring Boot provides excellent support for testing `RestClient` using `MockRestServiceServer` from `spring-boot-starter-test`:

```java
@SpringBootTest
@AutoConfigureMockRestServiceServer
class UserServiceTest {

    @Autowired
    private UserService userService;

    @Autowired
    private MockRestServiceServer server;

    @Test
    void getUserById_shouldReturnUser() {
        // Arrange
        server.expect(requestTo("/users/1"))
            .andRespond(withSuccess(
                """
                {"id":1,"name":"John Doe","email":"john@example.com"}
                """,
                MediaType.APPLICATION_JSON
            ));

        // Act
        User user = userService.getUserById(1L);

        // Assert
        assertEquals("John Doe", user.getName());
        server.verify();
    }

    @Test
    void getUserById_shouldThrowOnNotFound() {
        server.expect(requestTo("/users/99"))
            .andRespond(withStatus(HttpStatus.NOT_FOUND));

        assertThrows(UserNotFoundException.class, () -> {
            userService.getUserById(99L);
        });
    }
}
```

This approach allows you to test your service logic without hitting real endpoints, making tests fast and reliable.

## Migrating from RestTemplate

If you have existing `RestTemplate` code, migration is straightforward. Here's a quick reference:

| RestTemplate | RestClient |
|---|---|
| `restTemplate.getForObject(url, Class)` | `restClient.get().uri(url).retrieve().body(Class)` |
| `restTemplate.postForObject(url, request, Class)` | `restClient.post().uri(url).body(request).retrieve().body(Class)` |
| `restTemplate.exchange(url, HttpMethod, entity, Class)` | `restClient.method(HttpMethod).uri(url).headers(headers).body(body).retrieve().toEntity(Class)` |
| `restTemplate.execute(...)` | `restClient.method(HttpMethod).uri(url).exchange(...)` |

## Real-World Example: Complete Service

Let's put it all together with a realistic example—a service that interacts with a paginated API:

```java
@Service
public class PostService {

    private final RestClient restClient;

    public PostService(RestClient restClient) {
        this.restClient = restClient;
    }

    public List<Post> getPosts(int page, int size) {
        return restClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/posts")
                .queryParam("_page", page)
                .queryParam("_limit", size)
                .build())
            .retrieve()
            .onStatus(HttpStatus::is4xxClientError, (request, response) -> {
                throw new PostServiceException("Client error: " + response.getStatusCode());
            })
            .body(new ParameterizedTypeReference<List<Post>>() {});
    }

    public Post createPost(Post post) {
        return restClient.post()
            .uri("/posts")
            .contentType(MediaType.APPLICATION_JSON)
            .body(post)
            .retrieve()
            .onStatus(HttpStatus::isError, (request, response) -> {
                throw new PostServiceException("Failed to create post");
            })
            .body(Post.class);
    }

    public void deletePost(Long id) {
        restClient.delete()
            .uri("/posts/{id}", id)
            .retrieve()
            .onStatus(HttpStatus::isError, (request, response) -> {
                throw new PostServiceException("Failed to delete post " + id);
            })
            .toBodilessEntity();
    }
}
```

## Best Practices

1. **Always define a base URL** in the bean configuration to avoid duplication.
2. **Use `ParameterizedTypeReference`** for generic collections.
3. **Handle errors explicitly** with `onStatus` rather than relying on runtime exceptions.
4. **Inject `RestClient.Builder`** instead of `RestClient` to allow customization.
5. **Test with `MockRestServiceServer`** to validate request/response flows.
6. **Configure timeouts** globally in application properties.
7. **Use `exchange` sparingly**—only when you need low-level access.

## Key Takeaways

- **Spring 6's `RestClient`** is the modern replacement for `RestTemplate`, offering a fluent, functional API.
- **Fluent builder pattern** makes request construction intuitive and readable.
- **Declarative error handling** with `onStatus` simplifies exception management and testing.
- **Seamless integration** with Jackson, Spring Boot auto-configuration, and testing utilities.
- **Migration from `RestTemplate`** is straightforward, with one-to-one mapping for common operations.
- **Best practices** include using `ParameterizedTypeReference`, configuring timeouts, and leveraging `MockRestServiceServer` for unit tests.

Whether you're starting a new project or maintaining a legacy codebase, `RestClient` is the way forward for synchronous HTTP communication in Spring applications. Its clean API and robust error handling make it a joy to work with—and your future self will thank you for making the switch.