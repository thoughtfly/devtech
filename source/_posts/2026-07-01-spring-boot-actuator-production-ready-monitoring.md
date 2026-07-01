---
title: "Spring Boot Actuator: Production-Ready Monitoring for Your Microservices"
date: 2026-07-01
tags: [Spring Boot, Actuator, Monitoring, Microservices, DevOps]
categories: [Java]
cover:
description: Learn how to use Spring Boot Actuator for production monitoring, health checks, metrics, and custom endpoints. Includes code examples and best practices.
---

# Spring Boot Actuator: Production-Ready Monitoring for Your Microservices

You've just deployed your Spring Boot application to production. The deployment went smoothly, but now you're staring at a terminal, wondering: *Is my app actually healthy? How many requests are being processed? Is memory usage about to spike?* This is where Spring Boot Actuator comes to the rescue.

Spring Boot Actuator is a set of production-ready features that help you monitor and manage your application in any environment. It exposes operational information via HTTP endpoints and JMX MBeans, giving you deep visibility into your running application. In this post, we'll explore how to set up, secure, and extend Actuator for real-world monitoring scenarios.

## Getting Started with Actuator

To add Actuator to your Spring Boot project, include the following dependency:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

For Gradle:

```groovy
implementation 'org.springframework.boot:spring-boot-starter-actuator'
```

That's it! By default, Actuator exposes several endpoints over HTTP. The most commonly used ones include:

- `/actuator/health` - Application health information
- `/actuator/info` - Custom application information
- `/actuator/metrics` - Application metrics
- `/actuator/env` - Environment properties
- `/actuator/beans` - Spring beans in the context

Let's start by accessing the health endpoint:

```bash
curl http://localhost:8080/actuator/health
```

You'll get a simple response:

```json
{"status":"UP"}
```

## Configuring Actuator Endpoints

By default, only the `/health` and `/info` endpoints are exposed over HTTP. To expose more endpoints, configure them in `application.yml`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,env,beans,loggers
```

You can also expose all endpoints (not recommended for production):

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
```

For fine-grained control, use `exclude`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
        exclude: env,beans
```

## Health Checks: Beyond UP/DOWN

The health endpoint is the most critical for production monitoring. By default, it aggregates health indicators from various components (database, disk space, etc.). You can customize it to include your own checks.

### Custom Health Indicator

Let's create a health indicator that checks if an external API is reachable:

```java
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class ExternalApiHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        try {
            // Simulate checking an external API
            boolean apiReachable = checkExternalApi();
            if (apiReachable) {
                return Health.up()
                        .withDetail("api", "reachable")
                        .withDetail("latency", "120ms")
                        .build();
            } else {
                return Health.down()
                        .withDetail("api", "unreachable")
                        .build();
            }
        } catch (Exception e) {
            return Health.down(e).build();
        }
    }

    private boolean checkExternalApi() {
        // Actual HTTP call logic here
        return true;
    }
}
```

Now when you hit `/actuator/health`, you'll see detailed information:

```json
{
  "status": "UP",
  "components": {
    "diskSpace": {
      "status": "UP",
      "details": {
        "total": 499963170816,
        "free": 123456789,
        "threshold": 10485760
      }
    },
    "externalApi": {
      "status": "UP",
      "details": {
        "api": "reachable",
        "latency": "120ms"
      }
    },
    "ping": {
      "status": "UP"
    }
  }
}
```

### Health Groups

You can group health indicators for specific audiences. For example, create a group for load balancers that only checks critical components:

```yaml
management:
  endpoint:
    health:
      group:
        liveness:
          include: ping,diskSpace
        readiness:
          include: ping,diskSpace,externalApi
