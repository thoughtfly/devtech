---
title: "How to Build a Multi-Model AI Gateway with Spring Cloud Gateway"
date: 2026-07-07
tags: [Spring Cloud Gateway, AI Gateway, LLM Routing, Java, Microservices]
categories: [Java]
cover:
description: Learn to build a scalable multi-model AI gateway using Spring Cloud Gateway to route, throttle, and secure requests to multiple LLM providers (OpenAI, Anthro...
---

# How to Build a Multi-Model AI Gateway with Spring Cloud Gateway

Imagine your application needs to talk to multiple large language models (LLMs) — OpenAI’s GPT-4 for creative writing, Anthropic’s Claude for safety-critical analysis, and a local Llama 2 for cost-sensitive tasks. Managing these connections directly in your business logic leads to tight coupling, duplicated authentication logic, and a maintenance nightmare. Enter the **AI Gateway**: a single entry point that routes, throttles, and secures all AI API calls.

In this guide, I’ll show you how to build a production-ready multi-model AI gateway using **Spring Cloud Gateway**. You’ll learn to:

- Route requests to different LLM providers based on headers or query parameters
- Implement rate limiting per model and per user
- Add a unified authentication layer
- Handle streaming responses seamlessly
- Monitor and log all AI interactions

By the end, you’ll have a reusable gateway that any team in your organization can use to access AI models safely and consistently.

## Why a Dedicated AI Gateway?

Before diving into code, let’s clarify the problem. Without a gateway, each microservice needs to:

- Manage API keys for every LLM provider
- Handle rate limits, retries, and fallbacks
- Implement consistent logging and monitoring
- Deal with different response formats (OpenAI uses SSE, Anthropic uses JSON, etc.)

A gateway centralizes these concerns. It becomes the single point of contact for all AI traffic, enforcing company policies and simplifying client code.

## Architecture Overview

Our gateway will sit between client applications and multiple LLM backends. Here’s the high-level flow:

```
Client App -> Spring Cloud Gateway -> Route Predicate -> Filter Chain -> LLM Provider
```

Key components:

- **Route Configuration**: YAML-based routes that map request paths to target LLM URLs
- **Custom Filters**: Authentication, rate limiting, header transformation, response adaptation
- **Service Discovery**: Optional, but useful if you have multiple instances of local models
- **Circuit Breaker**: Using Spring Cloud Circuit Breaker with Resilience4j for fallback handling

## Setting Up the Project

Let’s bootstrap a Spring Boot project with Spring Cloud Gateway. I’ll use Maven, but Gradle works similarly.

### pom.xml Dependencies

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>

<properties>
    <spring-cloud.version>2023.0.0</spring-cloud.version>
</properties>

<dependencies>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-gateway</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

## Configuring Routes for Multiple LLMs

Spring Cloud Gateway allows you to define routes in `application.yml`. Each route maps a path pattern to a target URI and can apply filters.

### Basic Route Configuration

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: openai-route
          uri: https://api.openai.com
          predicates:
            - Path=/api/v1/ai/openai/**
          filters:
            - StripPrefix=3
            - AddRequestHeader=X-Custom-Header, my-gateway

        - id: anthropic-route
          uri: https://api.anthropic.com
          predicates:
            - Path=/api/v1/ai/anthropic/**
          filters:
            - StripPrefix=3

        - id: local-model-route
          uri: http://localhost:11434
          predicates:
            - Path=/api/v1/ai/local/**
          filters:
            - StripPrefix=3
```

Here, the client sends requests to `/api/v1/ai/openai/v1/chat/completions`, and the gateway strips the first three path segments (`/api/v1/ai/openai`) before forwarding to `https://api.openai.com/v1/chat/completions`.

### Dynamic Routing via Headers

Sometimes you want the client to specify the model via a header. We can use a custom predicate factory.

```java
@Component
public class ModelRoutePredicateFactory extends AbstractRoutePredicateFactory<ModelRoutePredicateFactory.Config> {

    public ModelRoutePredicateFactory() {
        super(Config.class);
    }

    @Override
    public Predicate<ServerWebExchange> apply(Config config) {
        return exchange -> {
            String modelHeader = exchange.getRequest().getHeaders().getFirst("X-Model-Provider");
            return config.getProvider().equalsIgnoreCase(modelHeader);
        };
    }

    @Data
    public static class Config {
        private String provider;
    }
}
```

Then use it in your routes:

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: dynamic-openai
          uri: https://api.openai.com
          predicates:
            - ModelRoute=openai
            - Path=/api/v1/ai/chat
          filters:
            - StripPrefix=2
```

Now clients just send `X-Model-Provider: openai` to `/api/v1/ai/chat`, and the gateway routes accordingly.

## Adding Authentication and API Key Management

Security is critical. We need to validate that the client has permission to use specific models and manage API keys for backend providers.

### Custom Global Filter for API Key Validation

```java
@Component
public class ApiKeyAuthFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String apiKey = exchange.getRequest().getHeaders().getFirst("X-API-Key");
        if (apiKey == null || !isValidApiKey(apiKey)) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
        // Add the backend API key to the request headers
        String backendKey = getBackendApiKey(exchange.getRequest().getURI().getPath());
        exchange.getRequest().mutate()
                .header("Authorization", "Bearer " + backendKey);
        return chain.filter(exchange);
    }

    private boolean isValidApiKey(String apiKey) {
        // Check against your database or Redis cache
        return true; // Simplified
    }

    private String getBackendApiKey(String path) {
        // Map path to provider-specific key from vault or config
        return "sk-...";
    }

    @Override
    public int getOrder() {
        return -1; // High precedence
    }
}
```

**Pro tip**: Never store API keys in code. Use Spring Cloud Config with Vault or Kubernetes Secrets.

## Rate Limiting per Model and User

Without rate limiting, a single user could exhaust your OpenAI quota. Spring Cloud Gateway integrates with Redis for distributed rate limiting.

### Request Rate Limiter Configuration

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: openai-route
          uri: https://api.openai.com
          predicates:
            - Path=/api/v1/ai/openai/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
                redis-rate-limiter.requestedTokens: 1
                key-resolver: "#{@userKeyResolver}"
```

### Custom Key Resolver

```java
@Component
public class UserKeyResolver implements KeyResolver {

    @Override
    public Mono<String> resolve(ServerWebExchange exchange) {
        String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
        String model = exchange.getRequest().getHeaders().getFirst("X-Model-Provider");
        return Mono.just(userId + ":" + model);
    }
}
```

This ensures each user has a separate rate limit bucket per model.

## Handling Streaming Responses

LLMs often stream responses using Server-Sent Events (SSE) or chunked transfer encoding. Spring Cloud Gateway can handle this natively if we configure the filter chain correctly.

### Preserving Streaming

By default, Gateway buffers responses. For streaming, we need to disable buffering:

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: openai-stream
          uri: https://api.openai.com
          predicates:
            - Path=/api/v1/ai/openai/v1/chat/completions
            - Header=Accept, text/event-stream
          filters:
            - DedupeResponseHeader=Access-Control-Allow-Origin
            - name: Retry
              args:
                retries: 3
                statuses: BAD_GATEWAY
```

Also, ensure your custom filters do not buffer the response. Use `ServerWebExchange` mutators carefully.

## Adding Circuit Breaker for Fallback

When an upstream LLM is down, we want to fail gracefully. Spring Cloud Circuit Breaker with Resilience4j provides this.

### Circuit Breaker Filter

```java
@Component
public class AiCircuitBreakerFilter implements GlobalFilter, Ordered {

    private final CircuitBreaker circuitBreaker;

    public AiCircuitBreakerFilter(CircuitBreakerFactory factory) {
        this.circuitBreaker = factory.create("ai-gateway");
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        return circuitBreaker.run(
            chain.filter(exchange),
            throwable -> fallbackResponse(exchange, throwable)
        );
    }

    private Mono<Void> fallbackResponse(ServerWebExchange exchange, Throwable t) {
        exchange.getResponse().setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);
        byte[] bytes = "{\"error\":\"AI service temporarily unavailable\"}".getBytes();
        DataBuffer buffer = exchange.getResponse().bufferFactory().wrap(bytes);
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return 0;
    }
}
```

## Logging and Monitoring

Every AI call should be logged for audit and debugging. We can use a custom filter to capture request and response metadata.

### Audit Logging Filter

```java
@Component
public class AuditLogFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(AuditLogFilter.class);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long start = System.currentTimeMillis();
        return chain.filter(exchange).then(Mono.fromRunnable(() -> {
            long duration = System.currentTimeMillis() - start;
            log.info("AI Call: user={}, model={}, path={}, status={}, duration={}ms",
                exchange.getRequest().getHeaders().getFirst("X-User-Id"),
                exchange.getRequest().getHeaders().getFirst("X-Model-Provider"),
                exchange.getRequest().getURI().getPath(),
                exchange.getResponse().getStatusCode(),
                duration);
        }));
    }

    @Override
    public int getOrder() {
        return 1;
    }
}
```

For production, send these logs to a centralized system like ELK or Datadog.

## Full Application.yml Example

Here’s a complete configuration that ties everything together:

```yaml
server:
  port: 8080

spring:
  application:
    name: ai-gateway
  redis:
    host: localhost
    port: 6379
  cloud:
    gateway:
      routes:
        - id: openai-route
          uri: https://api.openai.com
          predicates:
            - Path=/api/v1/ai/openai/**
          filters:
            - StripPrefix=3
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
                key-resolver: "#{@userKeyResolver}"

        - id: anthropic-route
          uri: https://api.anthropic.com
          predicates:
            - Path=/api/v1/ai/anthropic/**
          filters:
            - StripPrefix=3

        - id: local-model
          uri: http://localhost:11434
          predicates:
            - Path=/api/v1/ai/local/**
          filters:
            - StripPrefix=3

      default-filters:
        - name: Retry
          args:
            retries: 2
            statuses: BAD_GATEWAY, SERVICE_UNAVAILABLE
        - name: CircuitBreaker
          args:
            name: aiCircuitBreaker
            fallbackUri: forward:/fallback

management:
  endpoints:
    web:
      exposure:
        include: health,info,gateway
```

## Testing the Gateway

Start your gateway and test with curl:

```bash
# Route to OpenAI
curl -X POST http://localhost:8080/api/v1/ai/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-gateway-key" \
  -H "X-User-Id: user123" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# Route to local model
curl -X POST http://localhost:8080/api/v1/ai/local/api/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-gateway-key" \
  -H "X-User-Id: user456" \
  -d '{"model": "llama2", "prompt": "Hello"}'
```

Check the logs to see audit entries and rate limit headers in the response.

## Going Further: Production Considerations

1. **Security**: Use mTLS between gateway and local models. Rotate API keys frequently.
2. **Caching**: Cache common prompts/responses in Redis to reduce costs.
3. **Load Testing**: Use Gatling to simulate traffic and tune rate limits.
4. **Multi-Region**: Deploy the gateway in multiple regions with a global load balancer.
5. **Cost Tracking**: Add a filter that tallies token usage per user/model and sends to a billing system.

## Key Takeaways

- Spring Cloud Gateway provides a flexible, reactive foundation for building an AI gateway that routes to multiple LLM providers.
- Use custom predicates and filters to handle authentication, rate limiting, streaming, and circuit breaking without coupling client code to backend specifics.
- Redis-backed rate limiting ensures fair usage across users and models in a distributed environment.
- Audit logging and circuit breakers are essential for production readiness, providing visibility and resilience.
- The gateway pattern centralizes AI API management, enabling teams to innovate faster while maintaining security and cost control.

Start building your AI gateway today — your future self (and your ops team) will thank you.

---

*Have you built an AI gateway? What challenges did you face? Share your experience in the comments below.*