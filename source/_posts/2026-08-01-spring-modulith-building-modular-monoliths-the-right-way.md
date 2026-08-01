---
title: "Spring Modulith: Building Modular Monoliths the Right Way"
date: 2026-08-01
tags: [Spring Modulith, Modular Monolith, Spring Boot, Java, Architecture]
categories: [Java]
cover: "https://picsum.photos/seed/spring-modulith-building-modular-monoliths-the-right-way/1200/630.webp"
description: Learn how Spring Modulith helps you build maintainable modular monoliths with clear boundaries, enforcing module encapsulation and simplifying evolution to m...
---

## Introduction

In the ever-evolving landscape of software architecture, the pendulum often swings between two extremes: the simplicity of a monolithic application and the scalability of microservices. While microservices offer flexibility and independent deployability, they also introduce complexity in terms of network latency, distributed transactions, and operational overhead. On the other hand, a traditional monolith can quickly become a tangled mess of tightly coupled code, making it hard to maintain, test, and evolve.

Enter the **modular monolith** — an architectural style that strikes a balance by structuring the application into well-defined modules within a single deployable unit. This approach gives you the benefits of modularity, such as clear boundaries and reduced coupling, without the operational burden of distributed systems. However, enforcing these boundaries manually is challenging; developers often unknowingly introduce cross-module dependencies, eroding the architecture over time.

This is where **Spring Modulith** comes to the rescue. Spring Modulith is a framework that helps you build modular monoliths with enforced boundaries, making your codebase more maintainable and future-proof. In this blog post, we'll dive deep into what Spring Modulith is, why you should use it, and how to implement it in your Spring Boot projects. We'll cover everything from basic setup to advanced patterns like event-driven communication and testing strategies.

## Why Modular Monoliths?

Before we dive into Spring Modulith, let's understand the value of a modular monolith. A modular monolith is a single application that is divided into distinct modules, each responsible for a specific business capability. These modules are loosely coupled and communicate through well-defined interfaces.

### Benefits Over Traditional Monoliths

- **Maintainability**: With clear boundaries, developers can work on modules independently without accidentally breaking other parts of the system.
- **Testability**: Modules can be tested in isolation, making unit and integration tests more focused and reliable.
- **Onboarding**: New team members can quickly understand the system's structure by looking at the module boundaries.
- **Evolution**: If the monolith grows too large, you can extract modules into microservices with minimal refactoring, since the boundaries already exist.

### Benefits Over Microservices

- **Simpler Deployment**: You deploy a single artifact, reducing operational overhead.
- **Performance**: No network latency between modules; inter-module calls are just method calls.
- **Transactional Integrity**: You can use a single database and ACID transactions across modules, which is much simpler than distributed transactions.

However, these benefits are only realized if the module boundaries are respected. Without enforcement, developers might take shortcuts, leading to a 'big ball of mud'. Spring Modulith provides the enforcement and tooling to keep your architecture intact.

## What is Spring Modulith?

Spring Modulith is a project from the Spring ecosystem that supports building modular monoliths with Spring Boot. It provides:

- **Module Detection**: Automatically identifies modules based on package structure.
- **Dependency Enforcement**: Prevents unintended dependencies between modules at compile time and test time.
- **Event-Driven Communication**: Facilitates asynchronous communication between modules using Spring's application events and optional external message brokers.
- **Documentation Generation**: Creates diagrams of module dependencies to visualize your architecture.
- **Testing Support**: Provides utilities to test modules in isolation.

Spring Modulith is not a new runtime; it works with your existing Spring Boot application, adding a layer of structure and validation.

## Getting Started

Let's create a practical example to see Spring Modulith in action. We'll build a simple e-commerce application with modules for `catalog`, `order`, and `inventory`.

### Step 1: Add Dependencies

