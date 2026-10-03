---
title: "Designing Rate Limiting Systems: Token Bucket vs Sliding Window"
date: 2026-10-03
tags: [rate-limiting, distributed-systems, java, redis, system-design, performance]
categories: [Java]
cover: "https://images.unsplash.com/photo-1711823660797-ef7d919228d1?w=1200&q=80&fit=crop&fm=webp"
description: Compare Token Bucket and Sliding Window algorithms for building robust rate limiters. Learn implementation strategies in Java with Redis and practical trade-...
---

## Introduction

Rate limiting is one of those infrastructure components that most teams only think about when things break. You might have a perfectly functional API during normal traffic, but the moment a scraper hits your endpoint or a marketing campaign goes viral, your system grinds to a halt. I’ve been there – waking up to PagerDuty alerts because a single client exhausted our database connection pool with a tight loop. That’s when you realize that rate limiting isn’t just a nice-to-have feature; it’s a critical component of system resilience.

In this post, we’ll dive deep into two of the most popular rate-limiting algorithms: Token Bucket and Sliding Window. We’ll explore how they work, their trade-offs, and how to implement them effectively in Java using Redis. Whether you’re building a small API gateway or a large-scale distributed system, understanding these algorithms will help you design rate limiters that are both fair and efficient.

## Why Rate Limiting Matters

Before we get into the algorithms, let’s briefly cover why rate limiting is essential. Rate limiting serves several critical purposes:

- **Protection against abuse**: Prevents malicious actors from overwhelming your system with requests
- **Fair resource allocation**: Ensures no single user can monopolize system resources
- **Cost management**: Controls infrastructure costs by limiting request volumes
- **System stability**: Prevents cascading failures by controlling traffic spikes
- **SLA enforcement**: Helps maintain service level agreements by managing load

Without proper rate limiting, your system becomes vulnerable to denial-of-service attacks, resource exhaustion, and degraded performance for all users.

## Token Bucket Algorithm

The Token Bucket algorithm is one of the most intuitive and widely-used rate-limiting approaches. Let me explain it using a real-world analogy.

Imagine you have a bucket that can hold a maximum number of tokens. Tokens are added to the bucket at a constant rate. Each request consumes one token from the bucket. If the bucket is empty, the request is rejected. This simple mechanism provides several benefits:

### How It Works

1. **Bucket capacity**: Defines the maximum burst size allowed
2. **Refill rate**: Controls how quickly tokens are added back
3. **Token consumption**: Each request removes one token
4. **Rejection policy**: Requests are denied when the bucket is empty

The beauty of Token Bucket is that it allows for controlled bursts of traffic while maintaining a long-term average rate. This is particularly useful for APIs where users might occasionally need to send multiple requests in quick succession.

### Java Implementation with Redis

Here’s how you can implement a Token Bucket rate limiter using Redis and Java:

```java
import io.lettuce.core.ScriptOutputType;
import io.lettuce.core.api.sync.RedisCommands;
import org.springframework.stereotype.Component;

@Component
public class TokenBucketRateLimiter {
    
    private final RedisCommands<String, String> redisCommands;
    
    // Lua script for atomic token bucket operations
    private static final String TOKEN_BUCKET_SCRIPT = 
        "local key = KEYS[1]\n" +
        "local capacity = tonumber(ARGV[1])\n" +
        "local refillRate = tonumber(ARGV[2])\n" +
        "local now = tonumber(ARGV[3])\n" +
        "local requested = tonumber(ARGV[4])\n" +
        "\n" +
        "local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')\n" +
        "local tokens = tonumber(bucket[1])\n" +
        "local last_refill = tonumber(bucket[2])\n" +
        "\n" +
        "if tokens == nil then\n" +
        "    tokens = capacity\n" +
        "    last_refill = now\n" +
        "end\n" +
        "\n" +
        "local elapsed = math.max(0, now - last_refill)\n" +
        "local newTokens = math.min(capacity, tokens + (elapsed * refillRate))\n" +
        "\n" +
        "if newTokens >= requested then\n" +
        "    newTokens = newTokens - requested\n" +
        "    redis.call('HMSET', key, 'tokens', newTokens, 'last_refill', now)\n" +
        "    redis.call('EXPIRE', key, 3600)\n" +
        "    return 1\n" +
        "else\n" +
        "    redis.call('HMSET', key, 'tokens', newTokens, 'last_refill', now)\n" +
        "    redis.call('EXPIRE', key, 3600)\n" +
        "    return 0\n" +
        "end";
    
    public boolean allowRequest(String clientId, int capacity, double refillRate) {
        String key = "rate_limit:token_bucket:" + clientId;
        long now = System.currentTimeMillis() / 1000;
        
        Long result = redisCommands.eval(
            TOKEN_BUCKET_SCRIPT,
            ScriptOutputType.INTEGER,
            new String[]{key},
            String.valueOf(capacity),
            String.valueOf(refillRate),
            String.valueOf(now),
            "1"
        );
        
        return result == 1;
    }
}
```

