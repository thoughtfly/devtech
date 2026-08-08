---
title: "Java Records as DTOs: Best Practices for Clean and Efficient Code"
date: 2026-08-08
tags: [Java, Records, DTO, Best Practices]
categories: [Java]
cover: "https://images.unsplash.com/photo-1663658958221-8ab2382d9dfa?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to use Java Records as DTOs effectively. Discover best practices, validation, mapping, and performance tips to write cleaner code.
---

## Introduction

Java has evolved significantly since its inception, and one of the most exciting additions in recent years is the introduction of **Records** in Java 14 as a preview feature, and finally stabilized in Java 16. Records provide a compact syntax for declaring classes that are mere carriers of immutable data. They are a perfect fit for Data Transfer Objects (DTOs), which are used to transfer data between different layers of an application.

As a seasoned Java developer, you might have written countless DTO classes with boilerplate code: private fields, getters, setters, constructors, equals(), hashCode(), and toString(). With Records, all that boilerplate disappears, making your code cleaner, more readable, and less error-prone.

In this blog post, we'll dive deep into using Java Records as DTOs, explore best practices, discuss validation and mapping strategies, and highlight performance considerations. By the end, you'll be equipped to leverage Records to write more elegant and efficient Java code.

## What are Java Records?

Before we dive into best practices, let's quickly recap what Records are. A Record is a special kind of class in Java that is designed to be a transparent carrier for immutable data. Here's a simple example:

```java
public record UserDTO(Long id, String name, String email) {}
```

This single line gives you:

- A private final field for each component
- A public constructor that takes all components
- Accessor methods (e.g., `id()`, `name()`, `email()`)
- `equals()`, `hashCode()`, and `toString()` based on all components

Records are implicitly final, and they cannot extend any class (though they can implement interfaces). They are perfect for DTOs because DTOs are typically immutable and only carry data.

## Why Use Records for DTOs?

### 1. **Conciseness and Readability**

Traditional DTOs require a lot of boilerplate. Here's a typical DTO before Records:

```java
public class UserDTO {
    private final Long id;
    private final String name;
    private final String email;

    public UserDTO(Long id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }

    @Override
    public boolean equals(Object o) { ... }
    @Override
    public int hashCode() { ... }
    @Override
    public String toString() { ... }
}
```

That's a lot of code for a simple data carrier. With Records, you get all of that in one line. This reduces the chance of bugs and makes the code much easier to read and maintain.

### 2. **Immutability**

Records are shallowly immutable. All fields are final, and the accessor methods return the values directly. This is a huge advantage for DTOs because it ensures that the data cannot be accidentally modified after creation, leading to fewer concurrency issues and more predictable behavior.

### 3. **Value-Based Equality**

Records automatically provide `equals()` and `hashCode()` based on the component values. This is exactly what you want for DTOs, as two DTOs with the same data should be considered equal. This is particularly useful in testing and when using DTOs in collections or as map keys.

### 4. **Pattern Matching (Future)**

Records work seamlessly with pattern matching for `instanceof` (introduced in Java 16) and switch expressions (as a preview in later versions). This allows for concise and safe data extraction:

```java
if (dto instanceof UserDTO(Long id, String name, String email)) {
    System.out.println("User: " + name + " (" + email + ")");
}
```

## Best Practices for Using Records as DTOs

### 1. **Keep Records Simple**

Records are meant to be simple data carriers. Avoid adding complex logic or mutable state. If you need additional business logic, consider placing it in a separate service or utility class. For example, don't add methods that modify the record's state; instead, create a new record instance.

### 2. **Use Descriptive Component Names**

Just like with fields in a class, choose meaningful names for record components. This improves readability and self-documentation. For example, `UserDTO(Long userId, String userName, String userEmail)` is clearer than `UserDTO(Long a, String b, String c)`.

### 3. **Validation in the Compact Constructor**

Records allow you to define a **compact constructor** to validate the data before it is stored. This is a great place to enforce invariants. For example:

