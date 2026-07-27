---
title: "Backend System Design Interview: Design a URL Shortener"
date: 2026-07-27
tags: [system design, URL shortener, backend, interview preparation, distributed systems]
categories: [Java]
cover:
description: Master the URL shortener system design interview with this comprehensive guide covering requirements, architecture, database schema, and scaling strategies.
---

# Backend System Design Interview: Design a URL Shortener

If you've ever prepared for a senior backend engineering interview, you've likely encountered the "Design a URL Shortener" problem. It's a classic system design question—deceptively simple on the surface, but rich with complexity when you dig deeper. In this post, I'll walk you through a complete approach to designing a URL shortener like TinyURL or bit.ly, covering everything from requirements gathering to scaling considerations.

## Why This Problem Matters

URL shorteners are ubiquitous. They power link sharing on Twitter, SMS marketing, and analytics tracking. But beneath the simple act of shortening a URL lies a fascinating set of engineering challenges:

- **High write throughput**: Millions of new URLs created daily
- **Extremely high read throughput**: Billions of redirects per day
- **Low latency requirements**: Every redirect should happen in under 100ms
- **Data integrity**: No two long URLs should map to different short URLs (unless designed for analytics)
- **Scalability**: The system must handle spikes (e.g., Super Bowl ads)

## Step 1: Requirements Gathering

Before writing a single line of code, clarify the requirements with your interviewer. This demonstrates your ability to think critically about trade-offs.

### Functional Requirements

- **Shorten**: Given a long URL, generate a unique, short alias
- **Redirect**: Given a short URL, redirect the user to the original long URL
- **Custom aliases**: (Optional) Allow users to specify their own short path
- **TTL/Expiration**: (Optional) URLs can expire after a certain time
- **Analytics**: (Optional) Track click counts, referrers, geolocation

### Non-Functional Requirements

- **High availability**: The system should never go down
- **Low latency**: Redirects in < 100ms
- **Scalability**: Handle billions of requests per month
- **Durability**: Once a short URL is created, it should never be lost

### Out of Scope (for this interview)

- User authentication
- Spam detection
- Advanced analytics dashboards

## Step 2: Traffic and Storage Estimation

Always estimate scale. This shows you understand real-world constraints.

**Assumptions:**
- 100 million new URLs per month
- 10 billion redirects per month
- Average URL length: 100 characters
- Short URL length: 6 characters (alphanumeric: 62^6 ≈ 56 billion combinations)

**Storage Calculation:**
- Each mapping: 100 bytes (long URL) + 6 bytes (short key) + 8 bytes (creation timestamp) + overhead ≈ 200 bytes
- Monthly: 100 million × 200 bytes = 20 GB
- 5 years: 20 GB × 12 × 5 = 1.2 TB

**Bandwidth:**
- Writes: 100 million / (30 × 24 × 3600) ≈ 38 writes/second
- Reads: 10 billion / (30 × 24 × 3600) ≈ 3,800 reads/second
- Peak: Assume 10× spike → 38,000 reads/second

## Step 3: API Design

Let's design a clean REST API.

### Create Short URL

```
POST /api/shorten
Request Body:
{
  "longUrl": "https://example.com/very/long/url/that/needs/shortening",
  "customAlias": "my-custom-alias", // optional
  "ttl": 86400 // optional, in seconds
}

Response:
{
  "shortUrl": "https://short.ly/abc123",
  "longUrl": "https://example.com/very/long/url/that/needs/shortening",
  "createdAt": "2024-01-15T10:30:00Z",
  "ttl": 86400
}
```

### Redirect

```
GET /{shortKey}
Response: 301 Redirect to longUrl
```

**Why 301 vs 302?**
- 301 (Moved Permanently): Browser caches the redirect, reducing load on servers
- 302 (Found): For analytics, use 302 to track each click

## Step 4: Database Schema

We need a simple but efficient schema.

```sql
CREATE TABLE url_mappings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    short_key VARCHAR(10) NOT NULL UNIQUE,
    long_url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_short_key (short_key)
);
```