```

Now you can check:

```bash
curl http://localhost:8080/actuator/health/liveness
curl http://localhost:8080/actuator/health/readiness
```

This is especially useful for Kubernetes liveness and readiness probes.

## Metrics: The Pulse of Your Application

Actuator integrates with Micrometer to provide dimensional metrics. By default, it collects JVM metrics, system metrics, and more. Let's explore some useful metrics.

### Built-in Metrics

Access `/actuator/metrics` to see available metric names:

```json
{
  "names": [
    "jvm.memory.used",
    "jvm.memory.max",
    "jvm.gc.pause",
    "http.server.requests",
    "process.cpu.usage",
    "system.cpu.usage",
    "logback.events",
    "disk.free",
    "disk.total"
  ]
}
```

To view a specific metric, add its name:

```bash
curl http://localhost:8080/actuator/metrics/jvm.memory.used
```

Response:

```json
{
  "name": "jvm.memory.used",
  "description": "The amount of used memory",
  "baseUnit": "bytes",
  "measurements": [
    {
      "statistic": "VALUE",
      "value": 256000000
    }
  ],
  "availableTags": [
    {
      "tag": "area",
      "values": ["heap", "nonheap"]
    },
    {
      "tag": "id",
      "values": ["PS Eden Space", "PS Old Gen", ...]
    }
  ]
}
```

### Custom Metrics

You can record custom metrics using Micrometer's `MeterRegistry`:

```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Counter;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    private final Counter orderCounter;

    public OrderService(MeterRegistry registry) {
        this.orderCounter = Counter.builder("orders.created")
                .description("Number of orders created")
                .register(registry);
    }

    public void createOrder() {
        // Business logic
        orderCounter.increment();
    }
}
```

Now you can query:

```bash
curl http://localhost:8080/actuator/metrics/orders.created
```

## Info Endpoint: Your Application's Identity Card

The `/info` endpoint exposes custom application information. Configure it in `application.yml`:

```yaml
info:
  app:
    name: @project.name@
    version: @project.version@
    description: @project.description@
  build:
    artifact: @project.artifactId@
    group: @project.groupId@
  contact:
    team: platform-engineering
    slack: #app-monitoring
```

With Maven resource filtering, the `@...@` placeholders are replaced at build time. The response will look like:

```json
{
  "app": {
    "name": "order-service",
    "version": "1.2.3",
    "description": "Order management microservice"
  },
  "build": {
    "artifact": "order-service",
    "group": "com.example"
  },
  "contact": {
    "team": "platform-engineering",
    "slack": "#app-monitoring"
  }
}
```

## Securing Actuator Endpoints

Exposing operational information to the world is dangerous. You must secure Actuator endpoints, especially in production.

### Using Spring Security

If you have Spring Security on the classpath, Actuator endpoints are automatically secured. You can configure access rules:

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class ActuatorSecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/actuator/info").permitAll()
                .requestMatchers("/actuator/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .httpBasic();
        return http.build();
    }
}
```

### Using Management Port

For better isolation, run Actuator on a separate port:

```yaml
management:
  server:
    port: 8081
  endpoints:
    web:
      base-path: /internal
```

Now Actuator is accessible at `http://localhost:8081/internal/health`. This allows you to firewall the management port separately from the main application port.

## Custom Endpoints

Sometimes built-in endpoints aren't enough. You can create custom endpoints for domain-specific operations.

### Custom @Endpoint

Let's create an endpoint that exposes cache statistics:

```java
import org.springframework.boot.actuate.endpoint.annotation.Endpoint;
import org.springframework.boot.actuate.endpoint.annotation.ReadOperation;
import org.springframework.stereotype.Component;

@Component
@Endpoint(id = "cache-stats")
public class CacheStatsEndpoint {

    private final CacheManager cacheManager;

    public CacheStatsEndpoint(CacheManager cacheManager) {
        this.cacheManager = cacheManager;
    }

    @ReadOperation
    public Map<String, Object> cacheStats() {
        Map<String, Object> stats = new HashMap<>();
        for (String name : cacheManager.getCacheNames()) {
            Cache cache = cacheManager.getCache(name);
            // Access native cache for statistics
            stats.put(name, getNativeCacheStats(cache));
        }
        return stats;
    }

    private Map<String, Object> getNativeCacheStats(Cache cache) {
        // Implementation depends on cache provider
        return Map.of("size", 100, "hitRate", 0.85);
    }
}
```

