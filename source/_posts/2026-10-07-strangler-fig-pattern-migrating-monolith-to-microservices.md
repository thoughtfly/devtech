---
title: "Strangler Fig Pattern: Migrating Monolith to Microservices"
date: 2026-10-07
tags: [microservices, monolith, strangler fig, java, architecture, migration]
categories: [Java, Architecture]
cover: "https://images.unsplash.com/photo-1679403766682-3b31efa571a8?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to incrementally migrate a monolithic Java application to microservices using the Strangler Fig pattern with practical examples and best practices.
---

## The Monolith Trap: Why We Need a Better Way

We’ve all been there. You join a company with a "simple" codebase. Six months later, you realize that simple codebase has 400,000 lines of Java, 15,000 unit tests (most of which are integration tests), and a deployment process that requires a three-day window every quarter. The business wants new features yesterday, but every change risks breaking something in the inventory module. This is the monolith trap.

Many engineers and architects face this dilemma: the monolith is stable enough, but it’s too slow to innovate. The temptation is to rewrite everything from scratch—a big bang migration. But history shows us that big bang migrations fail at an alarming rate. According to various industry studies, over 60% of large-scale rewrites encounter significant delays, budget overruns, or complete failure.

Enter the Strangler Fig Pattern. Named after the tropical tree that grows around a host tree, slowly strangling it until it can survive on its own, this pattern offers a pragmatic, incremental approach to decomposing monolithic applications. Instead of tearing down the old system and building a new one, you gradually replace specific functionalities with new microservices while the monolith continues to serve traffic.

In this post, I’ll walk you through implementing the Strangler Fig pattern in a Java-based enterprise application, covering the architectural setup, routing strategies, data migration, and common pitfalls to avoid.

## Understanding the Strangler Fig Architecture

The core concept behind the Strangler Fig pattern is progressive replacement. You identify a bounded context within your monolith—perhaps a user service, an order processing module, or a notification system—and extract it into a standalone microservice. Once that service is stable and handling traffic, you move to the next context.

### The Router: Your Traffic Controller

The critical component in any Strangler Fig implementation is the router or facade. This sits between your clients (web browsers, mobile apps, other services) and your backend systems. The router decides whether a request should go to the monolith or the new microservice.

```java
public class RequestRouter {
    
    private final Map<String, ServiceEndpoint> routingTable;
    private final MonolithGateway monolithGateway;
    
    public Response route(Request request) {
        String endpoint = request.getPath();
        
        if (routingTable.containsKey(endpoint)) {
            ServiceEndpoint target = routingTable.get(endpoint);
            if (target.isMigrated()) {
                return target.getMicroservice().handle(request);
            }
        }
        
        // Fallback to monolith
        return monolithGateway.forward(request);
    }
}
```

The routing table is dynamic. As you migrate functionality, you update the table to point specific endpoints to their new homes. This allows you to migrate one piece at a time without disrupting existing users.

## Step-by-Step Implementation Guide

### Step 1: Assess Your Monolith

Before you begin, you need a clear map of your monolith. Document all the bounded contexts, their dependencies, and data flows. Use tools like ArchUnit or manual code analysis to identify coupling points. Look for:

- Clear module boundaries (e.g., order processing, user management, payment)
- External service dependencies
- Database tables that belong to specific domains
- API endpoints that can be isolated

### Step 2: Set Up the Routing Infrastructure

You’ll need a reverse proxy or API gateway to handle the routing. Common choices include NGINX, Kong, AWS API Gateway, or Spring Cloud Gateway. Here’s a basic NGINX configuration example:

```nginx
upstream monolith {
    server monolith:8080;
}

upstream user-service {
    server user-service:8081;
}

server {
    listen 80;
    
    # Route user-related requests to the new microservice
    location /api/users {
        proxy_pass http://user-service;
    }
    
    # Everything else goes to the monolith
    location /api {
        proxy_pass http://monolith;
    }
}
```

### Step 3: Extract the First Microservice

Start with a low-risk, high-value module. Perhaps a read-only service like product catalog or user profiles. Create a new Spring Boot application with its own database schema.

```java
@SpringBootApplication
@RestController
public class UserServiceApplication {
    
    @Autowired
    private UserRepository userRepository;
    
    @GetMapping("/api/users/{id}")
    public UserDto getUser(@PathVariable Long id) {
        User user = userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
        return mapToDto(user);
    }
    
    private UserDto mapToDto(User user) {
        return new UserDto(
            user.getId(),
            user.getEmail(),
            user.getFirstName(),
            user.getLastName()
        );
    }
}
```

### Step 4: Data Migration Strategy

Data is often the hardest part. You have several options:

1. **Dual Write**: Write to both monolith and microservice databases during migration
2. **Change Data Capture (CDC)**: Use tools like Debezium to replicate changes
3. **Batch Migration**: Migrate historical data, then sync deltas

Here’s a CDC configuration using Kafka Connect and Debezium:

```yaml
name: postgres-connector
config: {
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "database.hostname": "monolith-db",
  "database.port": "5432",
  "database.user": "debezium",
  "database.password": "dbz",
  "database.dbname": "monolith_db",
  "topic.prefix": "monolith",
  "schema.include.list": "public"
}
```

### Step 5: Implement the Router Logic

Your router needs to handle both read and write requests. For writes, you’ll need to ensure consistency between the monolith and the new service.

