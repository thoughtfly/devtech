---
title: "CQRS and Event Sourcing: A Practical Introduction"
date: 2026-07-23
tags: [CQRS, Event Sourcing, Java, Architecture, DDD]
categories: [Java]
cover:
description: Learn CQRS and Event Sourcing with practical Java examples. Understand patterns, trade-offs, and when to use them in real-world applications.
---

# CQRS and Event Sourcing: A Practical Introduction

You’ve probably heard the terms CQRS and Event Sourcing thrown around in architecture discussions. Maybe you’ve seen them associated with microservices, DDD, or high-performance systems. But what do they actually mean in practice? And more importantly—should you use them?

In this post, I’ll walk through the core concepts of CQRS (Command Query Responsibility Segregation) and Event Sourcing with concrete Java examples. We’ll look at real trade-offs, common pitfalls, and when these patterns actually shine.

## The Problem with Traditional CRUD

Before diving into patterns, let’s look at a typical CRUD-based system. Imagine a simple banking application:

```java
@Entity
public class Account {
    @Id private Long id;
    private BigDecimal balance;
    private String owner;
    
    public void deposit(BigDecimal amount) {
        this.balance = this.balance.add(amount);
    }
    
    public void withdraw(BigDecimal amount) {
        if (this.balance.compareTo(amount) < 0) {
            throw new InsufficientFundsException();
        }
        this.balance = this.balance.subtract(amount);
    }
}
```

This works fine for simple cases. But as your system grows, you notice problems:

- **Read and write models are coupled.** The same entity handles both commands (deposit/withdraw) and queries (get balance). If you want different representations for reads (e.g., a dashboard showing transaction history), you either add more fields or create separate DTOs that still depend on the same entity.
- **Performance suffers.** Complex queries (aggregations, reporting) slow down writes because they share the same data store.
- **Audit trails are hard.** To track changes, you need additional tables or columns (e.g., `updated_at`, `changed_by`). Even then, reconstructing historical state is painful.
- **Conflict resolution is tricky.** In concurrent systems, locking strategies become complex and error-prone.

These problems are not hypothetical—I’ve seen them in production systems handling millions of transactions. CQRS and Event Sourcing address these issues head-on.

## CQRS: Separating Commands from Queries

CQRS is a pattern that separates read operations (queries) from write operations (commands). Instead of a single model, you have two distinct models:

- **Command Model:** Handles writes. Validates business rules, enforces invariants, and produces events. Returns void or a simple acknowledgment.
- **Query Model:** Handles reads. Optimized for specific query needs, can be denormalized, and may use different storage technology.

### A Simple CQRS Example in Java

Let’s refactor the banking example. First, the command side:

```java
// Command
public class DepositCommand {
    private final UUID accountId;
    private final BigDecimal amount;
    // constructor, getters
}

// Command Handler
public class DepositCommandHandler {
    private final AccountRepository repository;
    
    public void handle(DepositCommand command) {
        Account account = repository.findById(command.getAccountId());
        account.deposit(command.getAmount());
        repository.save(account);
    }
}
```

Now the query side—completely separate:

```java
// Query
public class GetAccountBalanceQuery {
    private final UUID accountId;
    // constructor, getter
}

// Query Handler
public class GetAccountBalanceQueryHandler {
    private final AccountReadModelRepository readRepo;
    
    public AccountBalanceDTO handle(GetAccountBalanceQuery query) {
        return readRepo.findBalanceByAccountId(query.getAccountId());
    }
}
```

Notice that the query handler uses a different repository (`AccountReadModelRepository`). This repository might back a denormalized table, a Redis cache, or even a search index—whatever suits the read use case.

### Benefits of CQRS
- **Independent scaling:** Reads and writes can scale separately. If you have a read-heavy workload, you can add more read replicas without affecting writes.
- **Optimized models:** Write models enforce consistency; read models are denormalized for fast queries.
- **Security:** You can apply different authorization rules to commands and queries.
- **Team autonomy:** Different teams can own the read and write sides, each using their preferred technology.

But CQRS also adds complexity. You now have two models to maintain, and eventual consistency between them must be handled. Which brings us to Event Sourcing.

