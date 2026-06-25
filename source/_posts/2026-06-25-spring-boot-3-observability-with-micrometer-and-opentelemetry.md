---
title: "Spring Boot 3 Observability with Micrometer and OpenTelemetry"
date: 2026-06-25
tags: [Spring Boot 3, Micrometer, OpenTelemetry, Observability, Distributed Tracing, Metrics]
categories: [Java]
cover:
description: Spring Boot 3 Observability with Micrometer and OpenTelemetry
---

---
title: "Spring Boot 3 Observability with Micrometer and OpenTelemetry"
date: 2025-04-10
tags: ["Spring Boot 3", "Micrometer", "OpenTelemetry", "Observability", "Distributed Tracing", "Metrics"]
categories: ["Java"]
---

# Spring Boot 3 Observability with Micrometer and OpenTelemetry

If you've ever tried to debug a production issue in a distributed system without proper observability, you know the pain. Logs alone tell you *what* happened, but not *why* or *where* the latency came from. With Spring Boot 3, observability is no longer an afterthought—it's a first-class citizen. The combination of Micrometer and OpenTelemetry provides a powerful, vendor-neutral way to capture metrics, traces, and logs in a unified manner.

In this post, I'll walk you through setting up observability in a Spring Boot 3 application using Micrometer for metrics and OpenTelemetry for distributed tracing. We'll cover practical configurations, code examples, and how to export data to popular backends like Prometheus, Jaeger, and Grafana.

## Why Spring Boot 3 Changes the Game

Spring Boot 3 introduced a new observability API built on top of Micrometer's Observation API. This API unifies metrics and tracing under a single abstraction. Before Spring Boot 3, you had to manually instrument your code with separate libraries for metrics (Micrometer) and tracing (Spring Cloud Sleuth + OpenTelemetry). Now, you write one observation and get both metrics and traces automatically.

Key benefits:
- **Unified API**: One annotation or programmatic API for metrics and traces
- **Vendor-neutral**: Switch backends (Prometheus, Datadog, Jaeger, Zipkin) without code changes
- **Automatic instrumentation**: Spring Boot auto-configures many common components (HTTP, JDBC, Redis, Kafka)
- **Context propagation**: Trace context flows seamlessly across threads and services

## Setting Up a Spring Boot 3 Project

Let's start from scratch. Create a new Spring Boot 3 project with the necessary dependencies. I'll use Maven, but Gradle works similarly.

### pom.xml dependencies

```xml
<dependencies>
    <!-- Core Spring Boot -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- Micrometer + OpenTelemetry -->
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-tracing-bridge-otel</artifactId>
    </dependency>
    
    <!-- OpenTelemetry exporter (e.g., Jaeger) -->
    <dependency>
        <groupId>io.opentelemetry</groupId>
        <artifactId>opentelemetry-exporter-otlp</artifactId>
    </dependency>
    
    <!-- Micrometer registry for metrics (e.g., Prometheus) -->
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-registry-prometheus</artifactId>
    </dependency>
    
    <!-- Actuator for health and metrics endpoints -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### Key dependencies explained

- `micrometer-tracing-bridge-otel`: Bridges Micrometer's tracing API to OpenTelemetry
- `opentelemetry-exporter-otlp`: Exports traces via OTLP (OpenTelemetry Protocol) to any OTLP-compatible backend
- `micrometer-registry-prometheus`: Exposes metrics in Prometheus format at `/actuator/prometheus`
- `spring-boot-starter-actuator`: Provides health, info, metrics, and tracing endpoints

## Configuration

### application.yml

```yaml
spring:
  application:
    name: order-service

management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics,otlp
  tracing:
    sampling:
      probability: 1.0  # 100% sampling for development; reduce in production
  metrics:
    tags:
      application: ${spring.application.name}

otel:
  service:
    name: ${spring.application.name}
  exporter:
    otlp:
      endpoint: http://localhost:4317  # OTLP gRPC endpoint (Jaeger, Grafana Tempo, etc.)
      protocol: grpc
