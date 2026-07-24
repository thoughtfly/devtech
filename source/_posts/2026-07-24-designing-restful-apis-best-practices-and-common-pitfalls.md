---
title: "Designing RESTful APIs: Best Practices and Common Pitfalls"
date: 2026-07-24
tags: [REST API, API Design, Best Practices, Java, Spring Boot]
categories: [Java]
cover:
description: Learn how to design RESTful APIs that are scalable, maintainable, and developer-friendly. This guide covers best practices, common mistakes, and practical co...
---

# Designing RESTful APIs: Best Practices and Common Pitfalls

REST APIs have become the backbone of modern web applications. They enable communication between services, power mobile apps, and expose data to third-party developers. However, designing a truly RESTful API that is intuitive, scalable, and maintainable is harder than it looks. After years of building and consuming APIs, I’ve seen the same mistakes repeated over and over. In this post, I’ll share the best practices I’ve learned and the pitfalls you should avoid.

## Understanding REST Constraints

REST (Representational State Transfer) is an architectural style defined by Roy Fielding in his doctoral dissertation. It’s not a protocol or a standard, but a set of constraints:

- **Client-Server**: Separation of concerns between the client and the server.
- **Stateless**: Each request from the client contains all the information needed to process it.
- **Cacheable**: Responses must implicitly or explicitly define themselves as cacheable or not.
- **Uniform Interface**: A consistent way to interact with resources.
- **Layered System**: Components cannot see beyond their immediate layer.
- **Code on Demand** (optional): Servers can extend client functionality by transferring executable code.

Adhering to these constraints leads to APIs that are scalable, reliable, and easy to evolve. But in practice, many APIs that claim to be RESTful violate these principles.

## Best Practices for RESTful API Design

### 1. Use Nouns for Resources, Not Verbs

Your API should expose **resources** (nouns) rather than **actions** (verbs). The HTTP methods define the actions.

**Bad:**
```
GET /getUsers
POST /createUser
PUT /updateUser
DELETE /deleteUser
```

**Good:**
```
GET /users
POST /users
PUT /users/{id}
DELETE /users/{id}
```

This is a fundamental principle of REST. Resources are the core entities in your system—users, orders, products, etc.

### 2. Use Plural Nouns for Collections

Use plural nouns for collection endpoints. It’s a widely adopted convention that makes your API predictable.

```
GET /users          # collection
GET /users/{id}     # single resource
```

Avoid mixing singular and plural forms. Consistency is key.

### 3. Leverage HTTP Methods Correctly

Each HTTP method has a specific meaning. Use them correctly:

- **GET**: Retrieve a resource (safe, idempotent).
- **POST**: Create a new resource (not idempotent).
- **PUT**: Replace a resource entirely (idempotent).
- **PATCH**: Partially update a resource (idempotent if applied correctly).
- **DELETE**: Remove a resource (idempotent).

**Common mistake:** Using POST for everything or using GET to modify state.

```java
// Good: GET for retrieval
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}

// Good: POST for creation
@PostMapping("/users")
public User createUser(@RequestBody User user) {
    return userService.save(user);
}
```

### 4. Use Meaningful HTTP Status Codes

HTTP status codes are part of the uniform interface. Use them to communicate the result of an operation clearly.

- **200 OK**: Successful GET, PUT, PATCH.
- **201 Created**: Successful POST (include Location header).
- **204 No Content**: Successful DELETE or PUT that returns no body.
- **400 Bad Request**: Client-side error (invalid input, missing fields).
- **401 Unauthorized**: Missing or invalid authentication.
- **403 Forbidden**: Authenticated but not authorized.
- **404 Not Found**: Resource doesn’t exist.
- **409 Conflict**: Resource conflict (e.g., duplicate entry).
- **422 Unprocessable Entity**: Validation errors.
- **500 Internal Server Error**: Server-side error.

**Don’t** return 200 with an error message in the body. That defeats the purpose of status codes.

### 5. Version Your API

APIs evolve. You need a way to introduce breaking changes without breaking existing clients. Versioning is essential.

**Common approaches:**

- **URI versioning**: `/api/v1/users`, `/api/v2/users`
- **Header versioning**: `Accept: application/vnd.myapi.v1+json`
- **Query parameter versioning**: `/users?version=1`

URI versioning is the simplest and most visible. It’s widely used and easy to implement.

```java
@RestController
@RequestMapping("/api/v1/users")
public class UserControllerV1 {
    // ...
}
```

### 6. Use Consistent Naming Conventions

Consistency reduces cognitive load for developers consuming your API.

- Use **kebab-case** for URI path segments: `/order-items` not `/orderItems` or `/order_items`.
- Use **snake_case** or **camelCase** for JSON properties (choose one and stick with it).
- Use **lowercase** for everything.