### Advantages of Token Bucket

- **Burst tolerance**: Allows short bursts of traffic up to the bucket capacity
- **Simple implementation**: Easy to understand and implement
- **Predictable behavior**: Clear relationship between rate and capacity
- **Memory efficient**: Only stores current token count and timestamp

### Disadvantages

- **Clock synchronization**: Requires consistent time across distributed systems
- **Potential for abuse**: Can be exploited by timing requests precisely
- **Complexity in distributed systems**: Needs careful coordination across nodes

## Sliding Window Algorithm

The Sliding Window algorithm takes a different approach to rate limiting. Instead of tracking tokens, it tracks the actual number of requests within a time window. There are two main variants: Sliding Window Log and Sliding Window Counter.

### Sliding Window Log

This approach maintains a log of all request timestamps within the current window. When a new request arrives, it checks how many requests occurred in the last N seconds.

```java
import io.lettuce.core.api.sync.RedisCommands;
import org.springframework.stereotype.Component;

@Component
public class SlidingWindowLogRateLimiter {
    
    private final RedisCommands<String, String> redisCommands;
    
    public boolean allowRequest(String clientId, int maxRequests, int windowSeconds) {
        String key = "rate_limit:sliding_window:" + clientId;
        long now = System.currentTimeMillis();
        long windowStart = now - (windowSeconds * 1000L);
        
        // Remove old entries outside the window
        redisCommands.zremrangeByScore(key, 0, windowStart);
        
        // Count requests in current window
        long count = redisCommands.zcard(key);
        
        if (count < maxRequests) {
            // Add current request
            String requestId = now + ":" + Math.random();
            redisCommands.zadd(key, now, requestId);
            redisCommands.expire(key, windowSeconds + 1);
            return true;
        }
        
        return false;
    }
}
```

### Sliding Window Counter

The Sliding Window Counter is more efficient for high-traffic scenarios. It divides the time window into smaller intervals and maintains counts for each interval.

```java
@Component
public class SlidingWindowCounterRateLimiter {
    
    private final RedisCommands<String, String> redisCommands;
    
    public boolean allowRequest(String clientId, int maxRequests, int windowSeconds, int intervalSeconds) {
        long now = System.currentTimeMillis() / 1000;
        int currentInterval = (int)(now / intervalSeconds);
        int previousInterval = currentInterval - 1;
        
        String currentKey = "rate_limit:sw_counter:" + clientId + ":" + currentInterval;
        String previousKey = "rate_limit:sw_counter:" + clientId + ":" + previousInterval;
        
        // Get counts from current and previous intervals
        long currentCount = Long.parseLong(redisCommands.get(currentKey) != null ? 
            redisCommands.get(currentKey) : "0");
        long previousCount = Long.parseLong(redisCommands.get(previousKey) != null ? 
            redisCommands.get(previousKey) : "0");
        
        // Calculate weighted count based on position in window
        int positionInInterval = (int)(now % intervalSeconds);
        double weight = 1.0 - (double)positionInInterval / intervalSeconds;
        long weightedCount = (long)(currentCount + (previousCount * weight));
        
        if (weightedCount < maxRequests) {
            // Increment current interval counter
            redisCommands.incr(currentKey);
            redisCommands.expire(currentKey, windowSeconds + intervalSeconds);
            return true;
        }
        
        return false;
    }
}
```

### Advantages of Sliding Window

- **Precise rate limiting**: More accurate than fixed window approaches
- **No burst issues**: Smooths out traffic more effectively
- **Better distribution**: Prevents concentrated bursts at window boundaries
- **Flexible intervals**: Can adjust window size based on requirements