```

**Important notes:**
- Set `spring.tracing.sampling.probability` to a lower value (e.g., 0.1) in production to control costs
- The OTLP endpoint can point to Jaeger, Grafana Tempo, or any OpenTelemetry Collector
- Metrics tags help filter and group data in Prometheus

## Automatic Instrumentation: What You Get for Free

Spring Boot 3 automatically instruments many components. Without writing a single line of code, you get:

- **HTTP requests**: Incoming and outgoing requests are traced with span context
- **JDBC queries**: Each SQL statement is captured as a span (if using Spring Data JPA or JDBC)
- **Redis operations**: Lettuce or Jedis operations are traced
- **Kafka messaging**: Producer and consumer traces are propagated
- **Reactive streams**: Reactor operators preserve trace context

Let's test this with a simple REST controller.

### Sample Controller

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{id}")
    public Order getOrder(@PathVariable Long id) {
        log.info("Fetching order with id: {}", id);
        return orderService.findById(id);
    }
}
```

```java
@Service
public class OrderService {

    private final JdbcTemplate jdbcTemplate;

    public OrderService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Order findById(Long id) {
        String sql = "SELECT id, customer, total FROM orders WHERE id = ?";
        return jdbcTemplate.queryForObject(sql, new BeanPropertyRowMapper<>(Order.class), id);
    }
}
```

With the default configuration, every HTTP request to `/api/orders/{id}` generates:
- A **trace** with spans for the HTTP request, controller method, and JDBC query
- **Metrics** like `http.server.requests` with tags for status, method, and URI

You can view the trace in Jaeger (or your backend) and see the exact SQL statement executed.

## Custom Instrumentation with @Observed

Sometimes you need to instrument custom business logic. Spring Boot 3 provides the `@Observed` annotation for this purpose.

### Using @Observed

```java
import io.micrometer.observation.annotation.Observed;

@Service
public class PaymentService {

    @Observed(name = "payment.process", 
              contextualName = "process-payment",
              lowCardinalityKeyValues = {"paymentType", "credit-card"})
    public PaymentResult processPayment(PaymentRequest request) {
        // Simulate payment processing
        log.info("Processing payment for order {}", request.getOrderId());
        
        // This creates a span named "payment.process" with a tag paymentType=credit-card
        // It also records metrics: payment.process.seconds (histogram)
        
        return new PaymentResult(true, "Payment approved");
    }
}
```

**What @Observed does:**
1. Creates a new span in the current trace
2. Records timing metrics (duration histogram)
3. Automatically captures exceptions as error tags
4. Propagates the trace context to downstream calls

### Programmatic Observation

If annotations aren't flexible enough, use the `ObservationRegistry` directly.

```java
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;

@Service
public class InventoryService {

    private final ObservationRegistry observationRegistry;

    public InventoryService(ObservationRegistry observationRegistry) {
        this.observationRegistry = observationRegistry;
    }

    public boolean checkStock(Long productId) {
        return Observation.createNotStarted("inventory.check", observationRegistry)
            .lowCardinalityKeyValue("productId", String.valueOf(productId))
            .observe(() -> {
                // Actual business logic
                log.info("Checking stock for product {}", productId);
                return stockRepository.hasStock(productId);
            });
    }
}
```

## Adding Custom Metrics

While the Observation API handles common cases, you may need custom metrics like gauges or counters.

### Counter Example

```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Counter;

@Component
public class OrderMetrics {

    private final Counter orderCreatedCounter;
    private final Counter orderCancelledCounter;

    public OrderMetrics(MeterRegistry meterRegistry) {
        this.orderCreatedCounter = Counter.builder("orders.created")
            .description("Number of orders created")
            .tag("application", "order-service")
            .register(meterRegistry);
        
        this.orderCancelledCounter = Counter.builder("orders.cancelled")
            .description("Number of orders cancelled")
            .tag("application", "order-service")
            .register(meterRegistry);
    }

    public void incrementCreated() {
        orderCreatedCounter.increment();
    }

    public void incrementCancelled() {
        orderCancelledCounter.increment();
    }
}
```

### Timer Example

```java
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.MeterRegistry;

@Component
public class PaymentMetrics {

    private final Timer paymentTimer;

    public PaymentMetrics(MeterRegistry meterRegistry) {
        this.paymentTimer = Timer.builder("payment.duration")
            .description("Time taken to process a payment")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(meterRegistry);
    }

    public void recordPayment(Runnable paymentLogic) {
        paymentTimer.record(paymentLogic);
    }
}
```

