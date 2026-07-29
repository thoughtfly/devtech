---
title: "Distributed Caching with Redis: Patterns and Anti-Patterns"
date: 2026-07-29
tags: [Redis, Distributed Caching, Java, Performance, System Design]
categories: [Java]
cover:
description: Master distributed caching with Redis: explore proven patterns like cache-aside and read-through, and avoid common anti-patterns that kill performance and re...
---

# Distributed Caching with Redis: Patterns and Anti-Patterns

When your application starts serving millions of requests per day, the database becomes the bottleneck. You add indexes, optimize queries, and eventually reach the physical limits of your hardware. That's when you turn to caching. Redis, with its sub-millisecond latency and rich data structures, has become the de facto standard for distributed caching. But with great power comes great responsibility—misuse Redis and you'll trade one set of problems for another.

I've spent the last decade building and scaling Java applications in production. I've seen Redis save systems from collapse, and I've seen it bring them down. In this post, I'll walk through the most effective caching patterns, the anti-patterns that will haunt you at 3 AM, and practical code examples you can use today.

## Why Redis for Distributed Caching?

Before diving into patterns, let's understand why Redis excels at caching:

- **In-memory storage**: Data resides in RAM, providing microsecond response times.
- **Rich data structures**: Strings, hashes, lists, sets, sorted sets—choose the right tool for your data.
- **Built-in expiration**: TTL (Time-To-Live) automatically evicts stale data.
- **Atomic operations**: INCR, SETNX, and Lua scripting enable safe concurrent access.
- **Persistence options**: RDB snapshots and AOF logs for durability when needed.
- **Cluster mode**: Horizontal scaling with automatic sharding and replication.

## Core Caching Patterns

### 1. Cache-Aside (Lazy Loading)

This is the most common pattern. The application code is responsible for both reading from and writing to the cache.

**How it works:**
1. Check cache for data.
2. If found (cache hit), return it.
3. If not found (cache miss), load from database.
4. Store the data in cache with a TTL.
5. Return the data.

```java
public class UserService {
    private final RedisTemplate<String, User> redisTemplate;
    private final UserRepository userRepository;
    
    public User getUserById(String userId) {
        String cacheKey = "user:" + userId;
        
        // Step 1: Check cache
        User cachedUser = redisTemplate.opsForValue().get(cacheKey);
        if (cachedUser != null) {
            return cachedUser;
        }
        
        // Step 2: Load from database
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));
        
        // Step 3: Store in cache with 1-hour TTL
        redisTemplate.opsForValue().set(cacheKey, user, 1, TimeUnit.HOURS);
        
        return user;
    }
}
```

**Pros:**
- Simple to implement.
- Only caches data that is actually requested.
- Resilient—if cache fails, the system falls back to the database.

**Cons:**
- Three network round trips on a cache miss (cache → miss → DB → cache).
- Stale data until TTL expiration.
- Cache stampede risk on popular keys.

### 2. Read-Through Cache

The cache itself handles loading data from the database. The application treats the cache as the primary data source.

```java
@Component
public class UserCacheLoader implements CacheLoader<String, User> {
    private final UserRepository userRepository;
    
    @Override
    public User load(String key) {
        // Extract userId from cache key "user:123"
        String userId = key.replace("user:", "");
        return userRepository.findById(userId)
            .orElseThrow(() -> new CacheLoadingException("User not found: " + userId));
    }
}

// Usage with Spring Cache abstraction
@Cacheable(value = "users", key = "#userId")
public User getUserById(String userId) {
    // This method is only called on cache miss
    return userRepository.findById(userId).orElse(null);
}
```

**Pros:**
- Simplifies application code.
- Consistent cache loading logic.

**Cons:**
- Cache layer must be highly available.
- Harder to debug cache misses.

### 3. Write-Through Cache

Data is written to the cache first, then synchronously to the database. Every write goes through the cache.

```java
public void updateUser(User user) {
    String cacheKey = "user:" + user.getId();
    
    // Write to cache first
    redisTemplate.opsForValue().set(cacheKey, user, 1, TimeUnit.HOURS);
    
    // Then write to database
    userRepository.save(user);
}
```

**Pros:**
- Cache is always consistent with the database.
- No stale data issues.

**Cons:**
- Increased write latency.
- Writes to cache even for data that may never be read.
- Cache failure can block writes.

