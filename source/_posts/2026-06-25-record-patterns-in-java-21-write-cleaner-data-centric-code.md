---
title: "Record Patterns in Java 21: Write Cleaner Data-Centric Code"
date: 2026-06-25
tags: [Java 21, Record Patterns, Pattern Matching, Java Features]
categories: [Java]
cover:
description: Record Patterns in Java 21: Write Cleaner Data-Centric Code
---

---
title: "Record Patterns in Java 21: Write Cleaner Data-Centric Code"
date: 2024-01-15
tags: ["Java 21", "Record Patterns", "Pattern Matching", "Java Features"]
categories: ["Java"]
---

Java 21 introduced a game-changing feature for developers working with data-centric code: **Record Patterns**. Combined with pattern matching for `switch`, this feature lets you destructure records directly in conditional logic, eliminating boilerplate and making your intentions crystal clear.

In this post, I'll walk through what record patterns are, how they work under the hood, and practical examples where they shine. Whether you're building domain models, processing API responses, or parsing complex data structures, record patterns will make your code more readable and less error-prone.

## What Are Record Patterns?

Record patterns are a form of **destructuring pattern** that let you match a record instance against a pattern and extract its components in one step. Instead of writing:

```java
if (obj instanceof Point p) {
    int x = p.x();
    int y = p.y();
    // work with x and y
}
```

You can now write:

```java
if (obj instanceof Point(int x, int y)) {
    // work with x and y directly
}
```

This is more than syntactic sugar—it's a paradigm shift in how we think about data access.

## Prerequisites

Record patterns are a **preview feature** in Java 19 and 20, but became **standard** in Java 21. To use them, ensure you're running JDK 21 or later.

If you're still using an older version, consider upgrading. The productivity gains are substantial.

## Basic Syntax and Usage

Let's start with a simple record:

```java
record Point(int x, int y) {}
```

### Pattern Matching with `instanceof`

```java
void printCoordinates(Object obj) {
    if (obj instanceof Point(int x, int y)) {
        System.out.println("x=" + x + ", y=" + y);
    }
}
```

### Pattern Matching with `switch`

This is where record patterns truly shine:

```java
String describeShape(Object obj) {
    return switch (obj) {
        case Point(int x, int y) -> "Point at (" + x + ", " + y + ")";
        case Line(Point p1, Point p2) -> "Line from " + p1 + " to " + p2;
        case Circle(Point center, int radius) -> "Circle with radius " + radius;
        case null -> "null";
        default -> "Unknown shape";
    };
}
```

Notice how we can destructure nested records without any manual extraction.

## Nested Record Patterns

Record patterns compose naturally. Consider a `Line` that contains two `Point`s:

```java
record Line(Point start, Point end) {}
```

You can destructure nested records in a single pattern:

```java
if (obj instanceof Line(Point(int x1, int y1), Point(int x2, int y2))) {
    double length = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    System.out.println("Line length: " + length);
}
```

This is incredibly powerful for deeply nested data structures.

## Practical Examples

### 1. Processing JSON-like Data

Imagine you're building a configuration parser:

```java
sealed interface ConfigValue permits ConfigString, ConfigNumber, ConfigObject, ConfigArray {}
record ConfigString(String value) implements ConfigValue {}
record ConfigNumber(double value) implements ConfigValue {}
record ConfigObject(Map<String, ConfigValue> entries) implements ConfigValue {}
record ConfigArray(List<ConfigValue> items) implements ConfigValue {}

String extractConfig(ConfigValue value) {
    return switch (value) {
        case ConfigString(var s) -> s;
        case ConfigNumber(var n) -> String.valueOf(n);
        case ConfigObject(var map) -> map.toString();
        case ConfigArray(var list) -> list.stream()
            .map(this::extractConfig)
            .collect(Collectors.joining(", "));
    };
}
```

### 2. Error Handling with Result Types

Record patterns make working with algebraic data types elegant:

```java
sealed interface Result<T> permits Success, Error {}
record Success<T>(T value) implements Result<T> {}
record Error(String message) implements Result {}

void handleResult(Result<Integer> result) {
    switch (result) {
        case Success(var value) -> System.out.println("Result: " + value);
        case Error(var msg) -> System.err.println("Error: " + msg);
    }
}
```

### 3. Tree Traversal

Recursive data structures become much easier to work with:

```java
sealed interface Expr permits Constant, Add, Multiply {}
record Constant(int value) implements Expr {}
record Add(Expr left, Expr right) implements Expr {}
record Multiply(Expr left, Expr right) implements Expr {}

int evaluate(Expr expr) {
    return switch (expr) {
        case Constant(var v) -> v;
        case Add(var left, var right) -> evaluate(left) + evaluate(right);
        case Multiply(var left, var right) -> evaluate(left) * evaluate(right);
    };
}
```