```java
public record UserDTO(Long id, String name, String email) {
    public UserDTO {
        Objects.requireNonNull(id);
        Objects.requireNonNull(name);
        Objects.requireNonNull(email);
        if (email.isBlank()) {
            throw new IllegalArgumentException("Email cannot be blank");
        }
    }
}
```

This ensures that you cannot create an invalid DTO. However, be careful not to overdo it with complex validation; keep it simple and focused on data integrity.

### 4. **Avoid Getters/Setters (Use Accessors)**

Records provide accessor methods that match the component names (e.g., `id()`, `name()`, `email()`). Some developers coming from a JavaBean background might be tempted to add `getId()`, `getName()`, etc., but this is unnecessary and defeats the purpose of Records. Stick with the default accessors.

### 5. **Implement Interfaces for Layered Architecture**

If you want to abstract your DTOs, you can have Records implement interfaces. This is useful when you have multiple representations of the same data (e.g., a base DTO and a detailed DTO). For example:

```java
public interface BaseUserDTO {
    Long id();
    String name();
}

public record UserDTO(Long id, String name, String email) implements BaseUserDTO {}
```

This allows you to write code that works with the interface, providing flexibility and decoupling.

### 6. **Use with JSON Serialization Libraries**

Most modern JSON libraries like Jackson and Gson have added support for Records. Make sure you're using a version that supports Records (e.g., Jackson 2.12+). With Jackson, you can serialize and deserialize Records out of the box, but you might need to configure the `ObjectMapper` for parameter names:

```java
ObjectMapper mapper = new ObjectMapper();
mapper.findAndRegisterModules();
// or
mapper.registerModule(new ParameterNamesModule());
```

This ensures that the JSON keys match the component names.

### 7. **Map Entities to Records**

When mapping from JPA entities to DTOs, you can use a simple static factory method or a mapper class. Records can have static factory methods:

```java
public record UserDTO(Long id, String name, String email) {
    public static UserDTO from(User user) {
        return new UserDTO(user.getId(), user.getName(), user.getEmail());
    }
}
```

Alternatively, use a dedicated mapper class with libraries like MapStruct. MapStruct supports Records as of version 1.5.0.Beta1.

### 8. **Consider Nested Records**

For complex DTOs, you can nest records to represent hierarchical data. For example:

```java
public record OrderDTO(Long orderId, CustomerDTO customer, List<OrderItemDTO> items) {}
public record CustomerDTO(Long id, String name) {}
public record OrderItemDTO(Long productId, int quantity) {}
```

This keeps the code organized and concise.

### 9. **Use with Streams and Optional**

Records work great with streams and `Optional`. Since they are immutable, you can safely use them in functional pipelines. For example:

```java
List<UserDTO> users = ...
users.stream()
    .filter(u -> u.email().endsWith("@company.com"))
    .map(UserDTO::name)
    .forEach(System.out::println);
```

### 10. **Be Mindful of Serialization and Deserialization**

When using Records with frameworks like Spring Boot, ensure that you have the necessary dependencies and configurations. For example, with Spring Boot and Jackson, you might need to add the `jackson-datatype-jdk8` and `jackson-module-parameter-names` modules. But with Spring Boot 2.5+, Records are supported out of the box if you're using Jackson 2.12+.

## Performance Considerations

Records are not a silver bullet for performance, but they do have some benefits:

- **Memory Footprint**: Records are just regular classes, so they don't introduce any overhead compared to hand-written DTOs. However, they are immutable, which can help in caching and sharing.
- **Serialization**: Records can be serialized efficiently if the library supports them. Jackson's support for Records is optimized and avoids reflection-based accessors.
- **Compile-time Safety**: Records are final, and the compiler generates the methods, which can lead to better optimization by the JIT compiler.

However, one thing to note: Records are shallowly immutable. If a record contains a mutable field (like a `List`), the contents of that list can still be modified. For true immutability, you should use unmodifiable collections or defensive copying in the constructor.

## Common Pitfalls and How to Avoid Them

### 1. **Using Records for Mutable DTOs**

If you need a DTO that can be modified after creation (e.g., in a builder pattern), Records are not the right choice. Instead, use a regular class or a builder pattern. Records are best for read-only data transfer.