### 4. Write-Behind Cache

Data is written to cache and asynchronously persisted to the database. This is also called write-back caching.

```java
public void updateUser(User user) {
    String cacheKey = "user:" + user.getId();
    
    // Write to cache immediately
    redisTemplate.opsForValue().set(cacheKey, user, 1, TimeUnit.HOURS);
    
    // Queue database write for async processing
    writeBehindQueue.enqueue(() -> userRepository.save(user));
}
```

**Pros:**
- Very low write latency.
- Can batch database writes for efficiency.

**Cons:**
- Data loss risk if cache fails before persistence.
- Eventual consistency—database may lag behind cache.

## Anti-Patterns to Avoid

### 1. No Expiration Policy

```java
// DANGER: No TTL set
redisTemplate.opsForValue().set("user:123", user);
```

Without TTL, your cache grows unbounded. Redis will eventually run out of memory, triggering eviction. The default `noeviction` policy returns errors on writes. Other policies like `allkeys-lru` evict random keys, potentially removing hot data.

**Fix:** Always set TTL based on data volatility. Use `maxmemory-policy allkeys-lru` for general-purpose caching.

### 2. Caching Everything

Some teams cache entire database tables without considering access patterns.

```java
// Anti-pattern: Caching all users on startup
for (User user : userRepository.findAll()) {
    redisTemplate.opsForValue().set("user:" + user.getId(), user);
}
```

This wastes memory on data that may never be accessed. It also adds startup time and network overhead.

**Fix:** Cache on demand (cache-aside) or use a read-through pattern.

### 3. Cache Stampede (Thundering Herd)

When a popular cache key expires, multiple concurrent requests all miss the cache and hit the database simultaneously.

```java
// Anti-pattern: No protection against stampede
public Product getProduct(String id) {
    Product cached = redisTemplate.opsForValue().get("product:" + id);
    if (cached == null) {
        // Multiple threads can reach here concurrently
        Product product = database.findProduct(id);
        redisTemplate.opsForValue().set("product:" + id, product);
        return product;
    }
    return cached;
}
```

**Fix:** Use Redis SETNX for distributed locking, or use probabilistic expiration.

```java
public Product getProduct(String id) {
    Product cached = redisTemplate.opsForValue().get("product:" + id);
    if (cached != null) {
        return cached;
    }
    
    // Distributed lock to prevent stampede
    String lockKey = "lock:product:" + id;
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "locked", 10, TimeUnit.SECONDS);
    
    if (Boolean.TRUE.equals(acquired)) {
        try {
            // Double-check after acquiring lock
            Product cachedAgain = redisTemplate.opsForValue().get("product:" + id);
            if (cachedAgain != null) {
                return cachedAgain;
            }
            
            Product product = database.findProduct(id);
            redisTemplate.opsForValue().set("product:" + id, product, 1, TimeUnit.HOURS);
            return product;
        } finally {
            redisTemplate.delete(lockKey);
        }
    } else {
        // Wait for the first request to complete
        Thread.sleep(100);
        return getProduct(id); // Retry
    }
}
```

### 4. Hot Keys

A single key receives a disproportionate amount of traffic, overloading the Redis node that holds it.

**Example:** A trending product that gets 100,000 requests per second.

**Fix:** Shard hot keys by adding a random suffix.

```java
public String buildHotKey(String baseKey) {
    int shardCount = 100;
    int shard = ThreadLocalRandom.current().nextInt(shardCount);
    return baseKey + ":" + shard;
}
```

### 5. Using Redis as a Primary Database

Redis is an in-memory cache, not a database. Data loss can occur even with persistence enabled.

**Anti-pattern example:** Storing critical business transactions only in Redis.

**Fix:** Always persist important data to a durable database (PostgreSQL, MySQL, etc.). Use Redis for caching and transient state.

### 6. Ignoring Serialization Overhead

Java serialization is slow and produces large payloads. Using default JVM serialization with Redis can cause high CPU and memory usage.

```java
// Anti-pattern: Default Java serialization
RedisTemplate<String, Object> template = new RedisTemplate<>();
template.setDefaultSerializer(new JdkSerializationRedisSerializer());
```

**Fix:** Use efficient serialization like Protocol Buffers, Kryo, or JSON with compression.

