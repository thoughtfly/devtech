---
title: "Designing Resilient Systems: Circuit Breaker and Retry Patterns"
date: 2026-07-20
tags: [Resilience4j, Circuit Breaker, Retry Pattern, Microservices, Resilience Patterns]
categories: [Java]
cover:
description: Learn how to build fault-tolerant microservices with Circuit Breaker and Retry patterns. Practical Java examples using Resilience4j, best practices, and real...
---

# Designing Resilient Systems: Circuit Breaker and Retry Patterns

In a distributed system, failures are not a matter of *if* but *when*. Network partitions, slow downstream services, database timeouts, and transient errors are the daily reality of microservices. Without deliberate design, a single failing dependency can cascade into a system-wide outage. This is where resilience patterns come in.

Two of the most fundamental patterns for building fault-tolerant systems are the **Circuit Breaker** and the **Retry** pattern. While they are often used together, they solve different problems and must be configured carefully to avoid making things worse.

In this post, I'll share practical experience implementing these patterns in Java using Resilience4j, discuss real-world pitfalls, and provide code examples you can adapt today.

## Why Resilience Matters

Imagine your e-commerce application calls a payment gateway. That gateway might be temporarily slow due to high load. If your service keeps waiting for a response, threads pile up, memory fills, and your entire application becomes unresponsive. This is the **cascading failure** problem.

Resilience patterns aim to:
- **Isolate** failures to prevent them from spreading.
- **Recover** quickly from transient issues.
- **Degrade gracefully** when a dependency is unavailable.

Let's dive into the two most effective patterns.

## The Retry Pattern

The Retry pattern is straightforward: when a call to a remote service fails with a transient error (like a network timeout or a 503 Service Unavailable), automatically retry the operation after a short delay.

### When to Retry

Not all failures are retryable. You should retry only when:
- The error is transient (e.g., timeout, temporary database deadlock).
- The operation is **idempotent** (repeating it has the same effect as doing it once).
- Retrying does not violate business constraints (e.g., a payment charge should not be retried blindly).

### Basic Retry with Resilience4j

Resilience4j is a lightweight, easy-to-use library for Java applications. Here's a basic retry configuration:

```yaml
resilience4j.retry:
  configs:
    default:
      maxAttempts: 3
      waitDuration: 500ms
      retryExceptions:
        - org.springframework.dao.DataAccessException
        - java.net.SocketTimeoutException
      ignoreExceptions:
        - com.example.BusinessException
```

And in code:

```java
Retry retry = Retry.of("paymentService", retryConfig);

Supplier<String> supplier = () -> paymentService.charge(order);

Supplier<String> decorated = Retry.decorateSupplier(retry, supplier);

Try<String> result = Try.ofSupplier(decorated);
result.onSuccess(System.out::println)
      .onFailure(e -> log.error("Payment failed after retries", e));
```

### Exponential Backoff and Jitter

Using a fixed wait duration can cause a **thundering herd** problem: if many clients retry at the same interval, they all hit the recovering service simultaneously. Exponential backoff with jitter spreads out retries.

```yaml
resilience4j.retry:
  configs:
    default:
      maxAttempts: 5
      waitDuration: 1s
      exponentialBackoffMultiplier: 2
      enableExponentialBackoff: true
      enableRandomizedWait: true
      randomizedWaitFactor: 0.5
```

This means the first retry waits 1s, second 2s, third 4s, and so on, with up to 50% randomness.

### Common Pitfall: Retry Storm

A retry storm happens when a service is already struggling, and retries from multiple clients overwhelm it further. Always combine retries with a circuit breaker (next) and limit the max retry count to a small number (3–5).

## The Circuit Breaker Pattern

The Circuit Breaker pattern prevents your application from repeatedly trying an operation that is likely to fail. It monitors for failures and once a threshold is reached, it **opens** the circuit and subsequent calls fail immediately without hitting the downstream service.

### States of a Circuit Breaker

- **CLOSED**: Normal operation. Requests pass through.
- **OPEN**: Failures exceed threshold. Requests fail fast.
- **HALF_OPEN**: After a timeout, a limited number of test requests are allowed to check if the service has recovered.

### Circuit Breaker with Resilience4j

Configuration example:

```yaml
resilience4j.circuitbreaker:
  configs:
    default:
      slidingWindowSize: 10
      minimumNumberOfCalls: 5
      failureRateThreshold: 50
      waitDurationInOpenState: 10s
      permittedNumberOfCallsInHalfOpenState: 3
      recordExceptions:
        - java.net.ConnectException
        - java.util.concurrent.TimeoutException
```

- `slidingWindowSize`: Number of calls to analyze.
- `failureRateThreshold`: Percentage of failures that triggers open state.
- `waitDurationInOpenState`: How long the circuit stays open before half-open.
- `permittedNumberOfCallsInHalfOpenState`: How many test calls are allowed.

In Java:

```java
CircuitBreaker circuitBreaker = CircuitBreaker.of("paymentService", circuitBreakerConfig);

Supplier<String> decorated = CircuitBreaker.decorateSupplier(circuitBreaker, 
    () -> paymentService.charge(order));

Try<String> result = Try.ofSupplier(decorated);
result.onSuccess(System.out::println)
      .onFailure(e -> log.warn("Circuit breaker open, fallback used", e));
```

### Fallback Methods

When the circuit is open, you should provide a fallback:

```java
Supplier<String> decorated = CircuitBreaker.decorateSupplier(circuitBreaker, 
    () -> paymentService.charge(order));

Supplier<String> withFallback = Fallback.decorate(decorated, 
    e -> fallbackPayment(order));
```