## Guard Conditions

You can add `when` clauses to further refine matches:

```java
String describeTemperature(Object obj) {
    return switch (obj) {
        case Point(int x, int y) when x == y -> "Diagonal point";
        case Point(int x, int y) when x > 0 && y > 0 -> "Quadrant I";
        case Point(int x, int y) -> "Other point";
        default -> "Not a point";
    };
}
```

## Performance Considerations

Record patterns are compiled into efficient bytecode. The JVM can optimize pattern matching using techniques like:

- **Type checking caching**: Once a type check passes, subsequent checks are skipped
- **Component extraction inlining**: Accessor methods are inlined at runtime
- **Switch optimization**: Switch on sealed types can be compiled to `tableswitch` or `lookupswitch`

In my benchmarks, record patterns performed equivalently to hand-written instanceof checks with explicit casting.

## Migration Guide

Migrating existing code to use record patterns is straightforward. Start with these steps:

1. **Replace nested getters**: Where you have `obj.getX().getY()`, consider a nested pattern
2. **Simplify instanceof chains**: Convert multiple `if-else` instanceof checks to a single `switch`
3. **Leverage sealed types**: Make your type hierarchies sealed to get exhaustiveness checking

### Before:

```java
if (obj instanceof Point) {
    Point p = (Point) obj;
    int x = p.x();
    int y = p.y();
    // ...
} else if (obj instanceof Circle) {
    Circle c = (Circle) obj;
    int radius = c.radius();
    // ...
}
```

### After:

```java
switch (obj) {
    case Point(int x, int y) -> /* ... */;
    case Circle(Point center, int radius) -> /* ... */;
    default -> /* ... */;
}
```

## Common Pitfalls

1. **Null handling**: Record patterns don't match `null` by default. Always include a `case null` or handle null before the switch.

2. **Generic records**: Record patterns work with generic records, but type inference can be tricky. Use `var` in patterns to let the compiler infer types:

```java
record Box<T>(T content) {}

if (obj instanceof Box(var content)) {
    // content is inferred
}
```

3. **Exhaustiveness**: When using sealed types, ensure all subtypes are covered in your switch. The compiler will warn you if you miss one.

## Under the Hood

When you write:

```java
if (obj instanceof Point(int x, int y)) { ... }
```

The compiler generates something equivalent to:

```java
if (obj instanceof Point) {
    Point p = (Point) obj;
    int x = p.x();
    int y = p.y();
    // ...
}
```

For nested patterns, the compiler generates cascading instanceof checks. The key insight is that **the compiler handles all the boilerplate** while maintaining type safety.

## Real-World Use Case: API Response Processing

Let's look at a complete example from a real application—processing a paginated API response:

```java
sealed interface ApiResponse permits Success, Error, Loading {}
record Success<T>(List<T> data, int totalPages, int currentPage) implements ApiResponse {}
record Error(String message, int code) implements ApiResponse {}
record Loading(int progress) implements ApiResponse {}

void handleResponse(ApiResponse response) {
    switch (response) {
        case Success(var data, var totalPages, var currentPage) when currentPage < totalPages -> {
            System.out.println("Loading page " + (currentPage + 1) + " of " + totalPages);
            processData(data);
        }
        case Success(var data, _, _) -> {
            System.out.println("Last page loaded");
            processData(data);
        }
        case Error(var message, var code) when code >= 500 -> 
            System.err.println("Server error: " + message);
        case Error(var message, _) -> 
            System.err.println("Client error: " + message);
        case Loading(var progress) -> 
            System.out.println("Loading... " + progress + "%");
    }
}
```

Notice the use of `_` (underscore) for unused components—a Java 21 feature that pairs perfectly with record patterns.

## Key Takeaways

- **Record patterns** let you destructure records directly in `instanceof` and `switch`, eliminating boilerplate accessor calls
- **Nested patterns** compose naturally, making deeply nested data structures easy to work with
- **Guard conditions** (`when`) add fine-grained control over pattern matching
- **Sealed types + record patterns** provide exhaustive pattern matching, reducing runtime errors
- **Performance** is on par with hand-written code, with potential JVM optimizations
- **Migration** is incremental—you can start using record patterns in new code and gradually refactor existing code

Record patterns represent a significant leap forward in Java's expressiveness. They make data-centric code cleaner, safer, and more aligned with how we think about data structures. Start using them today—your future self (and your code reviewers) will thank you.