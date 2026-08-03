---
title: "Structured Concurrency in Java 21: Virtual Threads in Action"
date: 2026-08-03
tags: [Java 21, Structured Concurrency, Virtual Threads, Concurrency, Async]
categories: [Java]
cover: "https://picsum.photos/seed/structured-concurrency-in-java-21-virtual-threads-in-action/1200/630.webp"
description: Explore Java 21's structured concurrency with virtual threads. Learn to manage concurrent tasks, improve error handling, and write maintainable async code.
---

## Introduction

Remember the days when asynchronous programming in Java meant wrestling with `Future`, `CompletableFuture`, and callback hell? Or when scaling to thousands of concurrent connections required a thread pool with all its tuning and context-switching overhead? Java 21 (released September 2023) changed the game with two revolutionary features: **Virtual Threads** and **Structured Concurrency**. 

Virtual threads make it trivial to create millions of lightweight threads, while structured concurrency brings a new API (`StructuredTaskScope`) that treats related tasks as a single unit of work with a clear lifecycle. Together, they transform how we write concurrent code—making it more readable, maintainable, and reliable.

In this post, we'll dive deep into structured concurrency, show you how to use it with virtual threads, and compare it to traditional approaches. We'll explore real-world examples, error handling, and best practices. By the end, you'll be ready to write concurrent Java code that's both efficient and elegant.

## The Problem with Traditional Concurrency

Before diving into the new features, let's recap why traditional concurrency in Java is painful.

### Thread-Per-Request Model

In the classic model, each request gets its own thread. This is simple and matches the imperative programming style, but threads are heavyweight—each consumes about 1MB of stack space. A typical server can only handle a few thousand threads before hitting memory limits or causing excessive context switching.

### Asynchronous APIs

To scale, developers turned to asynchronous APIs like `CompletableFuture`. This allows a single thread to handle multiple requests, but it comes at a cost:

- **Callback hell**: Code becomes deeply nested and hard to read.
- **Error handling**: Exceptions in async chains are tricky to propagate.
- **Composability**: Combining multiple async operations is verbose and error-prone.
- **Debugging**: Stack traces are fragmented and unhelpful.

### The Need for a Better Model

We wanted the simplicity of thread-per-request but with the scalability of async. Enter **virtual threads**.

## Virtual Threads: A Quick Overview

Virtual threads are lightweight threads managed by the JVM. They are not OS threads—they are scheduled on a small number of carrier threads (typically the platform threads). When a virtual thread performs a blocking I/O operation, it is automatically unmounted from the carrier thread, freeing it to run other virtual threads. This means you can create millions of virtual threads without worrying about memory or performance.

Creating a virtual thread is simple:

```java
Thread vThread = Thread.ofVirtual().start(() -> {
    System.out.println("Hello from virtual thread: " + Thread.currentThread());
});
vThread.join();
```

But virtual threads alone don't solve the composability problem. You still need a way to structure concurrent tasks. That's where **Structured Concurrency** comes in.

## Structured Concurrency: The Concept

Structured concurrency is a programming paradigm that applies the principle of "structured programming" to concurrent tasks. The idea is simple: **the lifetime of a child task is strictly contained within the lifetime of its parent task**. 

In Java, this is realized with the `StructuredTaskScope` class. You create a scope, fork tasks into it, and then await their completion. When the scope closes, all tasks are guaranteed to be done (or cancelled). This eliminates common issues like thread leaks and orphaned tasks.

### Benefits:
- **Clear lifecycle**: Tasks are created and completed within a block.
- **Error propagation**: If one task fails, you can cancel the others and propagate the exception.
- **Observability**: Stack traces include the task hierarchy.
- **Resource management**: No need to manually manage thread pools.

## Getting Started with StructuredTaskScope

`StructuredTaskScope` is an abstract class in `java.util.concurrent`. It's designed to be used with virtual threads, but it works with platform threads too.

Here's a basic example:

```java
import java.util.concurrent.StructuredTaskScope;

public class BasicStructuredConcurrency {

    public static void main(String[] args) throws Exception {
        // Create a scope
        try (var scope = new StructuredTaskScope<String>()) {
            // Fork two tasks
            Future<String> task1 = scope.fork(() -> {
                Thread.sleep(1000);
                return "Result from task1";
            });
            Future<String> task2 = scope.fork(() -> {
                Thread.sleep(500);
                return "Result from task2";
            });

            // Wait for all tasks to complete
            scope.join();

            // Get results
            System.out.println(task1.resultNow());
            System.out.println(task2.resultNow());
        }
        // Scope closes here, ensuring all tasks are done
    }
}
```

In this example:
- `scope.fork()` submits a task to run concurrently.
- `scope.join()` blocks until all forked tasks complete (successfully or exceptionally).
- The try-with-resources ensures that the scope is closed, which cancels any unfinished tasks.

