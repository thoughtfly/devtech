---
title: "Handling Transactions in Spring: @Transactional Deep Dive"
date: 2026-07-02
tags: [Spring, Transactions, @Transactional, Java, Database]
categories: [Java]
cover:
description: Master Spring's @Transactional annotation with this deep dive. Learn propagation, isolation levels, rollback rules, and common pitfalls with practical code e...
---

# Handling Transactions in Spring: @Transactional Deep Dive

Transactions are the backbone of reliable data operations in enterprise applications. They ensure that a series of database operations either complete successfully as a unit or fail gracefully without leaving partial changes. Spring's `@Transactional` annotation is the most common way to manage transactions declaratively, but beneath its simple syntax lies a powerful and nuanced system. Misunderstand it, and you might end up with inconsistent data, deadlocks, or performance bottlenecks.

In this deep dive, I'll walk through how `@Transactional` works under the hood, explore propagation and isolation levels, discuss rollback rules, and highlight common pitfalls that even experienced developers encounter. Let's get started.

## How @Transactional Works

At its core, `@Transactional` is a declarative way to define transaction boundaries. When Spring sees this annotation on a method or class, it wraps the method invocation in a transaction using AOP (Aspect-Oriented Programming).

### The Proxy Mechanism

Spring creates a proxy around the bean that has `@Transactional` methods. When you call a method on the bean, the proxy intercepts the call, starts a transaction (or joins an existing one), invokes the actual method, and then commits or rolls back based on the outcome.

```java
@Service
public class PaymentService {
    @Transactional
    public void processPayment(Long orderId) {
        // Business logic
        paymentRepository.save(payment);
        orderRepository.updateStatus(orderId, "PAID");
    }
}
```

Here, the proxy ensures that both `save` and `updateStatus` happen within the same transaction. If an exception occurs, both operations are rolled back.

### Self-Invocation Pitfall

One of the most common mistakes is calling a `@Transactional` method from within the same class. Because the proxy only intercepts external calls, a direct internal call bypasses the proxy entirely.

```java
@Service
public class PaymentService {
    public void processPayment(Long orderId) {
        // This call does NOT go through the proxy
        updateOrderStatus(orderId);
    }

    @Transactional
    public void updateOrderStatus(Long orderId) {
        // Transaction logic
    }
}
```

**Solution:** Inject the proxy or restructure code to call the method from a separate bean.

```java
@Service
public class PaymentService {
    @Autowired
    private PaymentService self; // Self-injection

    public void processPayment(Long orderId) {
        self.updateOrderStatus(orderId);
    }

    @Transactional
    public void updateOrderStatus(Long orderId) {
        // Now this runs in a transaction
    }
}
```

## Propagation Levels

Propagation defines how transactions relate to each other when a method is called within an existing transaction context. Spring provides seven propagation behaviors via `Propagation` enum.

### REQUIRED (Default)

If a transaction exists, join it; otherwise, create a new one. This is the most common choice.

```java
@Transactional(propagation = Propagation.REQUIRED)
public void transferFunds(Account from, Account to, BigDecimal amount) {
    debit(from, amount);
    credit(to, amount);
}
```

### REQUIRES_NEW

Always create a new transaction, suspending the current one if it exists. Use this for operations that must commit independently, like audit logging.

```java
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void logAudit(AuditEntry entry) {
    auditRepository.save(entry);
}
```

### NESTED

Executes within a nested transaction if a current transaction exists. This uses savepoints internally, allowing partial rollback.

```java
@Transactional(propagation = Propagation.NESTED)
public void updateInventory(Long productId, int quantity) {
    inventoryRepository.update(productId, quantity);
}
```

### MANDATORY, NEVER, NOT_SUPPORTED, SUPPORTS

- **MANDATORY**: Must be called within an existing transaction; throws exception otherwise.
- **NEVER**: Must not run within a transaction; throws exception if one exists.
- **NOT_SUPPORTED**: Suspends any existing transaction and runs non-transactionally.
- **SUPPORTS**: If a transaction exists, join it; otherwise, run non-transactionally.

## Isolation Levels

Isolation levels control how transaction changes are visible to other concurrent transactions. Spring maps these to database-specific levels via `Isolation` enum.

### READ_UNCOMMITTED

Lowest isolation; dirty reads, non-repeatable reads, and phantom reads are possible. Rarely used in production.

### READ_COMMITTED (Default in most databases)