### Disadvantages

- **Higher memory usage**: Especially with Sliding Window Log
- **Complexity**: More complex to implement correctly
- **Performance overhead**: Additional computations for weighted calculations

## Comparing Token Bucket and Sliding Window

Let’s compare these algorithms across several dimensions:

### 1. Traffic Pattern Handling

**Token Bucket** excels at allowing bursts while maintaining an average rate. If you have a capacity of 100 tokens and a refill rate of 10 tokens/second, a user can send 100 requests immediately, then 10 requests per second afterward. This is ideal for APIs where occasional bursts are acceptable.

**Sliding Window** provides smoother rate limiting. It prevents bursts by tracking actual request counts within a moving window. This is better for systems that need consistent, predictable load patterns.

### 2. Implementation Complexity

Token Bucket is generally simpler to implement, especially with Redis. The Lua script approach ensures atomicity and reduces race conditions. Sliding Window, particularly the counter variant, requires more complex calculations and additional storage for interval tracking.

### 3. Memory Efficiency

Token Bucket stores minimal state: just the current token count and last refill timestamp. Sliding Window Log can consume significant memory if you’re tracking many requests over long periods. Sliding Window Counter is more memory-efficient but still requires storing multiple interval counters.

### 4. Accuracy

Sliding Window provides more accurate rate limiting, especially at window boundaries. Token Bucket can have slight inaccuracies due to timing variations, but these are usually negligible for most use cases.

### 5. Distributed System Considerations

Both algorithms work well in distributed systems when implemented with Redis. However, Token Bucket’s simpler state management often makes it more suitable for large-scale distributed environments.

## Practical Implementation Strategies

### When to Use Token Bucket

- **API rate limiting**: When you want to allow occasional bursts
- **File upload services**: Where users might upload multiple files quickly
- **Payment processing**: To allow quick retries while maintaining overall limits
- **Simple use cases**: When you need a straightforward implementation

### When to Use Sliding Window

- **Strict rate enforcement**: When you need precise control over request rates
- **High-traffic systems**: Where memory efficiency is critical
- **Fair usage policies**: When you want to prevent any single user from dominating resources
- **Compliance requirements**: When you need to prove exact request counts

## Advanced Considerations

### Handling Clock Skew

In distributed systems, clock skew can cause issues with both algorithms. Here are some strategies:

1. **Use Redis server time**: Instead of client-side timestamps, use Redis’s `TIME` command
2. **Implement clock synchronization**: Use NTP or similar protocols
3. **Add tolerance**: Allow small time variations in your calculations

### Rate Limiting by Multiple Dimensions

Often, you need to rate limit by multiple criteria simultaneously. For example, you might want to limit by:
- User ID
- IP address
- API endpoint
- Geographic region

Here’s how you can combine multiple rate limiters:

```java
@Component
public class CompositeRateLimiter {
    
    private final TokenBucketRateLimiter tokenBucketLimiter;
    private final SlidingWindowCounterRateLimiter slidingWindowLimiter;
    
    public RateLimitResult checkRateLimit(String userId, String ip, String endpoint) {
        // Check user-level rate limit
        boolean userAllowed = tokenBucketLimiter.allowRequest(
            "user:" + userId, 100, 10.0);
        
        if (!userAllowed) {
            return RateLimitResult.denied("User rate limit exceeded");
        }
        
        // Check IP-level rate limit
        boolean ipAllowed = slidingWindowLimiter.allowRequest(
            "ip:" + ip, 50, 60, 10);
        
        if (!ipAllowed) {
            return RateLimitResult.denied("IP rate limit exceeded");
        }
        
        // Check endpoint-specific rate limit
        boolean endpointAllowed = tokenBucketLimiter.allowRequest(
            "endpoint:" + endpoint, 200, 20.0);
        
        if (!endpointAllowed) {
            return RateLimitResult.denied("Endpoint rate limit exceeded");
        }
        
        return RateLimitResult.allowed();
    }
}
```

### Monitoring and Alerting

Effective rate limiting requires monitoring. Key metrics to track:

- **Request acceptance rate**: Percentage of requests allowed vs rejected
- **Rate limit violations**: Number and type of rate limit hits
- **Client distribution**: Which clients are hitting limits most often
- **System performance**: Impact of rate limiting on response times

