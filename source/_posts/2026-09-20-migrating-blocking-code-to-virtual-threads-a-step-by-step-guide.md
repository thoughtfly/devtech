---
title: "Migrating Blocking Code to Virtual Threads: A Step-by-Step Guide"
date: 2026-09-20
tags: [Java, Virtual Threads, Concurrency, Performance, Java 21]
categories: [Java]
cover: "https://images.unsplash.com/photo-1593720217529-01f0a5d09aed?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to migrate legacy Java applications from platform threads to virtual threads. Practical guide with code examples, pitfalls, and performance tips.
---

## Introduction

For over two decades, Java developers have relied on the platform thread model to handle concurrent workloads. While effective, this model has inherent limitations: each thread maps to an OS thread, consuming significant memory and resources. As applications grow more demanding, the traditional approach struggles to scale efficiently.

Enter virtual threads, introduced in Java 21 as a standard feature. Virtual threads are lightweight, managed by the JVM rather than the OS, and can handle millions of concurrent tasks with minimal overhead. But migrating existing code isn't always straightforward.

In this guide, we'll walk through the process of migrating blocking code to virtual threads, covering everything from assessment to deployment.

## Understanding the Problem

Before diving into migration, let's understand why virtual threads matter. Platform threads are expensive:

- **Memory overhead**: Each platform thread typically requires 1MB of stack space
- **Context switching**: OS-level thread switching is costly
- **Limited scalability**: Creating thousands of platform threads leads to resource exhaustion

Virtual threads solve these problems by:

- **Lightweight memory**: Only a few hundred bytes per virtual thread
- **JVM-managed scheduling**: No OS context switching overhead
- **Massive concurrency**: Handle millions of concurrent operations

## Step 1: Assess Your Codebase

The first step is identifying blocking operations in your application. Common culprits include:

- Database queries
- HTTP client calls
- File I/O operations
- Network socket operations
- Synchronous API calls

### Identifying Blocking Code

Use profiling tools to identify hotspots. Here's a simple example of blocking code that's a good candidate for virtual threads:

```java
public class LegacyService {
    
    public String fetchData(String url) {
        // Blocking HTTP call
        HttpResponse<String> response = HttpRequest
            .newBuilder()
            .uri(URI.create(url))
            .GET()
            .timeout(Duration.ofSeconds(30))
            .build()
            .send();
        return response.body();
    }
    
    public List<User> getUsers() {
        // Blocking database query
        try (Connection conn = dataSource.getConnection()) {
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT * FROM users");
            List<User> users = new ArrayList<>();
            while (rs.next()) {
                users.add(new User(rs.getLong("id"), rs.getString("name")));
            }
            return users;
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }
}
```

## Step 2: Update Dependencies

Ensure your project uses Java 21 or later and update your build configuration:

### Maven Configuration

```xml
<properties>
    <java.version>21</java.version>
    <maven.compiler.source>21</maven.compiler.source>
    <maven.compiler.target>21</maven.compiler.target>
</properties>
```

### Gradle Configuration

```groovy
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

## Step 3: Convert Thread Creation

The most straightforward migration involves replacing platform thread creation with virtual threads.

### Before: Platform Threads

```java
ExecutorService executor = Executors.newFixedThreadPool(100);

// Submit tasks using platform threads
executor.submit(() -> {
    String result = service.fetchData("https://api.example.com/data");
    processResult(result);
});
```

### After: Virtual Threads

```java
// Option 1: Using Thread.ofVirtual()
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

executor.submit(() -> {
    String result = service.fetchData("https://api.example.com/data");
    processResult(result);
});

// Option 2: Using Thread.startVirtualThread() for one-off tasks
Thread.startVirtualThread(() -> {
    String result = service.fetchData("https://api.example.com/data");
    processResult(result);
});
```

## Step 4: Handle ThreadLocal Variables

Virtual threads don't share ThreadLocal values with platform threads. If your code relies on ThreadLocal, you need to adapt:

### Problem: ThreadLocal in Virtual Threads

```java
public class RequestContext {
    private static final ThreadLocal<User> currentUser = new ThreadLocal<>();
    
    public static void setUser(User user) {
        currentUser.set(user);
    }
    
    public static User getUser() {
        return currentUser.get();
    }
}
```

### Solution: Use InheritableThreadLocal or Scoped Values

```java
// Option 1: InheritableThreadLocal (works with virtual threads)
private static final InheritableThreadLocal<User> currentUser = new InheritableThreadLocal<>();

// Option 2: Scoped Values (Java 21+, preferred for performance)
private static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

ScopedValue.where(CURRENT_USER, user)
    .run(() -> {
        // Code that accesses CURRENT_USER.get()
        processRequest();
    });
```

## Step 5: Address Synchronized Blocks

Virtual threads can cause issues with synchronized blocks due to pinning. When a virtual thread holds a monitor, it can't be unpinned, blocking the carrier thread.

### Problem: Synchronized with Virtual Threads

```java
public class SharedResource {
    private final List<String> data = new ArrayList<>();
    
    public synchronized void add(String item) {
        // This can pin the virtual thread
        data.add(item);
        simulateBlockingOperation();
    }
}
```

### Solution: Use ReentrantLock or Reduce Synchronization

```java
import java.util.concurrent.locks.ReentrantLock;

public class SharedResource {
    private final List<String> data = new ArrayList<>();
    private final ReentrantLock lock = new ReentrantLock();
    