**Database Choice:**
- **SQL** (PostgreSQL/MySQL): For strong consistency and transactions
- **NoSQL** (Cassandra/DynamoDB): For extreme scalability, but eventual consistency might cause issues

**Trade-off**: I'd recommend SQL for the primary store because we need strong consistency for short key uniqueness. Use NoSQL for caching or analytics.

## Step 5: Short Key Generation

This is the most interesting algorithmic challenge. We need to generate unique, short, and random-looking keys.

### Approach 1: Hash + Base62 Encoding

```java
import java.security.MessageDigest;
import java.math.BigInteger;

public class ShortKeyGenerator {
    private static final String BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    
    public static String generate(String longUrl) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(longUrl.getBytes());
            BigInteger number = new BigInteger(1, digest);
            StringBuilder sb = new StringBuilder();
            
            for (int i = 0; i < 6; i++) {
                sb.append(BASE62.charAt(number.mod(BigInteger.valueOf(62)).intValue()));
                number = number.divide(BigInteger.valueOf(62));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate short key", e);
        }
    }
}
```

**Pros:** Deterministic, no DB lookup needed
**Cons:** Collisions possible, need to handle with retry or append salt

### Approach 2: Distributed Unique ID + Base62

Use a distributed ID generator (like Snowflake) and encode it in Base62.

```java
public class SnowflakeIdGenerator {
    private final long datacenterId;
    private final long machineId;
    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public SnowflakeIdGenerator(long datacenterId, long machineId) {
        this.datacenterId = datacenterId;
        this.machineId = machineId;
    }

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();
        if (timestamp < lastTimestamp) {
            throw new RuntimeException("Clock moved backwards");
        }
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 4095;
            if (sequence == 0) {
                timestamp = waitNextMillis(timestamp);
            }
        } else {
            sequence = 0;
        }
        lastTimestamp = timestamp;
        return ((timestamp - 1609459200000L) << 22)
                | (datacenterId << 17)
                | (machineId << 12)
                | sequence;
    }

    private long waitNextMillis(long currentTimestamp) {
        while (currentTimestamp <= lastTimestamp) {
            currentTimestamp = System.currentTimeMillis();
        }
        return currentTimestamp;
    }
}
```

**Pros:** No collisions, fast, scalable
**Cons:** Need coordination for machine IDs

## Step 6: System Architecture

Let's put it all together with a high-level design.

```
[Client] → [Load Balancer] → [Web Servers] → [Cache (Redis)] → [Database (PostgreSQL)]
                                     ↓
                               [Key Generation Service]
```

### Components

1. **Load Balancer**: Distributes traffic across web servers (NGINX, HAProxy)
2. **Web Servers**: Stateless application servers (Spring Boot, Node.js)
3. **Cache**: Redis cluster for hot URLs (LRU eviction)
4. **Database**: PostgreSQL with replication for durability
5. **Key Generation Service**: Generates unique short keys

### Data Flow

**Creating a short URL:**
1. Client sends POST request with long URL
2. Web server calls Key Generation Service
3. Web server inserts mapping into DB
4. Web server caches mapping in Redis
5. Returns short URL to client

**Redirect flow:**
1. Client sends GET request with short key
2. Web server checks Redis cache
3. If miss, query DB
4. Cache the result in Redis (with TTL)
5. Return 301 redirect to long URL

## Step 7: Caching Strategy

Caching is critical for read-heavy workloads.

```yaml
# Redis Configuration
redis:
  cluster:
    nodes: 6
    replication-factor: 2
  eviction-policy: allkeys-lru
  ttl: 3600 # 1 hour for cached mappings
```

**Cache-Aside Pattern:**
```java
public String getLongUrl(String shortKey) {
    // Check cache first
    String longUrl = redis.get(shortKey);
    if (longUrl != null) {
        return longUrl;
    }
    
    // Cache miss - query database
    longUrl = database.findLongUrlByShortKey(shortKey);
    
    // Populate cache (only if found)
    if (longUrl != null) {
        redis.setex(shortKey, 3600, longUrl);
    }
    
    return longUrl;
}
```

