---
title: "What's New in Java 24: Stream Gatherers, Scoped Values, and More"
date: 2026-09-15
tags: [Java 24, Java, Stream Gatherers, Scoped Values, JEP, Programming]
categories: [Java]
cover: "https://picsum.photos/seed/whats-new-in-java-24-stream-gatherers-scoped-values-and-more/1200/630.webp"
description: Explore Java 24 features including Stream Gatherers for functional transformations, Scoped Values for immutable context passing, and other key updates for mo...
---

## Introduction

Java continues to evolve at a rapid pace, and Java 24 is no exception. This release brings several significant features that address real-world engineering challenges, from more expressive stream processing to better context management in concurrent applications. If you're looking to stay ahead of the curve, understanding these new capabilities is essential.

In this post, we'll dive deep into the most impactful features of Java 24, with practical examples and implementation guidance.

## Stream Gatherers: A New Paradigm for Stream Processing

One of the most anticipated features in Java 24 is the introduction of Stream Gatherers. This API allows you to create custom stream transformations that go beyond the capabilities of traditional intermediate operations.

### Why Gatherers Matter

Traditional stream operations like `map`, `filter`, and `flatMap` are powerful but have limitations when dealing with stateful transformations or windowing operations. Gatherers fill this gap by providing a clean, functional way to implement complex stream manipulations.

### Basic Usage

Here's how you can use gatherers to implement a sliding window operation:

```java
import java.util.stream.Stream;
import java.util.stream.StreamGatherer;

public class SlidingWindowExample {
    public static void main(String[] args) {
        Stream<Integer> numbers = Stream.of(1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
        
        Stream<Integer> result = numbers.gather(
            SlidingWindowGatherer.of(3)
        );
        
        result.forEach(window -> 
            System.out.println(window)
        );
    }
}
```

### Implementing a Custom Gatherer

Let's create a practical gatherer that groups elements by a predicate:

```java
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

public class GroupByGatherer<T> implements StreamGatherer<T, GroupByGatherer.State<T>, List<T>, Void> {
    
    private final Predicate<T> predicate;
    
    public GroupByGatherer(Predicate<T> predicate) {
        this.predicate = predicate;
    }
    
    @Override
    public Spublisher<? extends List<T>> apply(Stage<T, ? super List<T>> stage) {
        return stage.flatMap(window -> {
            List<T> group = new ArrayList<>();
            // Process elements and group them
            return Stream.of(group);
        });
    }
    
    static class State<T> {
        private final List<T> currentGroup = new ArrayList<>();
        private final Predicate<T> predicate;
        
        State(Predicate<T> predicate) {
            this.predicate = predicate;
        }
        
        void add(T element) {
            if (predicate.test(element)) {
                currentGroup.add(element);
            }
        }
        
        List<T> getGroup() {
            return Collections.unmodifiableList(currentGroup);
        }
    }
}
```

## Scoped Values: Immutable Context Passing

Scoped Values address a critical need in modern Java applications: passing immutable context data through call stacks without the overhead of thread-local storage.

### The Problem with ThreadLocals

ThreadLocal variables have several drawbacks:
- Performance overhead in high-concurrency scenarios
- Memory leaks if not properly cleaned up
- Difficult to reason about in async code

### Scoped Values Solution

Scoped Values provide a type-safe, immutable way to pass context through your application:

```java
import java.util.concurrent.ScopedValue;

public class ScopedValueExample {
    
    // Define a scoped value
    private static final ScopedValue<String> USER_CONTEXT = ScopedValue.newInstance();
    
    public static void main(String[] args) {
        // Run with a scoped value
        ScopedValue.runWhere(USER_CONTEXT, "user123", () -> {
            String user = USER_CONTEXT.get();
            System.out.println("Current user: " + user);
            processRequest();
        });
    }
    
    private static void processRequest() {
        // Access the scoped value without passing it explicitly
        String user = USER_CONTEXT.get();
        System.out.println("Processing request for: " + user);
    }
}
```

### Best Practices for Scoped Values

1. **Use for immutable context**: Scoped values should contain immutable data
2. **Avoid in long-running threads**: They're designed for short-lived scopes
3. **Combine with virtual threads**: Perfect fit for Java's virtual thread model

