---
title: "Spring Boot Graceful Shutdown: Why and How"
date: 2026-06-29
tags: [Spring Boot, Graceful Shutdown, Java, Microservices, Production]
categories: [Java]
cover:
description: Learn why graceful shutdown matters in Spring Boot, how to configure it, and best practices for zero-downtime deployments in production.
---

# Spring Boot Graceful Shutdown: Why and How

Imagine this: you're deploying a new version of your Spring Boot microservice to production. You send a kill signal to the old process, expecting a clean handover. Instead, you get a flood of error alerts—users are seeing 503s, database connections are severed mid-transaction, and in-flight requests are dropped like hot potatoes. Sound familiar?

This is the reality of an ungraceful shutdown. In a world of microservices, Kubernetes, and high-availability expectations, how you stop your application is just as important as how you start it. In this post, I'll walk you through why graceful shutdown matters, how Spring Boot makes it dead simple, and what pitfalls to avoid in production.

## Why Graceful Shutdown Matters

When you kill a Spring Boot application with `SIGTERM` (the default signal sent by Kubernetes, Docker, or `kill`), the JVM shuts down immediately unless you handle it. Without graceful shutdown, here's what goes wrong:

- **In-flight HTTP requests are aborted**: Clients see connection resets or timeouts.
- **Database transactions are interrupted**: You risk data corruption or incomplete writes.
- **Message queue consumers drop messages**: RabbitMQ, Kafka, or SQS consumers lose unacknowledged messages.
- **External caches or state stores become inconsistent**: Redis, Hazelcast, or infinispan entries may be stale.
- **Metrics and tracing become garbage**: You lose visibility into what was happening at shutdown.

Graceful shutdown solves these problems by allowing your application to finish processing active work before terminating. It's not just a nice-to-have—it's a requirement for zero-downtime deployments.

## How Spring Boot Handles Shutdown

Spring Boot has built-in support for graceful shutdown since version 2.3. It leverages the underlying web server's capabilities (Tomcat, Jetty, Undertow, or Netty) to stop accepting new requests while allowing existing ones to complete.

### The Default Behavior

By default, Spring Boot does **not** enable graceful shutdown. If you send a `SIGTERM`, the application stops immediately, regardless of pending work. This is fine for development but dangerous in production.

### Enabling Graceful Shutdown

Starting with Spring Boot 2.3, you can enable it with a single property:

```yaml
# application.yml
server:
  shutdown: graceful
```

Or in `application.properties`:

```properties
server.shutdown=graceful
```

That's it. With this configuration, when the application receives a shutdown signal, it stops accepting new requests and waits for active requests to finish before shutting down.

### Configuring the Timeout

By default, Spring Boot waits up to 30 seconds for in-flight requests to complete. After that, it forces a shutdown. You can adjust this timeout:

```yaml
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

Set this value based on your expected maximum request duration. If your application handles long-running tasks (e.g., file uploads, batch jobs), you may need a longer timeout. Be careful not to set it too high—your orchestrator (Kubernetes, for example) may kill the pod before your application finishes.

## Deep Dive: What Happens Under the Hood

When graceful shutdown is enabled, Spring Boot registers a shutdown hook that orchestrates a multi-phase shutdown sequence:

1. **Signal received**: The JVM catches `SIGTERM` (or `SIGINT` from Ctrl+C).
2. **Web server stops accepting new requests**: The embedded server (Tomcat, Jetty, etc.) closes its connector, rejecting new connections with a 503 or connection refused.
3. **Active requests are drained**: The server waits for all in-flight requests to complete, up to the configured timeout.
4. **Spring context closes**: The `ApplicationContext` begins its shutdown sequence, which includes:
   - Destroying beans (calling `@PreDestroy` methods)
   - Closing the `SmartLifecycle` beans in reverse order
   - Releasing resources (database connections, thread pools, etc.)
5. **JVM exits**: Once the context is closed, the JVM terminates.

### Code Example: Observing the Shutdown

Let's create a simple controller to demonstrate:

```java
@RestController
public class SlowController {

    @GetMapping("/slow")
    public ResponseEntity<String> slowEndpoint() throws InterruptedException {
        System.out.println("Request received at " + System.currentTimeMillis());
        Thread.sleep(10000); // Simulate long processing
        System.out.println("Request completed at " + System.currentTimeMillis());
        return ResponseEntity.ok("Done");
    }
}
```

Now, enable graceful shutdown and run the application. Send a request to `/slow`, then quickly send a `SIGTERM` (e.g., `kill <pid>`). You'll see the request completes before the application exits.

## Integration with Kubernetes

Graceful shutdown is critical in Kubernetes environments. When you update a deployment, Kubernetes:

1. Sends `SIGTERM` to the pod.
2. Waits for the `terminationGracePeriodSeconds` (default 30 seconds).
3. If the pod hasn't stopped, sends `SIGKILL`.

Your Spring Boot application's `timeout-per-shutdown-phase` should be **less than** Kubernetes' `terminationGracePeriodSeconds` to avoid being killed prematurely.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 45
      containers:
      - name: my-app
        image: my-app:latest
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: 8080
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: 8080
```

In this example, Kubernetes waits 45 seconds before sending `SIGKILL`. Your Spring Boot app should have `timeout-per-shutdown-phase` set to something like 35s to give it a buffer.

### Health Probes and Shutdown

To avoid routing traffic to a shutting-down pod, configure Kubernetes readiness probes to fail when the application is shutting down. Spring Boot Actuator provides this out of the box with the `readiness` endpoint:

```yaml
# application.yml
management:
  endpoint:
    health:
      probes:
        enabled: true
  health:
    readinessstate:
      enabled: true
```

When graceful shutdown begins, Spring Boot automatically sets the readiness state to `REFUSING_TRAFFIC`, causing the readiness probe to fail. Kubernetes then removes the pod from service endpoints.