## Event Sourcing: Store Events, Not State

Event Sourcing is a pattern where you store all changes to an application state as a sequence of events. Instead of persisting the current state, you persist the events that led to that state.

### How It Works

In the banking example, instead of storing the current balance, you store events like:

```java
public interface DomainEvent {}

public class AccountCreated implements DomainEvent {
    private final UUID accountId;
    private final String owner;
    private final BigDecimal initialBalance;
    // constructor, getters
}

public class MoneyDeposited implements DomainEvent {
    private final UUID accountId;
    private final BigDecimal amount;
    private final Instant timestamp;
    // constructor, getters
}

public class MoneyWithdrawn implements DomainEvent {
    private final UUID accountId;
    private final BigDecimal amount;
    private final Instant timestamp;
    // constructor, getters
}
```

To get the current state, you replay all events for an aggregate:

```java
public class Account {
    private UUID id;
    private BigDecimal balance;
    private boolean isActive;
    
    public static Account recreateFrom(List<DomainEvent> events) {
        Account account = new Account();
        for (DomainEvent event : events) {
            account.apply(event);
        }
        return account;
    }
    
    private void apply(DomainEvent event) {
        if (event instanceof AccountCreated) {
            this.id = ((AccountCreated) event).getAccountId();
            this.balance = ((AccountCreated) event).getInitialBalance();
            this.isActive = true;
        } else if (event instanceof MoneyDeposited) {
            this.balance = this.balance.add(((MoneyDeposited) event).getAmount());
        } else if (event instanceof MoneyWithdrawn) {
            this.balance = this.balance.subtract(((MoneyWithdrawn) event).getAmount());
        }
    }
    
    public List<DomainEvent> deposit(BigDecimal amount) {
        // Business validation
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Deposit amount must be positive");
        }
        return List.of(new MoneyDeposited(UUID.randomUUID(), this.id, amount, Instant.now()));
    }
}
```

Notice that `deposit()` returns events instead of modifying state directly. The caller is responsible for persisting those events.

### Event Store

An event store is a database optimized for storing events. It typically:
- Appends events sequentially
- Loads all events for an aggregate by its ID
- Supports optimistic concurrency (e.g., using version numbers)

Here’s a simple in-memory event store:

```java
public class InMemoryEventStore {
    private final Map<UUID, List<DomainEvent>> store = new ConcurrentHashMap<>();
    
    public synchronized void save(UUID aggregateId, List<DomainEvent> newEvents, int expectedVersion) {
        List<DomainEvent> existing = store.getOrDefault(aggregateId, new ArrayList<>());
        if (existing.size() != expectedVersion) {
            throw new ConcurrencyException("Version conflict");
        }
        existing.addAll(newEvents);
        store.put(aggregateId, existing);
    }
    
    public List<DomainEvent> load(UUID aggregateId) {
        return store.getOrDefault(aggregateId, Collections.emptyList());
    }
}
```

### Combining CQRS and Event Sourcing

CQRS and Event Sourcing complement each other naturally:

1. **Commands** produce events.
2. **Events** are stored in the event store.
3. **Projections** consume events and update the read model.

Here’s how the command handler looks with Event Sourcing:

```java
public class DepositCommandHandler {
    private final EventStore eventStore;
    
    public void handle(DepositCommand command) {
        List<DomainEvent> events = eventStore.load(command.getAccountId());
        Account account = Account.recreateFrom(events);
        List<DomainEvent> newEvents = account.deposit(command.getAmount());
        eventStore.save(command.getAccountId(), newEvents, events.size());
    }
}
```

And a simple projection that updates the read model:

```java
public class AccountBalanceProjection {
    private final AccountReadModelRepository readRepo;
    
    public void handle(MoneyDeposited event) {
        readRepo.updateBalance(event.getAccountId(), 
            balance -> balance.add(event.getAmount()));
    }
    
    public void handle(MoneyWithdrawn event) {
        readRepo.updateBalance(event.getAccountId(), 
            balance -> balance.subtract(event.getAmount()));
    }
}
```

