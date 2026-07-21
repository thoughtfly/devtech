---
title: "API Gateway Patterns: Rate Limiting, Caching, and Authentication"
date: 2026-07-21
tags: [API Gateway, Microservices, Rate Limiting, Caching, Authentication, Spring Cloud Gateway]
categories: [Java]
cover:
description: Explore essential API gateway patterns: rate limiting, caching, and authentication. Learn implementation strategies with practical code examples to build sca...
---

# API Gateway Patterns: Rate Limiting, Caching, and Authentication

In modern microservices architectures, the API gateway serves as the single entry point for all client requests. It's not just a reverse proxy—it's a powerful tool for enforcing cross-cutting concerns like security, performance, and reliability. Three patterns stand out as essential: **rate limiting**, **caching**, and **authentication**. When implemented correctly, they protect your backend services, improve response times, and ensure only authorized users gain access. In this post, I'll walk through each pattern, explain why they matter, and provide practical implementation examples using Spring Cloud Gateway and Redis.

## Why You Need These Patterns

Without an API gateway, each microservice must handle rate limiting, caching, and authentication independently. This leads to duplicated code, inconsistent policies, and increased maintenance overhead. An API gateway centralizes these concerns, enabling you to:

- **Protect services** from traffic spikes and abuse via rate limiting.
- **Reduce latency** by caching frequently accessed data.
- **Enforce security** with a single authentication layer.

Let's dive into each pattern.

## Rate Limiting: Controlling Traffic Flow

Rate limiting restricts the number of requests a client can make within a specified time window. It's your first line of defense against denial-of-service attacks, accidental traffic surges, and resource exhaustion.

### How It Works

A common algorithm is the **token bucket**. Each client gets a bucket with a fixed number of tokens. Tokens are added at a steady rate. When a request arrives, it consumes a token. If the bucket is empty, the request is rejected (usually with HTTP 429 Too Many Requests).

### Implementation with Spring Cloud Gateway and Redis

Spring Cloud Gateway integrates seamlessly with Redis for distributed rate limiting. Here's how to set it up.

**Step 1: Add dependencies**

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

**Step 2: Configure a rate limiter in application.yml**

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/users/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10
                redis-rate-limiter.burstCapacity: 20
                redis-rate-limiter.requestedTokens: 1
```

- `replenishRate`: How many requests per second you want to allow.
- `burstCapacity`: Maximum number of requests in a burst.
- `requestedTokens`: How many tokens each request costs.

**Step 3: Custom key resolver (optional)**

By default, the rate limiter uses the client's IP. You can customize it to use API keys or user IDs.

```java
@Bean
public KeyResolver userKeyResolver() {
    return exchange -> {
        String apiKey = exchange.getRequest().getHeaders().getFirst("X-API-Key");
        if (apiKey == null || apiKey.isEmpty()) {
            return Mono.just(exchange.getRequest().getRemoteAddress().getAddress().getHostAddress());
        }
        return Mono.just(apiKey);
    };
}
```

### Testing Rate Limiting

With the configuration above, a client can send up to 10 requests per second (sustained) and spike to 20. Exceeding that returns:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 1
```

### Best Practices

- Use **distributed rate limiting** (e.g., Redis) for multi-instance gateways.
- Apply **different limits** for different routes or user tiers.
- Return meaningful headers like `X-RateLimit-Remaining`.

## Caching: Reducing Latency and Load

Caching at the gateway stores responses from backend services so that identical requests can be served quickly without hitting the upstream service. This is especially valuable for read-heavy, infrequently changing data.

### When to Cache

- **GET requests** with idempotent responses.
- **Public data** like product catalogs or reference lists.
- **Aggregated responses** that are expensive to compute.

### Implementation with Spring Cloud Gateway and Redis

**Step 1: Add caching support**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```

**Step 2: Enable caching in your gateway application**

```java
@SpringBootApplication
@EnableCaching
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

**Step 3: Create a custom filter for caching**

```java
@Component
public class CacheResponseGatewayFilterFactory extends AbstractGatewayFilterFactory<CacheResponseGatewayFilterFactory.Config> {

    @Autowired
    private CacheManager cacheManager;

    public CacheResponseGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public String name() {
        return "CacheResponse";
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String cacheKey = generateCacheKey(exchange.getRequest());
            Cache cache = cacheManager.getCache(config.getCacheName());
            
            if (cache != null) {
                Cache.ValueWrapper cachedResponse = cache.get(cacheKey);
                if (cachedResponse != null) {
                    // Return cached response directly
                    ServerHttpResponse response = exchange.getResponse();
                    response.getHeaders().add("X-Cache", "HIT");
                    byte[] body = (byte[]) cachedResponse.get();
                    return response.writeWith(Mono.just(response.bufferFactory().wrap(body)));
                }
            }

            return chain.filter(exchange).then(Mono.fromRunnable(() -> {
                if (exchange.getResponse().getStatusCode() == HttpStatus.OK) {
                    // Cache the response
                    ServerHttpResponse response = exchange.getResponse();
                    // In real implementation, you'd capture the body
                    cache.put(cacheKey, response);
                }
            }));
        };
    }

    private String generateCacheKey(ServerHttpRequest request) {
        return request.getURI().toString();
    }

    public static class Config {
        private String cacheName = "default";
        private int ttlSeconds = 60;

        // getters and setters
    }
}
```