Now you can access `GET /actuator/cache-stats`.

### Write Operations

You can also expose write operations:

```java
@Endpoint(id = "cache-actions")
public class CacheActionsEndpoint {

    @WriteOperation
    public String clearCache(@Selector String cacheName) {
        Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            cache.clear();
            return "Cache " + cacheName + " cleared";
        }
        return "Cache " + cacheName + " not found";
    }
}
```

This allows you to clear a cache by sending a `POST` to `/actuator/cache-actions/myCache`.

## Integration with Monitoring Systems

Actuator metrics can be exported to popular monitoring systems. Here are two common setups.

### Prometheus

Add the Micrometer Prometheus registry:

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

Expose the Prometheus endpoint:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: prometheus
```

Now Prometheus can scrape metrics from `/actuator/prometheus` in the Prometheus text format.

### Grafana

With Prometheus as a data source, you can create dashboards in Grafana. There are many pre-built dashboards for Spring Boot applications that visualize JVM metrics, request rates, and error percentages.

## Production Best Practices

After implementing Actuator across multiple production systems, here are the practices I've found most valuable:

1. **Always secure endpoints** - Use Spring Security, management port, or network policies. Never expose sensitive endpoints to the internet.

2. **Use health groups** - Configure liveness and readiness probes for container orchestration platforms like Kubernetes.

3. **Set up alerts** - Monitor `health` status changes and key metrics like `jvm.memory.used` and `http.server.requests`. Use tools like Prometheus Alertmanager or cloud monitoring services.

4. **Log access** - Enable audit logging for Actuator endpoints to track who accessed what.

   ```yaml
   management:
     endpoints:
       web:
         exposure:
           include: "*"
     audit:
       events:
         enabled: true
   ```

5. **Limit exposure in production** - Only expose the endpoints you need. Start with `health`, `info`, `metrics`, and `prometheus`. Add others as required.

6. **Monitor custom business metrics** - Beyond system metrics, track domain-specific metrics like order rates, payment failures, or user registrations.

7. **Version your endpoints** - If you create custom endpoints, consider versioning them to avoid breaking changes.

## Troubleshooting Common Issues

### Endpoint Not Accessible

If you get a 404, check:
- The endpoint is exposed via `management.endpoints.web.exposure.include`
- The base path is correct (default `/actuator`)
- Security configuration isn't blocking it

### Health Status Always UP

If your custom health indicator isn't affecting the overall status, ensure it's properly registered as a Spring bean and implements `HealthIndicator`.

### Metrics Not Appearing

For custom metrics, verify:
- The `MeterRegistry` is injected correctly
- The metric name is unique
- The metric is being recorded (e.g., counter incremented)

## Key Takeaways

- **Spring Boot Actuator** provides production-ready monitoring with minimal configuration.
- **Health indicators** give deep insight into application and dependency health. Use custom indicators for external services.
- **Metrics** via Micrometer enable dimensional monitoring. Export to Prometheus and visualize in Grafana for powerful observability.
- **Security is paramount** — always secure Actuator endpoints using Spring Security, separate management ports, or network policies.
- **Custom endpoints** extend Actuator for domain-specific needs, but keep them focused and well-documented.
- **Health groups** simplify Kubernetes liveness and readiness probe configuration.
- **Production best practices** include limiting exposure, setting up alerts, and monitoring both system and business metrics.

By integrating Spring Boot Actuator into your deployment pipeline, you gain the visibility needed to operate confidently in production. Your application becomes not just a black box, but a transparent system that you can observe, diagnose, and optimize in real-time.