Notice that we use `resultNow()` to get the result—this method throws if the task failed, so we need to handle exceptions.

## Error Handling and Cancellation

One of the biggest advantages of structured concurrency is robust error handling. If one task fails, you often want to cancel the others and fail fast.

Let's look at an example where we fetch data from multiple remote services, and if any fails, we want to abort the whole operation.

```java
public class ErrorHandlingExample {

    public record Response(String service, String data) {}

    public static void main(String[] args) throws Exception {
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            // Fork tasks that might fail
            Future<Response> userService = scope.fork(() -> callService("user"));
            Future<Response> orderService = scope.fork(() -> callService("order"));

            // Wait for completion or failure
            scope.join();

            // If any task failed, this throws the first exception
            scope.throwIfFailed();

            // All tasks succeeded
            System.out.println("User: " + userService.resultNow());
            System.out.println("Order: " + orderService.resultNow());
        }
    }

    private static Response callService(String service) throws Exception {
        // Simulate network call
        Thread.sleep(1000);
        if (service.equals("order")) {
            throw new RuntimeException("Order service unavailable");
        }
        return new Response(service, "data from " + service);
    }
}
```

Here, we use `ShutdownOnFailure`—a predefined policy that cancels all tasks if any one fails. `throwIfFailed()` throws the first exception that occurred. This gives us fail-fast behavior without complex orchestration.

### Other Policies

- `ShutdownOnSuccess`: Cancels all tasks when the first one succeeds. Useful for race conditions (e.g., query multiple services and use the fastest response).
- `ShutdownOnFailure`: As shown above.
- You can also create custom policies by subclassing `StructuredTaskScope`.

## Real-World Example: Parallel API Calls

Let's build a realistic scenario: a service that aggregates data from three different APIs—user profile, recent orders, and recommendations. We want to fetch these concurrently and return a combined result.

```java
import java.time.Duration;
import java.util.concurrent.*;
import java.util.concurrent.StructuredTaskScope;

public class AggregationService {

    record UserProfile(String id, String name) {}
    record Order(String id, double amount) {}
    record Recommendation(String item) {}
    record AggregatedData(UserProfile profile, List<Order> orders, List<Recommendation> recs) {}

    public AggregatedData fetchAll(String userId) throws Exception {
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            // Fork all three tasks
            Future<UserProfile> profileFuture = scope.fork(() -> fetchUserProfile(userId));
            Future<List<Order>> ordersFuture = scope.fork(() -> fetchOrders(userId));
            Future<List<Recommendation>> recsFuture = scope.fork(() -> fetchRecommendations(userId));

            // Wait for completion
            scope.join();
            scope.throwIfFailed();

            // Combine results
            return new AggregatedData(
                profileFuture.resultNow(),
                ordersFuture.resultNow(),
                recsFuture.resultNow()
            );
        }
    }

    private UserProfile fetchUserProfile(String userId) throws InterruptedException {
        // Simulate API call
        Thread.sleep(Duration.ofMillis(500));
        return new UserProfile(userId, "Alice");
    }

    private List<Order> fetchOrders(String userId) throws InterruptedException {
        Thread.sleep(Duration.ofMillis(800));
        return List.of(new Order("1", 99.99), new Order("2", 49.50));
    }

    private List<Recommendation> fetchRecommendations(String userId) throws InterruptedException {
        Thread.sleep(Duration.ofMillis(600));
        return List.of(new Recommendation("Book"), new Recommendation("Laptop"));
    }

    public static void main(String[] args) throws Exception {
        var service = new AggregationService();
        var result = service.fetchAll("user123");
        System.out.println(result);
    }
}
```

This code is clean, readable, and each task is independent. The total time is roughly the maximum of the three calls (800ms) instead of the sum (1900ms).

## Comparing with CompletableFuture

Let's see how the same aggregation would look with `CompletableFuture`:

```java
public AggregatedData fetchAllWithCF(String userId) {
    CompletableFuture<UserProfile> profileCF = CompletableFuture.supplyAsync(() -> {
        try { Thread.sleep(500); return new UserProfile(userId, "Alice"); }
        catch (InterruptedException e) { throw new CompletionException(e); }
    });
    CompletableFuture<List<Order>> ordersCF = CompletableFuture.supplyAsync(() -> {
        try { Thread.sleep(800); return List.of(new Order("1", 99.99)); }
        catch (InterruptedException e) { throw new CompletionException(e); }
    });
    CompletableFuture<List<Recommendation>> recsCF = CompletableFuture.supplyAsync(() -> {
        try { Thread.sleep(600); return List.of(new Recommendation("Book")); }
        catch (InterruptedException e) { throw new CompletionException(e); }
    });

    return CompletableFuture.allOf(profileCF, ordersCF, recsCF)
            .thenApply(v -> new AggregatedData(
                profileCF.join(),
                ordersCF.join(),
                recsCF.join()
            )).join();
}
```

