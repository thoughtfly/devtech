---
title: "Java 21 Pattern Matching for Switch: Real-World Examples"
date: 2026-06-27
tags: [Java 21, Pattern Matching, Switch Expressions, Java Features]
categories: [Java]
cover:
description: Explore Java 21's pattern matching for switch with practical examples. Learn how to simplify code, handle nulls, and use guards for cleaner, safer logic.
---

# Java 21 Pattern Matching for Switch: Real-World Examples

Java 21 has finally brought pattern matching for switch expressions and statements out of preview and into the language as a permanent feature (JEP 441). This is a game-changer for how we write conditional logic in Java. If you’ve been using `if-else` chains or `switch` statements with type checks and casts, you’re in for a treat. In this post, we’ll explore real-world examples that demonstrate the power and elegance of this feature.

## What Is Pattern Matching for Switch?

At its core, pattern matching for switch allows you to test a value against multiple patterns, each of which can include a type check, a deconstruction, or even a guard condition. The compiler handles the type checks and casts for you, making your code safer and more concise.

Consider the old way of handling different types in a switch:

```java
// Old way (pre-Java 21)
Object obj = getSomeObject();
if (obj instanceof String s) {
    System.out.println("String: " + s);
} else if (obj instanceof Integer i) {
    System.out.println("Integer: " + i);
} else {
    System.out.println("Unknown type");
}
```

With Java 21, you can write this instead:

```java
// Java 21 pattern matching switch
Object obj = getSomeObject();
switch (obj) {
    case String s -> System.out.println("String: " + s);
    case Integer i -> System.out.println("Integer: " + i);
    default -> System.out.println("Unknown type");
}
```

The syntax is cleaner, and the compiler ensures that you don’t miss any casts. But this is just the beginning.

## Real-World Example 1: Parsing Different Message Types

Imagine you’re building a messaging system that receives payloads of different types: text, image, video, or a command. Without pattern matching, you’d have a chain of `if-else` or a cumbersome switch on a discriminator field. With pattern matching, you can directly switch on the payload object.

```java
public record TextMessage(String content) {}
public record ImageMessage(String url, int width, int height) {}
public record VideoMessage(String url, long durationMs) {}
public record CommandMessage(String command, String[] args) {}

public void handleMessage(Object payload) {
    switch (payload) {
        case TextMessage t -> sendText(t.content());
        case ImageMessage img -> processImage(img.url(), img.width(), img.height());
        case VideoMessage vid -> streamVideo(vid.url(), vid.durationMs());
        case CommandMessage cmd -> executeCommand(cmd.command(), cmd.args());
        case null -> logWarning("Received null payload");
        default -> logError("Unknown payload type: " + payload.getClass());
    }
}
```

Notice how the `case null` is explicitly handled. In previous Java versions, a null value would throw a `NullPointerException` in a switch. Now, you can handle null directly. This eliminates entire categories of bugs.

## Real-World Example 2: Processing Shapes in a Graphics Engine

Suppose you have a hierarchy of shapes in a graphics engine. You want to calculate the area and perimeter of each shape. With pattern matching, you can write a single method that handles all shapes elegantly.

```java
sealed interface Shape permits Circle, Rectangle, Triangle {}
record Circle(double radius) implements Shape {}
record Rectangle(double width, double height) implements Shape {}
record Triangle(double sideA, double sideB, double sideC) implements Shape {}

public double calculateArea(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.radius() * c.radius();
        case Rectangle r -> r.width() * r.height();
        case Triangle t -> {
            double s = (t.sideA() + t.sideB() + t.sideC()) / 2;
            yield Math.sqrt(s * (s - t.sideA()) * (s - t.sideB()) * (s - t.sideC()));
        }
    };
}
```

Because `Shape` is a sealed interface, the compiler knows all possible subtypes. This means you don’t need a `default` case—if you add a new shape later and forget to update the switch, the compiler will warn you. This is a huge safety net for maintainable code.

## Real-World Example 3: Guards for Conditional Logic

Sometimes you need to apply additional conditions to a pattern. For example, you might want to handle a string differently if it starts with a special prefix. Java 21 introduces *guards* (previously called "when clauses" in preview) that let you refine a pattern.

```java
public void processString(Object obj) {
    switch (obj) {
        case String s && s.startsWith("!") -> handleCommand(s.substring(1));
        case String s && s.length() > 100 -> handleLongString(s);
        case String s -> handleNormalString(s);
        case null -> handleNull();
        default -> handleOther(obj);
    }
}
```

Guards can also be used with record patterns. For example, in a trading system, you might want to handle orders above a certain amount differently:

```java
public record Order(String symbol, int quantity, double price) {}

public void processOrder(Order order) {
    switch (order) {
        case Order o && o.price() > 1000.0 -> executeLargeOrder(o);
        case Order o && o.quantity() > 10000 -> executeBulkOrder(o);
        case Order o -> executeStandardOrder(o);
    }
}
```