## When to Use CQRS + Event Sourcing

These patterns are powerful but not a silver bullet. Use them when:

- **Audit and compliance are critical.** Event Sourcing gives you a complete, immutable history.
- **Complex business logic with many state changes.** Think order management, banking, or inventory systems.
- **You need temporal queries.** “What did the account look like last Tuesday?” becomes trivial.
- **High write throughput with eventual consistency.** CQRS allows you to batch updates to read models.

Avoid them when:

- **Simple CRUD is sufficient.** Don’t over-engineer.
- **Strong consistency is required immediately.** Eventual consistency can be problematic for some use cases (e.g., real-time bidding).
- **Your team is new to the patterns.** The learning curve is steep.

## Real-World Trade-offs

Let me share some hard-earned lessons:

### Event Versioning

Events change over time. A `MoneyDeposited` event might later need a `transactionId` field. You must handle versioning:

```java
// Version 1
public class MoneyDepositedV1 implements DomainEvent {
    private final UUID accountId;
    private final BigDecimal amount;
}

// Version 2 (adds transactionId)
public class MoneyDepositedV2 implements DomainEvent {
    private final UUID accountId;
    private final BigDecimal amount;
    private final UUID transactionId;
    
    public static MoneyDepositedV2 upgrade(MoneyDepositedV1 old) {
        return new MoneyDepositedV2(old.getAccountId(), old.getAmount(), null);
    }
}
```

### Eventual Consistency

Read models are updated asynchronously. If a user deposits money and immediately queries the balance, they might see the old value. Solutions:
- Use a synchronous projection for critical reads.
- Show a “processing” indicator.
- Use optimistic UI updates.

### Storage Costs

Event stores grow indefinitely. You’ll need strategies like snapshotting (periodically saving the current state to avoid replaying all events).

```java
public class AccountSnapshot {
    private final UUID accountId;
    private final BigDecimal balance;
    private final int version; // last event version included
}
```

## A Practical Example: Order Management

Let’s tie everything together with a more realistic example: an order management system.

### Commands

```java
public class PlaceOrderCommand {
    private final UUID orderId;
    private final UUID customerId;
    private final List<OrderItem> items;
}

public class ShipOrderCommand {
    private final UUID orderId;
}
```

### Events

```java
public class OrderPlaced implements DomainEvent {
    private final UUID orderId;
    private final UUID customerId;
    private final List<OrderItem> items;
    private final Instant placedAt;
}

public class OrderShipped implements DomainEvent {
    private final UUID orderId;
    private final Instant shippedAt;
}
```

### Projections

A projection for the customer dashboard:

```java
public class CustomerOrderProjection {
    private final CustomerOrderRepository repo;
    
    @EventHandler
    public void on(OrderPlaced event) {
        repo.save(new CustomerOrderSummary(
            event.getOrderId(),
            event.getCustomerId(),
            event.getItems().size(),
            "PLACED",
            event.getPlacedAt()
        ));
    }
    
    @EventHandler
    public void on(OrderShipped event) {
        repo.updateStatus(event.getOrderId(), "SHIPPED");
    }
}
```

## Conclusion

CQRS and Event Sourcing are powerful patterns that solve real problems in complex systems. They give you auditability, scalability, and flexibility. But they also introduce significant complexity—event versioning, eventual consistency, and storage management are real challenges.

My advice: start small. Maybe just implement CQRS without Event Sourcing first. Or use Event Sourcing for a single bounded context. Learn the patterns incrementally.

In production, I’ve seen these patterns transform systems—but only when applied thoughtfully. Don’t cargo-cult them. Understand the trade-offs, and you’ll know exactly when they’re the right tool.

## Key Takeaways

- CQRS separates read and write models, allowing independent optimization and scaling.
- Event Sourcing stores state changes as an immutable sequence of events, enabling full auditability and temporal queries.
- Together, they form a powerful combination for systems with complex business logic and audit requirements.
- Event versioning and eventual consistency are the main challenges you’ll face.
- Start with a single bounded context—don’t apply these patterns globally from day one.
- Use snapshots to control event store growth and improve replay performance.