## Advanced Configuration

### Custom Shutdown Behavior with `SmartLifecycle`

If you have custom components that need to be shut down in a specific order, implement `SmartLifecycle`:

```java
@Component
public class CustomShutdownBean implements SmartLifecycle {

    private boolean running = false;

    @Override
    public void start() {
        running = true;
        System.out.println("Custom component started");
    }

    @Override
    public void stop() {
        System.out.println("Custom component shutting down...");
        // Perform cleanup
        running = false;
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public int getPhase() {
        return 0; // Lower values shut down first
    }
}
```

### Graceful Shutdown for Reactive Applications

If you're using Spring WebFlux with Netty, graceful shutdown works similarly:

```yaml
server:
  shutdown: graceful
```

Netty will stop accepting new connections and drain existing ones. The same timeout configuration applies.

### Handling Database Connections

During shutdown, you want to ensure database connection pools are drained gracefully. HikariCP (Spring Boot's default) supports this via the `idleTimeout` and `maxLifetime` settings. However, you can also hook into the shutdown:

```java
@Configuration
public class DatabaseShutdownConfig {

    @Bean
    public DataSource dataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:postgresql://localhost/mydb");
        config.setUsername("user");
        config.setPassword("pass");
        config.setMaximumPoolSize(10);
        config.setMinimumIdle(2);
        config.setIdleTimeout(30000);
        config.setMaxLifetime(60000);
        config.setConnectionTimeout(30000);
        return new HikariDataSource(config);
    }
}
```

Spring Boot will close the `DataSource` during context shutdown, which in turn closes the HikariCP pool gracefully.

## Common Pitfalls and How to Avoid Them

### 1. Thread Pools Not Drained

If you use `@Async` or `ExecutorService`, make sure they are properly shut down. Spring's `ThreadPoolTaskExecutor` implements `SmartLifecycle` and will shut down automatically, but custom executors need manual handling.

```java
@Bean
public ExecutorService customExecutor() {
    return Executors.newFixedThreadPool(10);
}
```

This won't shut down gracefully. Instead, use Spring's `ThreadPoolTaskExecutor`:

```java
@Bean
public ThreadPoolTaskExecutor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(10);
    executor.setWaitForTasksToCompleteOnShutdown(true);
    executor.setAwaitTerminationSeconds(30);
    return executor;
}
```

### 2. Long-Running Background Tasks

If you have scheduled tasks or background threads that don't respond to interruption, they may prevent shutdown. Use `@Scheduled` with a configurable timeout or implement `SmartLifecycle` to stop them.

### 3. Ignoring the Timeout

Don't set `timeout-per-shutdown-phase` too high. If your orchestrator kills the pod before the timeout expires, you'll get an ungraceful shutdown anyway. Align it with your Kubernetes `terminationGracePeriodSeconds`.

### 4. Not Testing Shutdown

Graceful shutdown is easy to test locally with a simple script:

```bash
#!/bin/bash
# Start the app in background
java -jar my-app.jar &
PID=$!
sleep 2

# Send a request and immediately kill
curl http://localhost:8080/slow &
sleep 1
kill -15 $PID
wait $PID
echo "App exited with code $?"
```

## Monitoring Shutdown Events

You can log shutdown events for debugging:

```java
@Component
public class ShutdownListener {

    private static final Logger log = LoggerFactory.getLogger(ShutdownListener.class);

    @EventListener
    public void onShutdown(ContextClosedEvent event) {
        log.info("Application shutting down...");
    }
}
```

Or expose shutdown metrics via Micrometer:

```yaml
management:
  metrics:
    export:
      prometheus:
        enabled: true
```

Then monitor `spring.application.shutdown.timeout` and `tomcat.sessions.active.current` to ensure shutdowns are clean.

## Real-World Example: Microservices Deployment

Let's tie everything together with a production-grade configuration:

```yaml
# application.yml
server:
  shutdown: graceful
  tomcat:
    connection-timeout: 5s
    max-connections: 1000
    threads:
      max: 200

spring:
  lifecycle:
    timeout-per-shutdown-phase: 25s
  task:
    execution:
      shutdown:
        await-termination: true
        await-termination-period: 20s

management:
  endpoint:
    health:
      probes:
        enabled: true
  health:
    readinessstate:
      enabled: true
```

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 30
      containers:
      - name: my-app
        image: my-app:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

With this setup, when Kubernetes updates the deployment:

1. The pod receives `SIGTERM`.
2. Spring Boot sets readiness to `REFUSING_TRAFFIC`.
3. Kubernetes removes the pod from the service.
4. Active requests complete within 25 seconds.
5. If any task executor is still busy, it waits up to 20 seconds.
6. After 30 seconds, Kubernetes sends `SIGKILL`.

## Key Takeaways

- **Graceful shutdown prevents dropped requests and data corruption** by allowing in-flight work to complete before termination.
- **Enable it with `server.shutdown=graceful`** in Spring Boot 2.3+. It's a one-liner that makes a huge difference.
- **Align your shutdown timeout with your orchestrator's grace period** (e.g., Kubernetes `terminationGracePeriodSeconds`).
- **Use Spring Boot Actuator's readiness probe** to signal Kubernetes to stop routing traffic during shutdown.
- **Configure `ThreadPoolTaskExecutor` with `waitForTasksToCompleteOnShutdown=true`** to handle async tasks gracefully.
- **Test your shutdown behavior** locally and in staging environments before deploying to production.
- **Monitor shutdown events** via logs and metrics to catch issues early.

Graceful shutdown is not just about being polite to your users—it's about building robust, production-ready systems that can withstand the chaos of modern infrastructure. With Spring Boot's built-in support, there's no excuse not to implement it.