While this works, it has issues:
- **Exception handling**: If one future fails, `join()` throws a `CompletionException` that wraps the original, making it harder to diagnose.
- **Cancellation**: There's no automatic cancellation of other tasks if one fails.
- **Readability**: The code is less linear and requires more mental overhead.

Structured concurrency provides better error propagation and cancellation out of the box.

## Under the Hood: How Virtual Threads and Structured Concurrency Work Together

When you fork a task in a `StructuredTaskScope`, the task runs on a new virtual thread. The scope maintains a registry of these threads. When `join()` is called, it waits for all threads to finish. If the scope is closed prematurely (e.g., via try-with-resources exit), it cancels all remaining tasks.

Virtual threads are perfect for this because they're cheap to create and dispose. Creating a million virtual threads is feasible, whereas a million platform threads would exhaust memory.

### Thread Dump and Observability

One of the underrated benefits is observability. With virtual threads, the JVM can produce thread dumps that show the hierarchy of tasks. This makes debugging much easier compared to traditional async code where stack traces are fragmented.

## Best Practices and Pitfalls

### Do:
- Use `StructuredTaskScope` for tasks that are logically related and have a clear parent-child relationship.
- Always use try-with-resources to ensure scope closure.
- Prefer `ShutdownOnFailure` or `ShutdownOnSuccess` for common patterns.
- Use virtual threads for I/O-bound tasks; for CPU-bound tasks, consider parallelism via parallel streams or `Executors.newFixedThreadPool`.

### Don't:
- **Don't** fork tasks that outlive the scope (e.g., fire-and-forget). That defeats the purpose.
- **Don't** use `StructuredTaskScope` for independent tasks that don't need coordination.
- **Don't** call `fork()` outside the scope's thread—the API enforces this, but be aware.
- **Don't** forget to handle `InterruptedException` in your tasks.

### Pitfalls:
- **Deadlocks**: If a task waits for another task's result using `future.get()`, it may deadlock if the other task is in a different scope. Use `scope.join()` instead.
- **Resource leaks**: If you open resources inside a task, ensure they are closed properly. The scope only manages thread lifecycle, not other resources.
- **Thread confinement**: Some libraries (e.g., JDBC) may not be virtual-thread-friendly. Ensure your libraries support virtual threads or use platform threads for those parts.

## Migration Strategy

If you're working on an existing codebase, you don't have to rewrite everything. Here's a step-by-step approach:

1. **Identify** blocking I/O operations (network calls, database queries, file I/O).
2. **Replace** `Executors.newFixedThreadPool` with `Executors.newVirtualThreadPerTaskExecutor()` for those operations.
3. **Gradually** refactor complex async chains to use `StructuredTaskScope` where it makes sense.
4. **Test** thoroughly—especially error handling and cancellation.

Example of using virtual threads with an executor:

```java
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
try (executor) {
    List<Future<String>> futures = IntStream.range(0, 1000)
        .mapToObj(i -> executor.submit(() -> fetchData(i)))
        .toList();
    for (Future<String> f : futures) {
        System.out.println(f.get());
    }
}
```

But this still lacks the structured error handling. Better to use `StructuredTaskScope` directly.

## Performance Considerations

Virtual threads are not a silver bullet. They shine for I/O-bound tasks, but for CPU-bound tasks, the overhead of context switching and scheduling may be higher than using a fixed pool sized to the number of cores.

Also, be aware of **pinning**: if a virtual thread enters a `synchronized` block or calls a native method, it may be pinned to the carrier thread, reducing concurrency. In Java 21, the JVM can detect some pinning, but it's best to avoid long-running `synchronized` blocks in virtual threads.

## Conclusion (Not included per instructions)

We've covered the essentials of structured concurrency with virtual threads in Java 21. This feature is a game-changer for writing clean, scalable concurrent code. By embracing `StructuredTaskScope`, you can avoid the pitfalls of traditional async programming and make your codebase more maintainable.

## Key Takeaways

- **Virtual threads** allow you to create millions of lightweight threads, making thread-per-request viable again without the resource overhead.
- **Structured concurrency** brings a new API (`StructuredTaskScope`) that ensures tasks are completed or cancelled within a defined scope.
- **Error handling** is simplified with policies like `ShutdownOnFailure` and `ShutdownOnSuccess`.
- **Readability** improves significantly compared to `CompletableFuture` and callbacks.
- **Observability** benefits from better thread dumps and stack traces.
- **Start migrating** by replacing thread pools with virtual threads and gradually adopting `StructuredTaskScope` for coordinated tasks.

Now go ahead and try it in your next Java 21 project! Your future self will thank you.