Fallbacks can return cached data, a default response, or redirect to an alternative service.

## Combining Retry and Circuit Breaker

This is where many developers make mistakes. If you apply retry *inside* the circuit breaker, each retry counts as a separate call, potentially opening the circuit faster than intended. The correct order is:

1. **Circuit Breaker** wraps the outer call.
2. **Retry** wraps the inner call.

```java
// Correct: Retry inside Circuit Breaker
Supplier<String> decorated = CircuitBreaker.decorateSupplier(circuitBreaker, 
    Retry.decorateSupplier(retry, () -> paymentService.charge(order)));
```

This way, if the circuit is open, the retry never executes. And if the circuit is closed but the call fails, the retry will attempt again, but each attempt is tracked by the circuit breaker.

### Visual Flow

```
Request -> CircuitBreaker (CLOSED?) -> Retry (up to 3 attempts) -> Service
                                     |
                                     +-> If all retries fail -> CircuitBreaker records failure
```

## Real-World Example: Payment Service

Let's build a complete example using Spring Boot and Resilience4j.

### Dependencies

```xml
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot2</artifactId>
    <version>2.0.2</version>
</dependency>
```

### Application.yml

```yaml
resilience4j.retry:
  instances:
    paymentRetry:
      maxAttempts: 3
      waitDuration: 500ms
      exponentialBackoffMultiplier: 2
      retryExceptions:
        - java.net.SocketTimeoutException
        - org.springframework.web.client.HttpServerErrorException

resilience4j.circuitbreaker:
  instances:
    paymentCircuitBreaker:
      registerHealthIndicator: true
      slidingWindowSize: 10
      minimumNumberOfCalls: 5
      failureRateThreshold: 50
      waitDurationInOpenState: 10s
      permittedNumberOfCallsInHalfOpenState: 3
      recordExceptions:
        - java.net.ConnectException
        - java.util.concurrent.TimeoutException
```

### Service Layer

```java
@Service
public class PaymentService {
    
    @CircuitBreaker(name = "paymentCircuitBreaker", fallbackMethod = "fallbackCharge")
    @Retry(name = "paymentRetry")
    public PaymentResponse charge(PaymentRequest request) {
        // call external payment gateway
        return restTemplate.postForObject("https://payment-gateway/charge", 
            request, PaymentResponse.class);
    }

    public PaymentResponse fallbackCharge(PaymentRequest request, Throwable t) {
        log.warn("Payment circuit breaker open, using fallback");
        return new PaymentResponse("FAILED", "Service unavailable, retry later");
    }
}
```

### Monitoring with Actuator

Resilience4j exposes metrics via Spring Boot Actuator:

```bash
# Check circuit breaker state
GET /actuator/health

# Get metrics
GET /actuator/metrics/resilience4j.circuitbreaker.state
```

## Best Practices

### 1. Set Realistic Timeouts

Circuit breakers work best when combined with timeouts. A call that hangs for 30 seconds is worse than a fast failure.

```yaml
resilience4j.timelimiter:
  instances:
    paymentService:
      timeoutDuration: 2s
```

### 2. Use Separate Configurations per Dependency

Don't use a single circuit breaker for all external calls. Each dependency (database, payment service, email service) should have its own configuration based on its typical latency and failure patterns.

### 3. Monitor and Tune

Start with conservative values (e.g., 5 calls, 50% failure rate, 10s open window). Monitor real traffic and adjust. If the circuit opens too often, increase the threshold. If it rarely opens, decrease it.

### 4. Test Failure Scenarios

Use tools like Chaos Monkey or Toxiproxy to simulate network failures, latency spikes, and service crashes. Verify that your circuit breakers and retries behave as expected.

## Common Mistakes

- **Retry on non-idempotent operations**: If the downstream processed the request but the response timed out, retrying might duplicate the action (e.g., charging a credit card twice). Use idempotency keys or deduplication.
- **Infinite retries**: Always set a max retry count. Infinite retries can cause resource exhaustion.
- **No fallback**: An open circuit breaker that throws an exception is better than a hanging request, but a fallback that returns cached data is even better.
- **Retry storm**: Multiple services retrying simultaneously can DDoS your own infrastructure.

## Advanced: Bulkhead Pattern

For even better resilience, combine circuit breakers with the **Bulkhead** pattern, which limits the number of concurrent calls to a service. Resilience4j supports both thread-pool and semaphore-based bulkheads.

```yaml
resilience4j.bulkhead:
  instances:
    paymentBulkhead:
      maxConcurrentCalls: 10
      maxWaitDuration: 500ms
```

## Conclusion

Resilience patterns are not optional in distributed systems. The Retry pattern handles transient failures, while the Circuit Breaker prevents cascading failures and gives services time to recover. When combined correctly—retry inside circuit breaker—they form a powerful defense against the chaos of production.

Start small. Add circuit breakers to your most critical external dependencies. Monitor the results. Then layer on retries with exponential backoff. Your future self (and your users) will thank you.

## Key Takeaways

- **Retry** handles transient failures; **Circuit Breaker** prevents repeated failures from overwhelming a service.
- Always place **Retry inside Circuit Breaker** to avoid unnecessary retries when the circuit is open.
- Use **exponential backoff with jitter** to avoid thundering herd problems.
- Provide **fallback methods** for circuit breaker open states.
- **Monitor and tune** circuit breaker thresholds based on real traffic patterns.
- Combine with **timeouts and bulkheads** for comprehensive resilience.
- Test failure scenarios proactively with chaos engineering tools.