### 2. **Overloading Constructors**

Records have a canonical constructor, and you can define additional constructors, but they must delegate to the canonical one. This can be limiting. For example, you cannot have a constructor that takes fewer arguments unless you provide default values:

```java
public record UserDTO(Long id, String name, String email) {
    public UserDTO(Long id, String name) {
        this(id, name, "unknown@example.com");
    }
}
```

This works, but it's a bit verbose. If you need many overloads, consider using a factory method instead.

### 3. **Forgetting to Update Dependencies**

Make sure you're using a Java version that supports Records (Java 16 or later) and that your libraries (e.g., Jackson, MapStruct) are compatible. Older versions might not support Records, leading to runtime errors.

### 4. **Misusing Accessor Methods in Frameworks**

Some frameworks (like Spring Data REST) might expect JavaBeans conventions (getters/setters). If you're using such frameworks, you might need to configure them to work with Records. For example, Spring Data REST can serialize Records, but you might need to adjust the naming strategy.

## Real-World Example: Building a REST API with Records

Let's put it all together with a simple Spring Boot REST controller that uses Records as DTOs.

**Entity** (simplified):

```java
@Entity
public class User {
    @Id
    @GeneratedValue
    private Long id;
    private String name;
    private String email;
    // getters and setters
}
```

**DTO** (Record):

```java
public record UserDTO(Long id, String name, String email) {
    public static UserDTO from(User user) {
        return new UserDTO(user.getId(), user.getName(), user.getEmail());
    }
}
```

**Repository**:

```java
public interface UserRepository extends JpaRepository<User, Long> {}
```

**Controller**:

```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserRepository userRepository;

    public UserController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @GetMapping
    public List<UserDTO> getAllUsers() {
        return userRepository.findAll().stream()
                .map(UserDTO::from)
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public UserDTO getUser(@PathVariable Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
        return UserDTO.from(user);
    }
}
```

With this setup, you get a clean, immutable DTO that can be easily serialized to JSON. Notice how concise the code is compared to traditional DTOs.

## Testing Records

Testing Records is straightforward. Since they provide value-based equality, you can use `assertEquals` on two records with the same values. For example:

```java
@Test
void testUserDTO() {
    UserDTO dto1 = new UserDTO(1L, "John", "john@example.com");
    UserDTO dto2 = new UserDTO(1L, "John", "john@example.com");
    assertEquals(dto1, dto2);
}
```

You can also use pattern matching in tests to extract values:

```java
if (dto instanceof UserDTO(Long id, String name, String email)) {
    assertEquals(1L, id);
    assertEquals("John", name);
}
```

## Conclusion

Java Records are a powerful addition to the Java language, and they are an excellent choice for DTOs. They reduce boilerplate, enforce immutability, and provide value-based equality out of the box. By following the best practices outlined in this post, you can write cleaner, more maintainable code while avoiding common pitfalls.

Remember to:
- Use Records for immutable, data-carrying DTOs.
- Validate data in the compact constructor.
- Keep Records simple and free of business logic.
- Ensure your libraries and frameworks support Records.
- Leverage static factory methods and mapping tools for entity-to-DTO conversion.

Embrace Records in your next project and experience the joy of writing less code with more clarity.

## Key Takeaways

- **Records provide a concise syntax for immutable data carriers**, eliminating boilerplate code for getters, constructors, equals, hashCode, and toString.
- **Use Records for DTOs** to ensure immutability, value-based equality, and better readability.
- **Validate data in the compact constructor** to enforce invariants at creation time.
- **Avoid adding business logic** to Records; keep them as simple data holders.
- **Use static factory methods** for mapping entities to DTOs, and consider libraries like MapStruct for complex mappings.
- **Ensure your serialization libraries (e.g., Jackson) are updated** to support Records.
- **Be cautious with mutable fields** inside Records; use defensive copying or unmodifiable collections for true immutability.
- **Records are not suitable for mutable DTOs**; use them only when data is read-only after creation.
- **Leverage pattern matching** with Records for concise and safe data extraction.
- **Update your Java version and dependencies** to fully utilize Records without compatibility issues.