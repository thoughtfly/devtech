---
title: "Building GraphQL APIs with Spring for GraphQL: A Comprehensive Guide"
date: 2026-07-31
tags: [Spring Boot, GraphQL, Java, API, Spring for GraphQL]
categories: [Java]
cover: "https://images.unsplash.com/photo-1613415958465-380fde69056c?w=1200&q=80&fit=crop&fm=webp"
description: Learn to build robust GraphQL APIs with Spring for GraphQL. From setup to advanced features like error handling, pagination, and security, this guide covers...
---

## Introduction

GraphQL has revolutionized the way we design APIs, offering a flexible and efficient alternative to REST. With its client-driven query language and runtime, GraphQL empowers developers to fetch exactly the data they need, eliminating over-fetching and under-fetching. For Java developers, the Spring ecosystem provides a first-class integration with **Spring for GraphQL**, a module that simplifies building GraphQL servers on top of Spring Boot. This guide will walk you through the essential concepts, setup, and advanced techniques to build production-ready GraphQL APIs with Spring for GraphQL.

Whether you're a seasoned Spring developer or new to GraphQL, this article will provide practical insights and code examples that you can directly apply to your projects.

## Getting Started with Spring for GraphQL

### 1. Adding Dependencies

To begin, create a new Spring Boot project and add the following dependencies to your `pom.xml` (Maven) or `build.gradle` (Gradle).

**Maven:**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-graphql</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<!-- Optional: For data fetching (e.g., JPA) -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>runtime</scope>
</dependency>
```

**Gradle:**

```gradle
implementation 'org.springframework.boot:spring-boot-starter-graphql'
implementation 'org.springframework.boot:spring-boot-starter-web'
// Optional
implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
runtimeOnly 'com.h2database:h2'
```

### 2. Defining Your GraphQL Schema

GraphQL APIs are driven by a schema, which defines the types, queries, mutations, and subscriptions. Spring for GraphQL uses schema files (`.graphqls`) placed in `src/main/resources/graphql`.

Let's create a simple schema for a blog platform:

```graphql
type Query {
    posts(first: Int, after: String): PostConnection!
    post(id: ID!): Post
}

type Mutation {
    createPost(input: PostInput!): Post!
    updatePost(id: ID!, input: PostInput!): Post!
    deletePost(id: ID!): Boolean!
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: Author!
    comments: [Comment!]!
    createdAt: String!
}

type Author {
    id: ID!
    name: String!
    email: String!
}

type Comment {
    id: ID!
    content: String!
    author: Author!
}

input PostInput {
    title: String!
    content: String!
    authorId: ID!
}

type PostConnection {
    edges: [PostEdge!]!
    pageInfo: PageInfo!
}

type PostEdge {
    node: Post!
    cursor: String!
}

type PageInfo {
    hasNextPage: Boolean!
    endCursor: String
}
```

### 3. Implementing Resolvers

In Spring for GraphQL, you can implement resolvers using `@QueryMapping`, `@MutationMapping`, and `@SchemaMapping` annotations. The framework uses the schema to map Java methods to fields.

Create a controller-like component:

```java
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.MutationMapping;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.graphql.data.method.annotation.SchemaMapping;
import org.springframework.stereotype.Controller;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Controller
public class PostController {

    private final PostService postService;
    private final AuthorService authorService;

    public PostController(PostService postService, AuthorService authorService) {
        this.postService = postService;
        this.authorService = authorService;
    }

    @QueryMapping
    public List<Post> posts() {
        return postService.getAllPosts();
    }

    @QueryMapping
    public Post post(@Argument String id) {
        return postService.getPostById(id);
    }

    @MutationMapping
    public Post createPost(@Argument(name = "input") PostInput input) {
        return postService.createPost(input);
    }

    @MutationMapping
    public Post updatePost(@Argument String id, @Argument(name = "input") PostInput input) {
        return postService.updatePost(id, input);
    }

    @MutationMapping
    public boolean deletePost(@Argument String id) {
        return postService.deletePost(id);
    }

    // Resolver for nested fields
    @SchemaMapping
    public Author author(Post post) {
        return authorService.getAuthorById(post.getAuthorId());
    }
}
```

### 4. Data Classes and Services

Define your domain models and services. Here's an example using a simple in-memory store for brevity:

```java
public record Post(String id, String title, String content, String authorId, LocalDateTime createdAt) {}

public record Author(String id, String name, String email) {}

public record Comment(String id, String content, String authorId, String postId) {}

@Service
public class PostService {
    private final List<Post> posts = new ArrayList<>();
    private final Map<String, List<Comment>> comments = new HashMap<>();

    public List<Post> getAllPosts() {
        return posts;
    }

    public Post getPostById(String id) {
        return posts.stream()
                .filter(p -> p.id().equals(id))
                .findFirst()
                .orElseThrow(() -> new PostNotFoundException(id));
    }

    public Post createPost(PostInput input) {
        Post post = new Post(UUID.randomUUID().toString(), input.title(), input.content(), input.authorId(), LocalDateTime.now());
        posts.add(post);
        return post;
    }

    public Post updatePost(String id, PostInput input) {
        Post existing = getPostById(id);
        Post updated = new Post(existing.id(), input.title(), input.content(), input.authorId(), existing.createdAt());
        posts.replaceAll(p -> p.id().equals(id) ? updated : p);
        return updated;
    }