```java
@Service
public class StranglerRouter {
    
    @Autowired
    private MonolithClient monolithClient;
    
    @Autowired
    private UserClient userClient;
    
    @Autowired
    private MigrationStatusService migrationStatus;
    
    public Mono<Response> handleRequest(Request request) {
        String path = request.getPath();
        
        if (path.startsWith("/api/users") && 
            migrationStatus.isMigrated("user-service")) {
            return userClient.handle(request);
        }
        
        return monolithClient.handle(request);
    }
}
```

### Step 6: Monitor and Iterate

Implement comprehensive monitoring using tools like Prometheus, Grafana, and Jaeger. Track:

- Request latency for routed vs. monolith requests
- Error rates in both systems
- Database replication lag
- Service health and availability

## Common Pitfalls and How to Avoid Them

### Pitfall 1: Distributed Transactions

When you split a monolith, you lose the ability to use distributed transactions. Instead of trying to maintain ACID properties across services, embrace eventual consistency. Use patterns like Saga, Outbox, or Event Sourcing.

```java
@TransactionConfiguration(timeout = 30)
public class OrderSaga {
    
    @Autowired
    private OrderRepository orderRepository;
    
    @Autowired
    private PaymentService paymentService;
    
    @Autowired
    private InventoryService inventoryService;
    
    public void executeOrder(Order order) {
        try {
            Order saved = orderRepository.save(order);
            paymentService.charge(saved.getPaymentDetails());
            inventoryService.reserve(saved.getItems());
        } catch (Exception e) {
            // Compensation: undo changes
            orderRepository.delete(saved.getId());
            paymentService.refund(saved.getPaymentDetails());
            inventoryService.release(saved.getItems());
        }
    }
}
```

### Pitfall 2: Network Latency

Microservices introduce network hops. What was a method call in the monolith is now an HTTP request. Optimize by:

- Using async communication where possible
- Implementing caching strategies
- Batching requests
- Choosing the right serialization format (Protobuf vs JSON)

### Pitfall 3: Incomplete Extraction

Don’t leave dangling references. When you migrate a service, ensure all callers are updated. Use tools like ArchUnit to enforce boundaries:

```java
@ArchTest
public class UserModuleTest {
    
    private static final ArchRule noUserModuleInMonolith = 
        noClasses().that()
            .resideInAPackage("com.example.monolith.user..")
            .should().bePublic();
}
```

### Pitfall 4: Data Consistency Issues

During migration, you’ll have data in both places. Implement a reconciliation process to detect and fix inconsistencies.

```java
@Component
public class DataReconciler {
    
    @Scheduled(fixedRate = 5000)
    public void reconcile() {
        List<Long> monolithUsers = monolithClient.getAllUserIds();
        List<Long> microserviceUsers = userService.getAllUserIds();
        
        Set<Long> monolithSet = new HashSet<>(monolithUsers);
        Set<Long> microserviceSet = new HashSet<>(microserviceUsers);
        
        // Find discrepancies
        Set<Long> missingInMicroservice = new HashSet<>(monolithSet);
        missingInMicroservice.removeAll(microserviceSet);
        
        Set<Long> missingInMonolith = new HashSet<>(microserviceSet);
        missingInMonolith.removeAll(monolithSet);
        
        // Log and alert on discrepancies
        if (!missingInMicroservice.isEmpty() || !missingInMonolith.isEmpty()) {
            logger.warn("Data inconsistency detected");
            alertService.notify("Data reconciliation failed");
        }
    }
}
```

## Testing the Migration

### Contract Testing

Use Pact or Spring Cloud Contract to ensure your microservice maintains backward compatibility with the monolith’s API.

```yaml
provider:
  name: user-service
consumer:
  name: monolith
interactions:
  - description: "Get user by ID"
    request:
      method: GET
      path: /api/users/123
    response:
      status: 200
      body:
        id: 123
        email: "user@example.com"
```

### Canary Deployments

Route a small percentage of traffic to the new service first. Monitor metrics closely before increasing the percentage.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service-canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: user-service
      track: canary
  template:
    metadata:
      labels:
        app: user-service
        track: canary
    spec:
      containers:
      - name: user-service
        image: user-service:canary
```

## When to Stop

The Strangler Fig pattern doesn’t require you to eliminate the monolith entirely. Some teams keep a "minimal monolith" that handles core functionality while new features are built as microservices. Others fully migrate. The key is to reach a point where the architecture supports your business needs without the technical debt of the original monolith.

Signs you’re done:
- All critical paths are migrated and tested
- The monolith no longer accepts new feature development
- Monitoring shows stable, independent operation
- Deployment frequency has improved significantly

## Key Takeaways

- **Incremental is better**: The Strangler Fig pattern allows you to migrate without the risk of a big bang rewrite
- **Router is key**: A robust routing layer enables gradual migration and easy rollback
- **Data consistency matters**: Plan for dual writes, CDC, or reconciliation during migration
- **Embrace eventual consistency**: Distributed transactions are hard; use sagas and event-driven patterns instead
- **Monitor everything**: You can’t migrate what you can’t measure
- **Don’t rush**: Take your time with each extraction. Better to migrate slowly and correctly than quickly and broken

The journey from monolith to microservices is a marathon, not a sprint. The Strangler Fig pattern gives you the tools to run that marathon without collapsing. Start small, learn continuously, and let the architecture evolve alongside your business needs.