## Real-World Example 4: Nested Pattern Matching with Records

One of the most powerful aspects of Java 21’s pattern matching is the ability to deconstruct nested records. Imagine you have a JSON-like structure represented as records:

```java
public record JsonObject(Map<String, Object> fields) {}
public record JsonArray(List<Object> elements) {}
public record JsonString(String value) {}
public record JsonNumber(double value) {}
public record JsonBoolean(boolean value) {}
public record JsonNull() {}

public void prettyPrint(Object json, int indent) {
    String prefix = " ".repeat(indent);
    switch (json) {
        case JsonObject obj -> {
            System.out.println(prefix + "{");
            obj.fields().forEach((key, value) -> {
                System.out.print(prefix + "  \"" + key + "\": ");
                prettyPrint(value, indent + 2);
            });
            System.out.println(prefix + "}");
        }
        case JsonArray arr -> {
            System.out.println(prefix + "[");
            arr.elements().forEach(elem -> {
                System.out.print(prefix + "  ");
                prettyPrint(elem, indent + 2);
            });
            System.out.println(prefix + "]");
        }
        case JsonString s -> System.out.println("\"" + s.value() + "\"");
        case JsonNumber n -> System.out.println(n.value());
        case JsonBoolean b -> System.out.println(b.value());
        case JsonNull _ -> System.out.println("null");
        default -> System.out.println("unknown");
    }
}
```

Notice the use of `_` in `case JsonNull _`. This is a pattern variable that we don’t use, so we can ignore it with an underscore. This is a small quality-of-life improvement that reduces clutter.

## Real-World Example 5: Simplifying Visitor Pattern

The Visitor pattern is notorious for its boilerplate. With pattern matching, you can often eliminate the need for a separate visitor class altogether.

Consider an expression evaluator for a simple arithmetic language:

```java
sealed interface Expr permits Constant, Add, Multiply, Negate {}
record Constant(int value) implements Expr {}
record Add(Expr left, Expr right) implements Expr {}
record Multiply(Expr left, Expr right) implements Expr {}
record Negate(Expr inner) implements Expr {}

public int evaluate(Expr expr) {
    return switch (expr) {
        case Constant c -> c.value();
        case Add a -> evaluate(a.left()) + evaluate(a.right());
        case Multiply m -> evaluate(m.left()) * evaluate(m.right());
        case Negate n -> -evaluate(n.inner());
    };
}
```

This is much cleaner than the traditional visitor pattern, which would require separate visitor interfaces and accept methods for each expression type.

## Performance Considerations

Pattern matching for switch is not just syntactic sugar. The Java compiler generates efficient code that is often faster than a chain of `instanceof` checks. The JVM also applies optimizations such as type profiling and inlining. In most cases, you should prefer pattern matching for its readability and safety, without worrying about performance.

However, be mindful of very large switch expressions with many patterns. The compiler may need to generate a decision tree, which could increase class file size. In practice, this is rarely an issue.

## Migration Tips

If you’re upgrading to Java 21 and want to start using pattern matching in your existing codebase, here are some tips:

1. **Start with simple type checks.** Replace `if (x instanceof Foo f) { ... } else if (x instanceof Bar b) { ... }` with a switch.
2. **Add null handling.** Explicitly handle `null` cases to avoid surprises.
3. **Use sealed classes.** If you control the type hierarchy, make it sealed to get exhaustiveness checks from the compiler.
4. **Refactor gradually.** You don’t have to rewrite everything at once. Pattern matching is additive—you can use it alongside legacy code.

## Common Pitfalls to Avoid

- **Forgetting the default case.** Even with sealed types, if your switch is a statement (not an expression), you still need a default unless you cover all possibilities.
- **Overusing guards.** While guards are powerful, complex boolean expressions can make code hard to read. Consider extracting the guard condition into a method.
- **Mixing patterns and constants.** You can combine pattern cases with traditional constant cases, but be careful about ordering. The first matching case wins.

## Conclusion

Java 21’s pattern matching for switch is one of the most significant language enhancements in years. It makes code more expressive, safer, and easier to maintain. By embracing this feature, you can reduce boilerplate, eliminate common bugs like missing null checks, and write code that clearly communicates your intent.

## Key Takeaways

- **Pattern matching for switch** allows type checks, deconstruction, and guards in a single construct, reducing boilerplate and improving readability.
- **Null handling** is now explicit with `case null`, eliminating a major source of runtime errors.
- **Sealed types** combined with pattern matching give you compile-time exhaustiveness checks, ensuring you handle all cases.
- **Record patterns** enable deep deconstruction of nested data structures, making code like JSON processing much cleaner.
- **Guards** (with `&&`) let you add additional conditions to patterns, replacing complex `if-else` chains.
- **Performance** is on par with or better than traditional `instanceof` chains, and the JVM continues to optimize.
- **Migration** can be incremental—start by replacing simple `if-else` chains and gradually adopt more advanced patterns.