**Example:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "order_items": [
    {
      "product_id": 123,
      "quantity": 2
    }
  ]
}
```

### 7. Support Filtering, Sorting, and Pagination

Collections can be large. Allow clients to filter, sort, and paginate results.

**Filtering:** Use query parameters for field-specific filters.
```
GET /users?role=admin&status=active
```

**Sorting:** Use `sort` parameter with field and direction.
```
GET /users?sort=created_at:desc
```

**Pagination:** Use `page` and `size` parameters.
```
GET /users?page=1&size=20
```

Return pagination metadata:
```json
{
  "data": [...],
  "page": 1,
  "size": 20,
  "total": 150,
  "total_pages": 8
}
```

### 8. Use HATEOAS (Hypermedia as the Engine of Application State)

HATEOAS is often overlooked but is a key constraint of REST. It means that responses should include links to related resources, allowing clients to navigate the API dynamically.

```json
{
  "id": 123,
  "name": "John Doe",
  "links": [
    {
      "rel": "self",
      "href": "/users/123"
    },
    {
      "rel": "orders",
      "href": "/users/123/orders"
    }
  ]
}
```

In Java with Spring HATEOAS:
```java
import static org.springframework.hateoas.server.mvc.WebMvcLinkBuilder.*;

@GetMapping("/users/{id}")
public EntityModel<User> getUser(@PathVariable Long id) {
    User user = userService.findById(id);
    EntityModel<User> model = EntityModel.of(user);
    model.add(linkTo(methodOn(UserController.class).getUser(id)).withSelfRel());
    model.add(linkTo(methodOn(UserController.class).getAllUsers()).withRel("users"));
    return model;
}
```

### 9. Handle Errors Gracefully

Provide consistent error responses with meaningful messages.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "email",
        "message": "Email is required"
      }
    ]
  }
}
```

Use a global exception handler in Spring Boot:
```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleResourceNotFound(ResourceNotFoundException ex) {
        return new ErrorResponse("NOT_FOUND", ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleValidation(MethodArgumentNotValidException ex) {
        List<FieldError> fieldErrors = ex.getBindingResult().getFieldErrors().stream()
            .map(fe -> new FieldError(fe.getField(), fe.getDefaultMessage()))
            .collect(Collectors.toList());
        return new ErrorResponse("VALIDATION_ERROR", "Validation failed", fieldErrors);
    }
}
```

## Common Pitfalls to Avoid

### 1. Using Verbs in URLs

As mentioned earlier, verbs in URLs are an anti-pattern. They indicate you’re thinking in terms of RPC rather than REST.

**Avoid:**
```
POST /users/createUser
GET /users/getUserById
```

### 2. Ignoring HTTP Caching

Caching can dramatically improve performance and reduce server load. Use `Cache-Control`, `ETag`, and `Last-Modified` headers.

```
Cache-Control: max-age=3600
ETag: "abc123"
```

Implement conditional requests:
```java
@GetMapping("/users/{id}")
public ResponseEntity<User> getUser(@PathVariable Long id, 
                                     @RequestHeader(value = "If-None-Match", required = false) String ifNoneMatch) {
    User user = userService.findById(id);
    String etag = generateETag(user);
    if (etag.equals(ifNoneMatch)) {
        return ResponseEntity.status(HttpStatus.NOT_MODIFIED).build();
    }
    return ResponseEntity.ok().eTag(etag).body(user);
}
```

### 3. Returning Too Much or Too Little Data

Don’t return the entire database row when the client only needs a few fields. Use projections or allow the client to specify fields.

```
GET /users?fields=id,name,email
```

GraphQL solves this elegantly, but with REST you can implement sparse fieldsets.

### 4. Not Using Proper Authentication and Authorization

Never expose an API without security. Use standards like OAuth 2.0, JWT, or API keys.

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(OAuth2ResourceServerConfigurer::jwt);
        return http.build();
    }
}
```

### 5. Ignoring Idempotency

Idempotency ensures that multiple identical requests have the same effect as a single request. GET, PUT, DELETE, and PATCH (with proper implementation) should be idempotent. POST is not idempotent.

For operations that need idempotency (e.g., payment processing), use an idempotency key:
```
POST /payments
Idempotency-Key: unique-key-123
```

### 6. Not Documenting Your API

An API is only as good as its documentation. Use OpenAPI/Swagger to generate interactive docs.

```yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get all users
      responses:
        '200':
          description: A list of users
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
```

Spring Boot can auto-generate OpenAPI docs:
```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.0.2</version>
</dependency>
```

### 7. Over-Engineering from the Start

Don’t design for every possible future use case. Start simple and iterate. YAGNI (You Ain’t Gonna Need It) applies to API design too.

## Tools and Libraries

- **Spring Boot**: Excellent for building REST APIs in Java.
- **Spring HATEOAS**: Adds hypermedia support.
- **Springdoc OpenAPI**: Auto-generates OpenAPI documentation.
- **Postman**: For testing and documenting APIs.
- **Insomnia**: Alternative to Postman.
- **Swagger Editor**: For designing OpenAPI specs.

## Key Takeaways

1. **Use nouns for resources** and HTTP methods for actions.
2. **Leverage HTTP status codes** to communicate results clearly.
3. **Version your API** from the start to avoid breaking changes.
4. **Support filtering, sorting, and pagination** for collection endpoints.
5. **Implement proper error handling** with consistent error responses.
6. **Use HATEOAS** to make your API self-documenting and navigable.
7. **Secure your API** with standard authentication mechanisms.
8. **Document your API** using OpenAPI/Swagger.
9. **Avoid common pitfalls** like verbs in URLs, ignoring caching, and over-engineering.
10. **Keep it simple** and evolve your API based on real-world usage.

Designing a great REST API is a skill that improves with practice. Start with these principles, learn from your mistakes, and always consider the developer experience. Your API is a product—treat it like one.