First, add the Spring Modulith dependencies to your `pom.xml` (for Maven) or `build.gradle` (for Gradle). As of Spring Boot 3.x, you can use the Spring Modulith BOM.

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-bom</artifactId>
            <version>1.1.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>org.springframework.modulith</groupId>
        <artifactId>spring-modulith-starter-core</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.modulith</groupId>
        <artifactId>spring-modulith-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

If you want to use event-driven communication with an external broker like Kafka, add `spring-modulith-starter-kafka` or `spring-modulith-starter-amqp`. For this example, we'll stick with in-process events.

### Step 2: Structure Your Packages

Spring Modulith uses package conventions to define modules. Typically, you place your classes under a root package (e.g., `com.example.shop`) and each sub-package represents a module. For example:

```
com.example.shop
├── catalog
│   ├── CatalogController.java
│   ├── CatalogService.java
│   └── Product.java
├── order
│   ├── OrderController.java
│   ├── OrderService.java
│   └── Order.java
└── inventory
    ├── InventoryService.java
    └── Stock.java
```

Spring Modulith will treat `catalog`, `order`, and `inventory` as distinct modules. By default, modules are allowed to depend on each other unless you forbid it, but we'll see how to enforce strict boundaries later.

### Step 3: Enforce Module Boundaries

To prevent direct dependencies between modules (e.g., `order` accessing `catalog`'s internal classes), you can use the `@ApplicationModule` annotation and set `allowedDependencies` to restrict access. For example:

```java
@ApplicationModule(allowedDependencies = "catalog")
package com.example.shop.order;
```

This declares that the `order` module can only depend on the `catalog` module. Any other dependency will cause a compile-time error or test failure.

### Step 4: Run the Application

With the dependencies in place, you can run your Spring Boot application as usual. Spring Modulith will automatically detect the modules and validate the dependencies at startup. If there's a violation, the application will fail with a descriptive error, preventing you from shipping a broken architecture.

## Module Communication Patterns

In a modular monolith, modules need to communicate. There are two primary ways: direct method calls (synchronous) and events (asynchronous). Spring Modulith supports both.

### Direct Method Calls

If a module is allowed to depend on another, you can simply inject the service bean from the other module and call its public methods. For example, the `order` module might need to check product availability in the `catalog` module.

```java
@Service
public class OrderService {

    private final CatalogService catalogService;

    public OrderService(CatalogService catalogService) {
        this.catalogService = catalogService;
    }

    public Order placeOrder(OrderRequest request) {
        Product product = catalogService.getProduct(request.productId());
        // ... process order
    }
}
```

However, direct calls create coupling. To keep modules more independent, you might prefer event-driven communication.

### Event-Driven Communication

Spring Modulith builds on Spring's application events to allow modules to publish and listen to events without knowing each other. This is ideal for cross-cutting concerns like order placement triggering inventory updates.

First, define an event class:

```java
public record OrderPlaced(Long orderId, Long productId, int quantity) {}
```

In the `order` module, publish the event after placing an order:

```java
@Service
public class OrderService {

    private final ApplicationEventPublisher events;

    public OrderService(ApplicationEventPublisher events) {
        this.events = events;
    }

    public Order placeOrder(OrderRequest request) {
        // ... save order
        events.publishEvent(new OrderPlaced(order.getId(), request.productId(), request.quantity()));
        return order;
    }
}
```

In the `inventory` module, listen for the event:

```java
@Service
public class InventoryService {

    @EventListener
    public void onOrderPlaced(OrderPlaced event) {
        // Decrease stock
        adjustStock(event.productId(), -event.quantity());
    }
}
```

This way, the `order` module doesn't need to know about the `inventory` module; it just publishes an event. The `inventory` module listens and reacts. This reduces coupling significantly.

### External Messaging

If you need asynchronous processing with durability or want to prepare for microservices, you can use an external message broker. Spring Modulith supports Kafka, AMQP (RabbitMQ), and JMS. Simply add the corresponding starter and annotate your event with `@Externalized`.

```java
@Externalized("order-placed")
public record OrderPlaced(Long orderId, Long productId, int quantity) {}
```

This will publish the event to a topic/queue named `order-placed`, and you can have a listener in another service (or module) consuming it.

## Testing Your Modular Application

Testing is crucial to ensure that module boundaries are not violated and that each module works as expected.

### Module Isolation Testing

Spring Modulith provides `@ApplicationModuleTest` to test a module in isolation. This loads only the necessary beans for that module, excluding others.

```java
@ApplicationModuleTest
class OrderModuleTest {

    @Autowired
    OrderService orderService;

    @Test
    void shouldPlaceOrder() {
        // test logic
    }
}
```

### Verifying Module Boundaries

You can write a test that verifies the dependency rules. Spring Modulith includes `verifyDependencies()` method in its test utilities.

```java
class ModularityTests {

    @Test
    void shouldVerifyModuleDependencies() {
        ApplicationModules modules = ApplicationModules.of(ShopApplication.class);
        modules.verify();
    }
}
```

This test will fail if there are any unexpected dependencies between modules. It's a great safety net to prevent architectural drift.

## Advanced Features

### Generating Documentation

Spring Modulith can generate a textual or graphical representation of your module dependencies. You can use the `spring-modulith-docs` dependency to produce diagrams at build time. For example, with Maven, you can generate an Asciidoc document that includes a PlantUML diagram.

### Observability

Spring Modulith integrates with Spring Boot Actuator to expose module information via a custom endpoint. You can access `/actuator/modulith` to see the module structure at runtime. This is useful for monitoring and debugging.

### Enforcing Rules in CI

You can integrate the modularity verification into your CI pipeline. Just run the `verify()` test as part of your build. If any developer introduces a forbidden dependency, the build will fail, ensuring that the architecture remains clean.

## Best Practices for Modular Monoliths

While Spring Modulith provides the tooling, you still need to design your modules thoughtfully. Here are some best practices:

- **Define Modules by Business Capability**: Each module should encapsulate a single business capability, such as `catalog`, `order`, `customer`, etc.
- **Keep Modules Small and Focused**: A module should have a clear responsibility and not become a mini-monolith itself.
- **Expose Public APIs**: Each module should have a public API (services, repositories) that other modules can use, while keeping internal classes package-private.
- **Avoid Cyclic Dependencies**: Use `allowedDependencies` to prevent cycles.
- **Use Events for Cross-Cutting Concerns**: When multiple modules need to react to an action, prefer events over direct calls.
- **Regularly Review Module Boundaries**: As the application evolves, revisit your module structure and adjust dependencies as needed.

## Conclusion

Spring Modulith is a powerful addition to the Spring ecosystem, enabling developers to build modular monoliths with confidence. By enforcing module boundaries, providing testing utilities, and supporting event-driven communication, it helps you maintain a clean architecture that can evolve gracefully, whether you stay with a monolith or decide to split into microservices later.

If you're starting a new Spring Boot project, consider structuring it as a modular monolith from day one. If you have an existing monolith, you can gradually refactor it into modules using Spring Modulith, reaping the benefits of maintainability without a complete rewrite.

## Key Takeaways

- **Modular monoliths** offer a balanced approach between monoliths and microservices, providing modularity without distributed system complexity.
- **Spring Modulith** enforces module boundaries through package conventions, annotations, and compile-time checks.
- **Event-driven communication** with Spring Modulith reduces coupling between modules and prepares for future microservices extraction.
- **Testing support** allows you to verify module dependencies and test modules in isolation, ensuring architectural integrity.
- **Tooling** like documentation generation and runtime endpoints helps you visualize and monitor your modular structure.
- **Best practices** include defining modules by business capability, exposing clear APIs, and regularly reviewing boundaries.

By adopting Spring Modulith, you're not just writing code—you're crafting an architecture that stands the test of time.