    public void add(String item) {
        lock.lock();
        try {
            data.add(item);
            simulateBlockingOperation();
        } finally {
            lock.unlock();
        }
    }
}
```

## Step 6: Migrate Connection Pools

Traditional connection pools are designed for platform threads. With virtual threads, you need pools that support virtual thread awareness.

### JDBC Connection Pool Configuration

```yaml
# application.yml
spring:
  datasource:
    hikari:
      # Virtual threads don't need large pools
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
```

### Custom Virtual Thread-Aware Pool

```java
public class VirtualThreadAwarePool {
    private final Queue<Connection> available = new ArrayDeque<>();
    private final int maxSize;
    
    public VirtualThreadAwarePool(int maxSize) {
        this.maxSize = maxSize;
    }
    
    public Connection getConnection() throws SQLException {
        // Try to get from pool
        Connection conn = available.poll();
        if (conn != null) {
            return conn;
        }
        
        // Create new connection if under limit
        if (available.size() < maxSize) {
            return createConnection();
        }
        
        // Wait for connection with virtual thread awareness
        return waitForConnection();
    }
}
```

## Step 7: Update HTTP Clients

Modern HTTP clients work well with virtual threads. Here's how to configure them:

### Using HttpClient (Java 11+)

```java
// HttpClient works seamlessly with virtual threads
HttpClient client = HttpClient.newHttpClient();

// Use with virtual threads
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

List<CompletableFuture<String>> futures = urls.stream()
    .map(url -> CompletableFuture.supplyAsync(() -> {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .GET()
                .build();
            HttpResponse<String> response = client.send(request, 
                BodyHandlers.ofString());
            return response.body();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }, executor))
    .toList();

// Wait for all results
List<String> results = futures.stream()
    .map(CompletableFuture::join)
    .toList();
```

### Using OkHttp with Virtual Threads

```java
OkHttpClient client = new OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(30, TimeUnit.SECONDS)
    .build();

ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

List<Call> calls = urls.stream()
    .map(url -> {
        Request request = new Request.Builder()
            .url(url)
            .build();
        return client.newCall(request);
    })
    .toList();

List<Response> responses = calls.stream()
    .map(call -> {
        try {
            return executor.submit(call::execute).get();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    })
    .toList();
```

## Step 8: Monitor and Tune

After migration, monitor your application to ensure virtual threads are performing as expected.

### Key Metrics to Track

- **Thread count**: Should be much higher than platform threads
- **CPU usage**: Should be similar or lower due to better scheduling
- **Memory usage**: Should decrease significantly
- **Response times**: Should improve under load

### JMX Monitoring

```java
// Monitor virtual threads via JMX
ThreadMXBean threadMXBean = ManagementFactory.getThreadMXBean();

long virtualThreadCount = Arrays.stream(threadMXBean.getAllThreadIds())
    .mapToObj(id -> threadMXBean.getThreadInfo(id, Long.MAX_VALUE))
    .filter(info -> info != null && info.getThreadType() == Thread.Type.VIRTUAL)
    .count();

System.out.println("Virtual threads: " + virtualThreadCount);
```

## Common Pitfalls and Solutions

### Pitfall 1: Thread Dump Analysis

Thread dumps show virtual threads differently. Use the `-XX:+PrintVirtualThreads` flag for better visibility.

```bash
# Generate thread dump with virtual thread details
jcmd <pid> Thread.print -v
```

### Pitfall 2: Blocking in Synchronized Blocks

As mentioned earlier, avoid synchronized blocks with virtual threads. Use ReentrantLock or other concurrent utilities.

### Pitfall 3: Excessive Thread Creation

While virtual threads are lightweight, creating millions of them still has costs. Use appropriate pool sizes for shared resources.

### Pitfall 4: Testing with Limited Concurrency

Ensure your tests exercise high concurrency to validate virtual thread behavior.

```java
@Test
void testHighConcurrency() throws Exception {
    ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
    
    int threadCount = 10000;
    CountDownLatch startLatch = new CountDownLatch(1);
    CountDownLatch doneLatch = new CountDownLatch(threadCount);
    
    for (int i = 0; i < threadCount; i++) {
        executor.submit(() -> {
            try {
                startLatch.await();
                service.processRequest();
            } catch (Exception e) {
                throw new RuntimeException(e);
            } finally {
                doneLatch.countDown();
            }
        });
    }
    
    startLatch.countDown();
    doneLatch.await(60, TimeUnit.SECONDS);
    
    executor.shutdown();
}
```

## Performance Comparison

Here's a comparison of platform threads vs. virtual threads:

| Metric | Platform Threads | Virtual Threads |
|--------|------------------|-----------------|
| Memory per thread | ~1MB | ~500 bytes |
| Max concurrent threads | ~1,000 | ~1,000,000+ |
| Context switch cost | High | Low |
| Setup time | Slow | Fast |
| Blocking handling | Poor | Excellent |

## Migration Checklist

1. [ ] Identify all blocking operations
2. [ ] Update to Java 21+
3. [ ] Replace thread pool configurations
4. [ ] Handle ThreadLocal variables
5. [ ] Replace synchronized blocks
6. [ ] Update connection pools
7. [ ] Configure HTTP clients
8. [ ] Add monitoring
9. [ ] Run load tests
10. [ ] Monitor production metrics

## Key Takeaways

- **Virtual threads are lightweight**: They enable massive concurrency with minimal memory overhead
- **Migration is often straightforward**: Many blocking operations work seamlessly with virtual threads
- **Watch out for synchronization**: Avoid synchronized blocks; use ReentrantLock instead
- **ThreadLocal needs attention**: Use InheritableThreadLocal or Scoped Values
- **Connection pools shrink**: Virtual threads don't need large pools for blocking operations
- **Monitor carefully**: Track thread counts, CPU, memory, and response times
- **Test with high concurrency**: Validate behavior under realistic load conditions

Virtual threads represent a paradigm shift in Java concurrency. By following this step-by-step guide, you can migrate your blocking code effectively and unlock the scalability benefits of modern Java concurrency.