```java
// Better: JSON serialization
RedisTemplate<String, User> template = new RedisTemplate<>();
template.setValueSerializer(new Jackson2JsonRedisSerializer<>(User.class));
```

## Advanced Patterns

### 1. Cache Warming

Pre-populate the cache with frequently accessed data during application startup or off-peak hours.

```java
@PostConstruct
public void warmCache() {
    List<String> popularUserIds = analyticsService.getTopUsers(1000);
    popularUserIds.parallelStream().forEach(userId -> {
        String cacheKey = "user:" + userId;
        if (Boolean.FALSE.equals(redisTemplate.hasKey(cacheKey))) {
            User user = userRepository.findById(userId).orElse(null);
            if (user != null) {
                redisTemplate.opsForValue().set(cacheKey, user, 1, TimeUnit.HOURS);
            }
        }
    });
}
```

### 2. Two-Level Caching

Combine local (in-process) cache with Redis for optimal performance.

```java
public class TwoLevelCache {
    private final Cache<String, User> localCache = Caffeine.newBuilder()
        .maximumSize(10000)
        .expireAfterWrite(5, TimeUnit.MINUTES)
        .build();
    
    private final RedisTemplate<String, User> redisTemplate;
    
    public User getUser(String userId) {
        // Level 1: Local cache
        User user = localCache.getIfPresent(userId);
        if (user != null) {
            return user;
        }
        
        // Level 2: Redis
        String cacheKey = "user:" + userId;
        user = redisTemplate.opsForValue().get(cacheKey);
        if (user != null) {
            localCache.put(userId, user);
            return user;
        }
        
        // Level 3: Database
        user = userRepository.findById(userId).orElse(null);
        if (user != null) {
            redisTemplate.opsForValue().set(cacheKey, user, 1, TimeUnit.HOURS);
            localCache.put(userId, user);
        }
        return user;
    }
}
```

### 3. Cache Invalidation with Pub/Sub

When data changes, use Redis Pub/Sub to notify all application instances to invalidate their local caches.

```java
// Publisher: On data update
public void updateUser(User user) {
    userRepository.save(user);
    redisTemplate.convertAndSend("cache:invalidate:user", user.getId());
}

// Subscriber: In all application instances
@RedisListener(channel = "cache:invalidate:user")
public void handleUserInvalidation(String userId) {
    localCache.invalidate(userId);
    redisTemplate.delete("user:" + userId);
}
```

## Operational Best Practices

### Monitoring Redis

- **Hit rate**: Track cache hits vs misses. Low hit rate indicates ineffective caching.
- **Memory usage**: Set `maxmemory` and monitor eviction rates.
- **Latency**: Use `redis-cli --latency` and `SLOWLOG` to identify slow commands.
- **Keyspace hits/misses**: `INFO stats` provides these metrics.

### Connection Management

Use connection pooling with sensible limits:

```yaml
spring:
  redis:
    host: localhost
    port: 6379
    lettuce:
      pool:
        max-active: 16
        max-idle: 8
        min-idle: 4
```

### Security

- Always use Redis passwords (`requirepass`).
- Run Redis in a trusted network, never expose to the internet.
- Use TLS for encryption in transit.
- Rename dangerous commands (FLUSHALL, CONFIG) or disable them.

## Key Takeaways

1. **Choose the right pattern**: Cache-aside for simplicity, read-through for consistency, write-behind for performance.
2. **Always set TTL**: Never cache data indefinitely. Match TTL to your data's volatility.
3. **Prevent cache stampede**: Use distributed locks or probabilistic expiration for hot keys.
4. **Avoid hot keys**: Shard frequently accessed keys across multiple cache entries.
5. **Don't treat Redis as a database**: It's a cache with best-effort persistence. Critical data belongs in a durable store.
6. **Serialize efficiently**: Use JSON, Protocol Buffers, or Kryo—never default Java serialization.
7. **Monitor aggressively**: Track hit rates, memory usage, and latency to catch problems early.
8. **Cache selectively**: Only cache data that is expensive to compute and frequently accessed.
9. **Use two-level caching**: Combine local and distributed caches for optimal performance.
10. **Invalidate proactively**: Use Pub/Sub or write-through patterns to keep caches fresh.

Distributed caching with Redis can transform your application's performance, but it requires careful design. Start simple, monitor everything, and evolve your patterns as you learn your traffic patterns. Your database will thank you.