    public boolean deletePost(String id) {
        return posts.removeIf(p -> p.id().equals(id));
    }
}
```

## Advanced Features

### 5. Error Handling

GraphQL requires a structured error response. Spring for GraphQL automatically maps exceptions to GraphQL errors, but you can customize the behavior using `@GraphQlExceptionHandler` or by implementing `DataFetcherExceptionResolver`.

Create a custom exception:

```java
public class PostNotFoundException extends RuntimeException {
    public PostNotFoundException(String id) {
        super("Post not found with id: " + id);
    }
}
```

Then create a handler:

```java
import graphql.GraphQLError;
import graphql.GraphqlErrorBuilder;
import org.springframework.graphql.data.method.annotation.GraphQlExceptionHandler;
import org.springframework.graphql.execution.ErrorType;
import org.springframework.web.bind.annotation.ControllerAdvice;

@ControllerAdvice
public class GraphQLExceptionHandler {

    @GraphQlExceptionHandler
    public GraphQLError handlePostNotFound(PostNotFoundException ex) {
        return GraphqlErrorBuilder.newError()
                .message(ex.getMessage())
                .errorType(ErrorType.NOT_FOUND)
                .build();
    }
}
```

### 6. Pagination and Sorting

For scalable APIs, implement pagination using the Relay connection pattern. Spring for GraphQL provides `CursorStrategy` and `Window` utilities.

Modify your resolver to accept pagination arguments:

```java
import org.springframework.data.domain.Window;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.graphql.data.query.annotation.QueryMapping;
import org.springframework.graphql.data.query.annotation.Querydsl;

@QueryMapping
public Window<Post> posts(@Argument int first, @Argument String after) {
    // Convert cursor to offset (simplified)
    int offset = after != null ? Integer.parseInt(after) : 0;
    return postService.getPosts(offset, first);
}
```

For a more robust solution, use Spring Data's `Window` support with JPA:

```java
public interface PostRepository extends JpaRepository<Post, Long> {
    Window<Post> findAllBy(Pageable pageable);
}
```

### 7. Validation and Input Sanitization

Use Bean Validation (`jakarta.validation`) to validate inputs. Add `@Validated` to your controller and use constraints on your input records.

```java
public record PostInput(
    @NotBlank String title,
    @NotBlank @Size(max = 5000) String content,
    @NotBlank String authorId
) {}
```

Then in your controller:

```java
@MutationMapping
public Post createPost(@Valid @Argument(name = "input") PostInput input) {
    // ...
}
```

### 8. Security

Secure your GraphQL endpoint using Spring Security. You can protect the endpoint itself or add field-level security.

Add dependency:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

Configure security:

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/graphql").permitAll() // Public endpoint
                .anyRequest().authenticated()
            )
            .httpBasic();
        return http.build();
    }
}
```

For field-level security, use `@PreAuthorize` on resolver methods:

```java
@QueryMapping
@PreAuthorize("hasRole('ADMIN')")
public List<Post> allPostsAdmin() {
    return postService.getAllPosts();
}
```

### 9. Subscriptions for Real-Time Updates

GraphQL subscriptions allow clients to receive real-time updates. Spring for GraphQL supports WebSocket-based subscriptions.

Add the WebSocket dependency:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>
```

Define a subscription in your schema:

```graphql
type Subscription {
    postCreated: Post!
}
```

Implement the subscription resolver using `@SubscriptionMapping`:

```java
import org.reactivestreams.Publisher;
import org.springframework.graphql.data.method.annotation.SubscriptionMapping;
import reactor.core.publisher.Sinks;

@Controller
public class PostSubscriptionController {

    private final Sinks.Many<Post> postSink = Sinks.many().multicast().onBackpressureBuffer();

    @SubscriptionMapping
    public Publisher<Post> postCreated() {
        return postSink.asFlux();
    }

    // Call this method when a new post is created
    public void publishPost(Post post) {
        postSink.tryEmitNext(post);
    }
}
```

## Testing Your GraphQL API

Spring for GraphQL provides excellent testing support. Use `@GraphQlTest` for slice testing:

```java
@GraphQlTest(PostController.class)
public class PostControllerTest {

    @Autowired
    private GraphQlTester graphQlTester;

    @Test
    void shouldCreatePost() {
        String query = """
            mutation {
                createPost(input: {title: "Hello", content: "World", authorId: "1"}) {
                    id
                    title
                }
            }
            """;

        graphQlTester.document(query)
            .execute()
            .path("createPost.id")
            .entity(String.class)
            .isNotEmpty();
    }
}
```

## Best Practices

- **Schema-first design**: Always design your schema before implementation to ensure a clear contract.
- **Use DTOs**: Avoid exposing entity objects directly; use DTOs to decouple internal models.
- **N+1 problem**: Use `@BatchMapping` to fetch related entities in batches to avoid performance issues.
- **Monitoring**: Integrate with Micrometer and Actuator to monitor query execution times.
- **Versioning**: Use schema evolution techniques like deprecation instead of breaking changes.

## Conclusion

Spring for GraphQL simplifies the development of GraphQL APIs in Java, providing a robust, scalable, and secure foundation. By following the patterns and best practices outlined in this guide, you can build efficient APIs that meet modern client requirements. Start with the basics, then explore advanced features like subscriptions and batching to take full advantage of GraphQL's power.

## Key Takeaways

- Spring for GraphQL integrates seamlessly with Spring Boot, offering a schema-first approach.
- Use `@QueryMapping`, `@MutationMapping`, and `@SubscriptionMapping` for resolver methods.
- Handle errors gracefully with custom exception handlers for better client experiences.
- Implement pagination with Relay connections for scalable data fetching.
- Secure your GraphQL endpoints with Spring Security, including field-level authorization.
- Leverage subscriptions for real-time features using WebSocket support.
- Test your APIs with `@GraphQlTest` and `GraphQlTester` for reliable development.
- Always design your schema first and use DTOs to keep your API contract stable.

Start building your GraphQL API today with Spring for GraphQL and unlock a new level of API flexibility and performance!