**Cache Hit Ratio:** With proper sizing, expect 95%+ hit rate for popular URLs.

## Step 8: Handling Edge Cases

### Collision Handling

```java
public String createShortUrl(String longUrl, String customAlias) {
    String shortKey = (customAlias != null) ? customAlias : generateShortKey(longUrl);
    
    int retries = 3;
    while (retries > 0) {
        try {
            // Use database unique constraint to detect collision
            database.insert(new UrlMapping(shortKey, longUrl));
            return shortKey;
        } catch (DuplicateKeyException e) {
            if (customAlias != null) {
                throw new IllegalArgumentException("Custom alias already exists");
            }
            // Generate a new key and retry
            shortKey = generateShortKey(longUrl + System.nanoTime());
            retries--;
        }
    }
    throw new RuntimeException("Failed to generate unique short key after retries");
}
```

### Expiration

Implement a background job to clean expired URLs:

```java
@Component
public class ExpirationCleanupJob {
    @Scheduled(fixedRate = 3600000) // Every hour
    public void cleanupExpiredUrls() {
        List<UrlMapping> expired = database.findExpiredUrls();
        expired.forEach(mapping -> {
            redis.del(mapping.getShortKey());
            database.delete(mapping);
        });
    }
}
```

## Step 9: Scaling Considerations

### Database Scaling

- **Read replicas**: Offload read traffic to replicas
- **Sharding**: Partition by short key hash (consistent hashing)
- **Connection pooling**: Use HikariCP for efficient connections

```yaml
# Sharding configuration
database:
  shards:
    - range: 0-999
      host: shard1.example.com
    - range: 1000-1999
      host: shard2.example.com
    - range: 2000-2999
      host: shard3.example.com
```

### Rate Limiting

Protect against abuse:

```java
public class RateLimiter {
    private final Redis redis;
    private final int maxRequestsPerSecond = 100;
    
    public boolean allowRequest(String clientIp) {
        String key = "ratelimit:" + clientIp;
        Long current = redis.incr(key);
        if (current == 1) {
            redis.expire(key, 1); // Expire after 1 second
        }
        return current <= maxRequestsPerSecond;
    }
}
```

### Monitoring

Essential metrics to track:
- QPS (reads and writes)
- Cache hit ratio
- Database query latency (p99)
- Error rates (collision, timeout)
- Expired URL count

## Step 10: Alternative Designs and Trade-offs

### Design A: Single Database + Cache
**Pros:** Simple, consistent
**Cons:** Database becomes bottleneck at scale

### Design B: Distributed Key-Value Store
**Pros:** Highly scalable, low latency
**Cons:** Eventual consistency, complex operations

### Design C: Pre-generated Keys Pool
**Pros:** Fast key generation, no collisions
**Cons:** Wasteful if keys not used, need to manage pool size

**My recommendation:** Start with Design A for MVP, evolve to Design B as traffic grows.

## Key Takeaways

- **Start with requirements**: Always clarify functional and non-functional requirements before diving into design.
- **Estimate scale**: Calculate storage, bandwidth, and QPS to guide architecture decisions.
- **Key generation is critical**: Choose between hash-based (simple) or distributed ID (scalable) approaches.
- **Cache aggressively**: With a 95%+ read-to-write ratio, caching is your best performance lever.
- **Plan for collisions**: Implement retry logic and unique constraints to handle edge cases.
- **Think about expiration**: Background jobs for cleanup are essential for long-term maintenance.
- **Rate limiting is non-negotiable**: Protect your system from abuse and DDoS attacks.
- **Monitor everything**: Without observability, you're flying blind in production.

Remember: In a system design interview, the goal isn't to produce a perfect design—it's to demonstrate your thought process, trade-off analysis, and ability to communicate complex ideas clearly. Practice this problem with different variations, and you'll be well-prepared for the real thing.