Prevents dirty reads; non-repeatable reads and phantom reads can still occur. It's a good balance for most applications.

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public BigDecimal getBalance(Long accountId) {
    return accountRepository.findById(accountId).getBalance();
}
```

### REPEATABLE_READ

Prevents dirty and non-repeatable reads; phantom reads can still occur. Ensures that if you read a row twice, you get the same data.

### SERIALIZABLE

Highest isolation; prevents dirty reads, non-repeatable reads, and phantom reads. It achieves this by locking ranges, which can severely impact concurrency.

### Practical Guidance

- Use `READ_COMMITTED` for most operations.
- Use `REPEATABLE_READ` or `SERIALIZABLE` only when you must prevent phantom reads and can accept reduced concurrency.
- Remember that isolation levels are database-dependent; always verify behavior with your specific database.

## Rollback Rules

By default, `@Transactional` rolls back on unchecked exceptions (`RuntimeException` and `Error`) but not on checked exceptions. This is often surprising to developers coming from other frameworks.

```java
@Transactional
public void processOrder(Order order) throws BusinessException {
    // If BusinessException is checked, the transaction does NOT roll back
    throw new BusinessException("Order invalid");
}
```

### Customizing Rollback Behavior

You can override this using `rollbackFor` and `noRollbackFor`.

```java
@Transactional(rollbackFor = BusinessException.class, noRollbackFor = InvalidDataException.class)
public void processOrder(Order order) throws BusinessException {
    // BusinessException triggers rollback
    // InvalidDataException does not
}
```

### Best Practice

Always explicitly declare rollback rules for clarity, especially when dealing with checked exceptions.

## Transaction Timeout

Set a timeout to prevent long-running transactions from holding locks.

```java
@Transactional(timeout = 5) // seconds
public void bulkImport(List<Record> records) {
    // If this takes more than 5 seconds, the transaction is rolled back
}
```

The timeout starts when the transaction begins. If the method takes longer, Spring throws `TransactionTimedOutException`.

## Read-Only Transactions

Marking a transaction as read-only can optimize performance by allowing the database to skip certain locks.

```java
@Transactional(readOnly = true)
public List<Product> getAllProducts() {
    return productRepository.findAll();
}
```

**Note:** Read-only is only a hint; some databases ignore it. It does not prevent writes; you should still enforce read-only logic in your code.

## Common Pitfalls and Solutions

### 1. Transactional on Private Methods

`@Transactional` on private methods has no effect because the proxy cannot intercept them.

**Solution:** Only use `@Transactional` on public methods.

### 2. Mixing Transactional with Async

Combining `@Transactional` with `@Async` can cause issues because the async call runs in a different thread, losing the transaction context.

**Solution:** Ensure transaction propagation is `REQUIRES_NEW` or handle transactions explicitly within the async method.

### 3. Transactional in Tests

Spring test framework supports `@Transactional` on test methods, automatically rolling back after each test. This is great for isolation but can mask issues if you rely on committed data.

```java
@SpringBootTest
@Transactional
class PaymentServiceTest {
    @Test
    void testPayment() {
        // Transaction is rolled back after this test
    }
}
```

### 4. Large Transactions

Keeping transactions open for too long can cause connection pool exhaustion and lock contention.

**Solution:** Keep transactions as short as possible. Move heavy computations or external API calls outside the transaction.

### 5. Transactional with JPA Lazy Loading

Accessing lazy-loaded entities outside a transaction throws `LazyInitializationException`.

**Solution:** Use `@Transactional(readOnly = true)` on service methods that fetch data, or use `FetchType.EAGER` judiciously.

## Advanced: Transaction Management with PlatformTransactionManager

While `@Transactional` is convenient, sometimes you need programmatic control. Spring provides `PlatformTransactionManager` for this.

```java
@Service
public class PaymentService {
    @Autowired
    private PlatformTransactionManager transactionManager;

    public void processPayment() {
        TransactionDefinition def = new DefaultTransactionDefinition();
        TransactionStatus status = transactionManager.getTransaction(def);
        try {
            // Business logic
            transactionManager.commit(status);
        } catch (Exception e) {
            transactionManager.rollback(status);
            throw e;
        }
    }
}
```

This is useful when you need fine-grained control, such as retrying transactions or handling multiple transaction managers.

## Conclusion (Key Takeaways)

Let's summarize the critical points from this deep dive:

- **@Transactional** uses AOP proxies; internal method calls bypass the proxy, so inject the bean or refactor.
- **Propagation** controls transaction boundaries; `REQUIRED` is the default, `REQUIRES_NEW` for independent operations.
- **Isolation** levels trade consistency for concurrency; `READ_COMMITTED` is usually sufficient.
- **Rollback** defaults to unchecked exceptions; use `rollbackFor` and `noRollbackFor` to customize.
- **Timeout** prevents long-running transactions; set it wisely.
- **Read-only** hints optimize performance but are not enforced.
- **Common pitfalls** include self-invocation, private methods, async mixing, and large transactions.
- **Programmatic management** with `PlatformTransactionManager` offers granular control when needed.

Mastering `@Transactional` is essential for building robust Spring applications. Test your transaction behavior thoroughly, especially in concurrent scenarios, and always keep transactions short and focused. Happy coding!