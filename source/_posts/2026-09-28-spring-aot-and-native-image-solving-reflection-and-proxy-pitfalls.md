---
title: "Spring AOT and Native Image: Solving Reflection and Proxy Pitfalls"
date: 2026-09-28
tags: [Spring Boot, GraalVM, Native Image, Java, AOT, Performance]
categories: [Java]
cover: "https://images.unsplash.com/photo-1618683141484-edd31f7ad36a?w=1200&q=80&fit=crop&fm=webp"
description: Master Spring AOT and GraalVM Native Image by solving common reflection and proxy pitfalls. Practical guide for Java developers building high-performance nat...
---

## Introduction

If you have ever tried to compile a Spring Boot application into a native binary using GraalVM, you likely hit a wall. The JVM is a dynamic beast; it inspects classes, creates proxies on the fly, and uses reflection extensively. GraalVM Native Image, however, is a static compilation. It needs to know everything at build time. When it encounters code it cannot analyze statically, it throws errors like "Class not found" or "Cannot instantiate proxy."

These are not bugs; they are features of a different execution model. The solution lies in Spring AOT (Ahead-of-Time) compilation and understanding the specific pitfalls of reflection and proxies. In this post, we will dive deep into why these errors occur and how to fix them using modern Spring Boot 3.x patterns.

## Why Native Image is Different

Before solving problems, we must understand the root cause. The standard JVM (HotSpot) uses Just-In-Time (JIT) compilation. It runs your code, gathers statistics, and then optimizes. It also maintains a runtime database of classes, allowing reflection to work dynamically.

GraalVM Native Image uses Ahead-of-Time (AOT) compilation. It analyzes your application's class graph at build time. It removes unused code (dead code elimination) to reduce memory footprint and startup time. However, this means:

1. **Reflection is restricted:** The JIT compiler can dynamically access any field or method. Native Image requires you to declare which fields/methods are accessible via reflection.
2. **Proxies are static:** Dynamic proxies (like those used by Spring’s `@Transactional` or `@Async`) must be generated at build time, not runtime.
3. **Initialization is fixed:** Code that runs during class loading (`static {}` blocks) must be predictable. Runtime initialization is often too complex for the native image builder to handle.

Spring Boot 3.0 introduced built-in support for GraalVM native images. This means you no longer need to manually configure most GraalVM features. Instead, Spring AOT processes your application before packaging, generating the necessary metadata for reflection, proxies, and resources.

## Setting Up the Environment

To follow along, ensure you have:
- Java 17 or 21 (LTS versions recommended)
- Spring Boot 3.2+ (or 3.3+)
- GraalVM installed with the native image toolchain
- Maven or Gradle

For this guide, we will use Maven. Add the native profile to your `pom.xml`:

```xml
<profiles>
    <profile>
        <id>native</id>
        <build>
            <plugins>
                <plugin>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-maven-plugin</artifactId>
                    <configuration>
                        <image>
                            <builder>dashaun/builder:tiny</builder>
                        </image>
                    </configuration>
                    <executions>
                        <execution>
                            <id>process-aot</id>
                            <goals>
                                <goal>process-aot</goal>
                            </goals>
                        </execution>
                    </executions>
                </plugin>
            </plugins>
        </build>
    </profile>
</profiles>
```

Note: The `process-aot` goal is crucial. It triggers Spring’s AOT processor, which generates the configuration files needed for native compilation.

## Pitfall 1: Reflection Errors

Reflection errors are the most common issue. They typically look like this:

```
Error: Detected a started instance of type 'java.util.HashMap' in the image heap. 
Instances created during runtime must be registered explicitly or replaced with 
supplier-based approaches.
```

Or more commonly:

```
Error: Class has multiple methods with the same name: 'equals'
```

This happens when your code uses reflection to access a class that the native image builder cannot analyze statically. For example, if you have a custom serializer or a database driver that uses reflection to map fields, the native image will fail.

### Solution: Use Spring’s Reflection Configuration

Spring Boot automatically configures reflection for many common libraries (like Jackson, JPA, and Hibernate). However, if you have custom classes that are serialized/deserialized dynamically, you need to declare them.

#### Option A: JSON Configuration (Jackson)

If you are using Jackson, create a `reflect-config.json` file in `src/main/resources/META-INF/native-image/your-app/`:

```json
[
  {
    "name": "com.example.MyCustomClass",
    "allDeclaredConstructors": true,
    "allPublicConstructors": true,
    "allDeclaredMethods": true,
    "allPublicMethods": true,
    "allDeclaredFields": true,
    "allPublicFields": true
  }
]
```

This tells the native image builder that `MyCustomClass` can be accessed via reflection.

#### Option B: Annotation-Based Configuration

Alternatively, you can use annotations in your code. For Jackson, add `@JsonSerialize` or `@JsonDeserialize` with explicit types. For other libraries, check if they support GraalVM-native annotations.

#### Option C: Spring AOT Auto-Configuration

Often, the best solution is to let Spring AOT handle it. Ensure your application is using Spring Boot 3.2+ and that the `spring-boot-maven-plugin` is configured with the `process-aot` goal. Spring AOT will analyze your code and generate the necessary reflection configuration automatically for many common patterns.

## Pitfall 2: Proxy Generation Failures