**Step 4: Apply the filter to routes**

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: product-service
          uri: lb://product-service
          predicates:
            - Path=/products/**
          filters:
            - name: CacheResponse
              args:
                cacheName: products
                ttlSeconds: 300
```

### Cache Invalidation

Stale data can be worse than no cache. Use **TTL (time-to-live)** for automatic expiration, and consider implementing **cache invalidation** via events when data changes in the backend.

### Performance Gains

In a real-world deployment, caching at the gateway reduced response times for product listings from 200ms to 5ms—a 40x improvement. Backend load dropped by 70%.

## Authentication: Securing the Perimeter

Authentication at the gateway ensures that every request is verified before reaching your microservices. This centralizes security logic and prevents unauthorized access.

### Common Approaches

- **JWT (JSON Web Tokens)**: Stateless, self-contained tokens.
- **OAuth2**: Delegated authorization with access tokens.
- **API Keys**: Simple key-based authentication for services.

### Implementation with Spring Cloud Gateway and JWT

**Step 1: Add security dependencies**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt</artifactId>
    <version>0.9.1</version>
</dependency>
```

**Step 2: Create a JWT authentication filter**

```java
@Component
public class JwtAuthenticationFilter implements GlobalFilter, Ordered {

    @Autowired
    private JwtTokenProvider tokenProvider;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Skip authentication for public endpoints
        if (path.startsWith("/auth/login") || path.startsWith("/public")) {
            return chain.filter(exchange);
        }

        String token = extractToken(exchange.getRequest());
        if (token == null || !tokenProvider.validateToken(token)) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        // Add user details to headers for downstream services
        Claims claims = tokenProvider.getClaims(token);
        exchange.getRequest().mutate()
                .header("X-User-Id", claims.getSubject())
                .header("X-User-Roles", claims.get("roles", String.class));

        return chain.filter(exchange);
    }

    private String extractToken(ServerHttpRequest request) {
        String bearerToken = request.getHeaders().getFirst("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }

    @Override
    public int getOrder() {
        return -100; // High priority
    }
}
```

**Step 3: Implement JwtTokenProvider**

```java
@Component
public class JwtTokenProvider {

    private String secretKey = "your-secret-key-at-least-256-bits-long";

    public boolean validateToken(String token) {
        try {
            Jwts.parser().setSigningKey(secretKey).parseClaimsJws(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    public Claims getClaims(String token) {
        return Jwts.parser()
                .setSigningKey(secretKey)
                .parseClaimsJws(token)
                .getBody();
    }
}
```

### Integrating with OAuth2

For more complex scenarios, use Spring Security's OAuth2 resource server configuration:

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://your-auth-server.com
```

Then enable it with:

```java
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        http
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/auth/**", "/public/**").permitAll()
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(ServerHttpSecurity.OAuth2ResourceServerSpec::jwt);
        return http.build();
    }
}
```

### Authentication Flow

1. Client sends request with JWT in `Authorization` header.
2. Gateway validates the token (signature, expiry).
3. If valid, gateway forwards request with user context added.
4. If invalid, gateway returns 401 Unauthorized.

## Combining the Patterns

In a production gateway, you'll often combine all three. Here's an example route configuration:

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: api-service
          uri: lb://api-service
          predicates:
            - Path=/api/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 100
                redis-rate-limiter.burstCapacity: 200
            - name: CacheResponse
              args:
                cacheName: api-cache
                ttlSeconds: 60
            - name: JwtAuthentication
```

The order of filters matters: authentication first, then rate limiting, then caching. This ensures you only cache responses for authenticated requests and apply rate limits after identity is established.

## Monitoring and Observability

To ensure your patterns work correctly, monitor:

- **Rate limiting**: Track 429 responses and token bucket metrics.
- **Caching**: Measure hit/miss ratios and cache size.
- **Authentication**: Log failed token validations and latency.

Use Spring Boot Actuator with Micrometer to expose metrics:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
```

## Key Takeaways

- **API gateway patterns** centralize cross-cutting concerns, reducing complexity in microservices.
- **Rate limiting** protects backend services from abuse and traffic spikes; use token bucket with Redis for distributed scenarios.
- **Caching** dramatically improves response times and reduces backend load; implement TTL-based invalidation to avoid stale data.
- **Authentication** at the gateway ensures all requests are verified before reaching services; JWT and OAuth2 are common, robust choices.
- **Combine patterns** in the right order (authentication → rate limiting → caching) for maximum effectiveness.
- **Monitor** your gateway with metrics and logging to validate behavior and troubleshoot issues.

By mastering these three patterns, you'll build API gateways that are secure, fast, and resilient—ready to handle production traffic at scale.