```yaml
# Example Prometheus metrics configuration
metrics:
  rate_limiting:
    enabled: true
    metrics:
      - name: rate_limit_requests_total
        type: counter
        labels:
          - client_id
          - endpoint
          - result  # allowed, denied
      - name: rate_limit_active_clients
        type: gauge
      - name: rate_limit_rejection_rate
        type: histogram
        buckets: [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
```

## Common Pitfalls and Solutions

### 1. Race Conditions

**Problem**: Multiple requests arriving simultaneously can cause race conditions.

**Solution**: Use atomic operations with Redis Lua scripts or Redis transactions.

### 2. Memory Leaks

**Problem**: Sliding Window Log can accumulate old entries indefinitely.

**Solution**: Always set appropriate TTLs and periodically clean up old entries.

### 3. Inconsistent State

**Problem**: Different nodes might have inconsistent rate limit state.

**Solution**: Use a centralized Redis cluster and ensure all nodes read/write to the same keys.

### 4. Performance Degradation

**Problem**: Complex rate limiting logic can slow down request processing.

**Solution**: Implement caching, use efficient data structures, and consider async processing for non-critical checks.

## Testing Your Rate Limiter

Testing rate limiters is crucial but often overlooked. Here’s a comprehensive testing strategy:

```java
@SpringBootTest
class RateLimiterTest {
    
    @Autowired
    private TokenBucketRateLimiter rateLimiter;
    
    @Test
    void testBasicRateLimiting() {
        // Test that requests are allowed within limit
        for (int i = 0; i < 100; i++) {
            assertTrue(rateLimiter.allowRequest("test-client", 100, 10.0));
        }
        
        // Test that requests are denied after limit
        assertFalse(rateLimiter.allowRequest("test-client", 100, 10.0));
    }
    
    @Test
    void testConcurrentRequests() throws InterruptedException {
        List<Future<Boolean>> futures = new ArrayList<>();
        ExecutorService executor = Executors.newFixedThreadPool(10);
        
        // Submit 150 concurrent requests with limit of 100
        for (int i = 0; i < 150; i++) {
            futures.add(executor.submit(() -> 
                rateLimiter.allowRequest("concurrent-client", 100, 10.0)
            ));
        }
        
        long allowedCount = futures.stream()
            .filter(f -> {
                try { return f.get(); }
                catch (Exception e) { return false; }
            })
            .count();
        
        assertEquals(100, allowedCount);
        executor.shutdown();
    }
    
    @Test
    void testRefillOverTime() throws InterruptedException {
        // Exhaust all tokens
        for (int i = 0; i < 100; i++) {
            rateLimiter.allowRequest("refill-client", 100, 10.0);
        }
        
        assertFalse(rateLimiter.allowRequest("refill-client", 100, 10.0));
        
        // Wait for refill
        Thread.sleep(1000);
        
        // Should have refilled ~10 tokens
        assertTrue(rateLimiter.allowRequest("refill-client", 100, 10.0));
    }
}
```

## Key Takeaways

- **Token Bucket** is ideal for scenarios requiring burst tolerance and simple implementation
- **Sliding Window** provides more precise rate limiting but requires more complex implementation
- **Redis** is the recommended backend for distributed rate limiting due to its atomic operations and persistence
- **Lua scripts** ensure atomicity and prevent race conditions in rate limiter implementations
- **Composite rate limiters** allow you to enforce limits across multiple dimensions (user, IP, endpoint)
- **Monitoring** is essential for effective rate limit management and troubleshooting
- **Testing** should cover concurrent access, refill behavior, and edge cases
- **Memory management** is critical, especially for Sliding Window Log implementations
- **Clock synchronization** becomes increasingly important in distributed systems
- **Performance optimization** should consider both the rate limiting logic and the underlying infrastructure

Choosing between Token Bucket and Sliding Window depends on your specific requirements. If you need simplicity and burst tolerance, go with Token Bucket. If you require precise rate control and can handle the additional complexity, Sliding Window is the better choice. In many cases, implementing both and allowing configuration based on the use case provides the most flexibility.

Remember that rate limiting is not a one-size-fits-all solution. Consider your traffic patterns, business requirements, and system constraints when designing your rate limiter. Start simple, monitor your metrics, and iterate based on real-world usage patterns.