## Integrating with Grafana, Prometheus, and Jaeger

Let's set up a complete observability stack using Docker Compose.

### docker-compose.yml

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

### prometheus.yml

```yaml
scrape_configs:
  - job_name: 'spring-boot-app'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['host.docker.internal:8080']
```

## Advanced: Context Propagation Across Threads

One common challenge is preserving trace context when using async operations. Spring Boot 3 handles this with `ThreadPoolTaskExecutor` auto-configuration.

### Async Example

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(10);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("async-");
        executor.initialize();
        return executor;
    }
}
```

```java
@Service
public class NotificationService {

    @Async
    @Observed(name = "notification.send")
    public CompletableFuture<Void> sendEmail(Long orderId) {
        // This runs in a separate thread but preserves the trace context
        log.info("Sending email for order {}", orderId);
        return CompletableFuture.completedFuture(null);
    }
}
```

No extra configuration needed—Spring Boot 3 automatically wraps the executor with trace context propagation.

## Best Practices from Production

After running this setup in production for several months, here are some lessons learned:

### 1. Sampling Strategy

Don't sample 100% in production unless you have unlimited storage. Use a probabilistic sampler with a rate that balances cost and visibility. For critical services, consider a rate-limiting sampler that captures all traces for high-latency requests.

```yaml
management:
  tracing:
    sampling:
      probability: 0.1
```

### 2. Tag Cardinality

Avoid high-cardinality tags (e.g., user IDs, session IDs) in metrics. They explode the number of time series in Prometheus. Use them only in traces, not metrics.

### 3. Custom Spans for External Calls

If your service calls external APIs not instrumented by Spring Boot, wrap them with `@Observed` or programmatic observations.

```java
@Observed(name = "external.api.call", 
          contextualName = "call-payment-gateway")
public PaymentResponse callPaymentGateway(PaymentRequest request) {
    // HTTP call to external service
}
```

### 4. Use OpenTelemetry Collector

Instead of exporting directly to Jaeger or Prometheus, use the OpenTelemetry Collector as a middleware. It provides buffering, retries, and can fan-out to multiple backends.

### 5. Log Correlation

Spring Boot 3 automatically adds trace IDs and span IDs to MDC (Mapped Diagnostic Context). Configure your logging pattern to include them.

```yaml
logging:
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - [%X{traceId:-},%X{spanId:-}] %msg%n"
```

This allows you to correlate logs with traces in Grafana or Kibana.

## Troubleshooting Common Issues

### Traces not appearing?

1. Check that the OTLP exporter is correctly configured
2. Verify the backend (Jaeger, Tempo) is running and accessible
3. Look for errors in logs like `Failed to export spans`
4. Ensure `spring-boot-starter-actuator` is on the classpath

### Metrics not showing in Prometheus?

1. Hit `/actuator/prometheus` endpoint to verify metrics are exposed
2. Check Prometheus target status in the UI
3. Ensure `micrometer-registry-prometheus` is on the classpath

### High memory usage?

Reduce sampling probability or increase the export interval. Also, consider using the OpenTelemetry Collector with batching.

## Key Takeaways

- **Spring Boot 3 unifies metrics and tracing** through the Micrometer Observation API, reducing boilerplate and cognitive load
- **Automatic instrumentation** covers HTTP, JDBC, Redis, Kafka, and more—zero code needed for basic observability
- **Use @Observed** for custom business logic to get both spans and metrics with a single annotation
- **Export traces via OTLP** to Jaeger, Grafana Tempo, or any OpenTelemetry-compatible backend
- **Export metrics via Prometheus** and visualize in Grafana for powerful dashboards
- **Always sample strategically** in production—100% sampling is rarely necessary
- **Correlate logs with traces** using MDC to speed up debugging
- **Invest in the OpenTelemetry Collector** for production deployments to handle backpressure and multi-backend export

Observability in Spring Boot 3 is no longer a headache. With Micrometer and OpenTelemetry, you get a robust, vendor-neutral foundation that grows with your system. Start instrumenting today—your future self (and on-call team) will thank you.