Spring uses proxies extensively for features like `@Transactional`, `@Async`, and `@Cacheable`. In the JVM, these proxies are created at runtime using JDK dynamic proxies or CGLIB. In Native Image, this is not possible because the class graph is fixed.

You might see an error like:

```
Error: Unsupported proxy generation at runtime. 
Proxy classes must be generated at build time.
```

### Solution: Build-Time Proxy Generation

Spring Boot 3.x handles this automatically for most cases. The AOT processor generates proxy classes at build time. However, if you are using custom proxy logic or third-party libraries that create proxies dynamically, you may need to configure them.

#### For Custom Proxies

If you are using a library that creates proxies dynamically, check if it has a GraalVM-native alternative. For example, if you are using a custom AOP framework, ensure it supports build-time proxy generation.

#### For JPA/Hibernate

Hibernate uses proxies for lazy loading. Spring Boot’s native support includes Hibernate-specific AOT processors. Ensure you are using the latest Hibernate version compatible with Spring Boot 3.x.

## Pitfall 3: Resource Loading

Native Image bundles resources (like configuration files, templates, etc.) into the binary. However, if your code tries to load resources dynamically using `Class.getResourceAsStream()` with a path that is not known at build time, it may fail.

Example error:

```
Error: Resource 'config/unknown.properties' not found.
```

### Solution: Resource Configuration

Create a `resource-config.json` file in `src/main/resources/META-INF/native-image/your-app/`:

```json
{
  "resources": [
    {
      "pattern": "config/.*\\.properties"
    },
    {
      "pattern": "messages/.*\\.properties"
    }
  ]
}
```

This ensures that matching resources are bundled into the native image.

## Pitfall 4: Dynamic Class Loading

Some libraries use dynamic class loading (e.g., `Class.forName()`). This is not supported in Native Image because the class must be known at build time.

Example error:

```
Error: Class 'com.example.DynamicClass' not found.
```

### Solution: Substitution and Feature Registration

#### Option A: Substitution

You can substitute the dynamic class loading with a static one. Create a substitution class:

```java
import org.graalvm.nativeimage.hosted.Feature;
import com.oracle.svm.core.annotate.Substitute;
import com.oracle.svm.core.annotate.TargetClass;

@TargetClass(className = "com.example.DynamicLoader")
final class Target_DynamicLoader {
    @Substitute
    public static Class<?> loadClass(String name) {
        if ("com.example.DynamicClass".equals(name)) {
            return com.example.DynamicClass.class;
        }
        throw new IllegalArgumentException("Unknown class: " + name);
    }
}
```

#### Option B: Feature Registration

For more complex cases, you can write a GraalVM feature to register the class. This is advanced and rarely needed with Spring Boot’s auto-configuration.

## Pitfall 5: Initialization Errors

Native Image has strict rules about initialization. Code that runs during class loading (`static {}` blocks) must be predictable. If your code initializes resources at runtime (e.g., connecting to a database in a `static` block), it may fail.

Example error:

```
Error: Class initialization of 'com.example.DatabaseConnection' failed.
```

### Solution: Delay Initialization

Avoid static initialization. Use lazy initialization or Spring’s dependency injection to initialize resources at runtime. Spring AOT can help with this by generating initialization code that is safe for native images.

## Best Practices for Spring AOT and Native Image

1. **Use Spring Boot 3.2+**: Newer versions have better native image support.
2. **Enable AOT Processing**: Always use the `process-aot` goal in your build plugin.
3. **Minimize Reflection**: Avoid using reflection in your application code. Use typed APIs where possible.
4. **Check Library Compatibility**: Ensure all dependencies have GraalVM-native support or alternatives.
5. **Test Locally First**: Compile to native image locally before deploying. Use the `./mvnw -Pnative native:compile` command.
6. **Monitor Build Logs**: GraalVM build logs are verbose. Look for warnings about unreachable classes or resources.

## Debugging Native Image Issues

When you encounter an error, follow these steps:

1. **Identify the Class**: The error message usually specifies the class that failed.
2. **Check if It’s Used**: Determine if the class is used via reflection, dynamic loading, or proxy generation.
3. **Add Configuration**: Add the appropriate configuration file (`reflect-config.json`, `resource-config.json`, etc.).
4. **Rebuild**: Run the native image build again.
5. **Iterate**: Native image compilation is iterative. You will likely need to fix multiple issues.

## Conclusion

Spring AOT and Native Image are powerful tools for building high-performance, low-latency Java applications. However, they require a shift in mindset from dynamic JVM execution to static compilation. By understanding and addressing reflection and proxy pitfalls, you can leverage the benefits of native images without getting stuck on common errors.

Remember: Spring Boot’s auto-configuration handles many of these issues automatically. Focus on writing clean, static code and using the latest Spring Boot version. When issues arise, use the configuration files and substitution techniques outlined in this post to resolve them.

## Key Takeaways

- **Native Image is static**: It requires all classes, resources, and proxies to be known at build time.
- **Reflection must be declared**: Use `reflect-config.json` or Spring AOT auto-configuration to allow reflection.
- **Proxies are generated at build time**: Spring Boot handles this automatically for most use cases.
- **Resources must be bundled**: Use `resource-config.json` to include dynamic resources.
- **Avoid dynamic class loading**: Use substitution or static initialization instead.
- **Iterate on errors**: Native image compilation is iterative; fix issues one by one.
- **Use Spring Boot 3.2+**: Newer versions have better native image support and auto-configuration.