## Other Notable Features in Java 24

### Record Patterns Enhancement

Java 24 continues to refine record patterns, making them more flexible and easier to use:

```java
public class RecordPatternExample {
    
    public static void analyze(Object obj) {
        if (obj instanceof Point(int x, int y)) {
            System.out.println("Point at: " + x + ", " + y);
        }
    }
    
    record Point(int x, int y) {}
}
```

### Enhanced Switch Expressions

The switch expressions continue to evolve with better pattern matching capabilities:

```java
public enum Shape { CIRCLE, RECTANGLE, TRIANGLE }

public class ShapeAnalyzer {
    
    public String describe(Shape shape, double value) {
        return switch (shape) {
            case CIRCLE -> "Circle with radius " + value;
            case RECTANGLE -> "Rectangle with dimension " + value;
            case TRIANGLE -> "Triangle with height " + value;
        };
    }
}
```

## Migration Guide: Upgrading to Java 24

### Step 1: Update Your Build Configuration

```xml
<!-- Maven example -->
<properties>
    <java.version>24</java.version>
    <maven.compiler.source>24</maven.compiler.source>
    <maven.compiler.target>24</maven.compiler.target>
</properties>
```

### Step 2: Review API Changes

Check for any deprecated APIs that have been removed. The Java 24 migration guide provides detailed information about breaking changes.

### Step 3: Test Thoroughly

Run your test suite and pay special attention to:
- Stream processing logic
- Context passing mechanisms
- Performance characteristics

## Performance Considerations

### Stream Gatherers Performance

Stream gatherers are designed to be efficient, but there are some considerations:
- They add a layer of indirection compared to built-in operations
- For simple transformations, traditional operations may still be faster
- Gatherers shine when implementing complex, stateful transformations

### Scoped Values vs ThreadLocals

| Aspect | Scoped Values | ThreadLocals |
|--------|--------------|--------------|
| Performance | Better for short scopes | Overhead in high concurrency |
| Memory Safety | Automatically cleaned up | Prone to leaks |
| Immutability | Enforced | Not enforced |
| Async Support | Excellent | Problematic |

## Real-World Use Cases

### Use Case 1: Distributed Tracing

Scoped Values are perfect for implementing distributed tracing:

```java
public class TracingExample {
    
    private static final ScopedValue<String> TRACE_ID = ScopedValue.newInstance();
    
    public static void handleRequest(Runnable task) {
        String traceId = generateTraceId();
        ScopedValue.runWhere(TRACE_ID, traceId, task);
    }
    
    private static void processStep() {
        String traceId = TRACE_ID.get();
        logger.info("Processing with trace ID: " + traceId);
    }
}
```

### Use Case 2: Data Transformation Pipeline

Stream gatherers excel in data transformation pipelines:

```java
public class DataPipelineExample {
    
    public static List<Double> processMetrics(Stream<Double> metrics) {
        return metrics.gather(new RollingAverageGatherer(10))
                     .toList();
    }
    
    static class RollingAverageGatherer implements StreamGatherer<Double, State, Double, Void> {
        private final int windowSize;
        
        RollingAverageGatherer(int windowSize) {
            this.windowSize = windowSize;
        }
        
        // Implementation details...
    }
}
```

## Key Takeaways

1. **Stream Gatherers** provide a powerful way to implement custom stream transformations, especially for stateful operations like windowing and grouping.

2. **Scoped Values** offer a modern, efficient alternative to ThreadLocal for passing immutable context through your application, particularly in virtual thread environments.

3. **Record Patterns** continue to evolve, making pattern matching more expressive and easier to read.

4. **Migration** to Java 24 requires careful review of API changes and thorough testing, especially for code using streams and context passing.

5. **Performance** characteristics differ between new features and traditional approaches—choose based on your specific use case rather than defaulting to one approach.

6. **Best practices** include using scoped values for immutable context, leveraging gatherers for complex stream transformations, and combining these features with virtual threads for optimal concurrency handling.

Java 24 represents another step forward in making the language more expressive, efficient, and aligned with modern programming patterns. By understanding and adopting these features, you can write cleaner, more maintainable code that takes full advantage of the Java platform's capabilities.