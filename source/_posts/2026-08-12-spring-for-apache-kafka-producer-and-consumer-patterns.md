---
title: "Spring for Apache Kafka: Producer and Consumer Patterns"
date: 2026-08-12
tags: [Spring Boot, Apache Kafka, Kafka Producer, Kafka Consumer, Event-Driven Architecture]
categories: [Java]
cover: "https://images.unsplash.com/photo-1576444356170-66073046b1bc?w=1200&q=80&fit=crop&fm=webp"
description: Explore Spring for Apache Kafka producer and consumer patterns with code examples, best practices, and error handling for robust event-driven microservices.
---

## Introduction

In the world of microservices, event-driven architecture has become a cornerstone for building scalable, decoupled systems. At the heart of this paradigm lies Apache Kafka—a distributed event streaming platform that handles trillions of events a day. But raw Kafka APIs can be verbose and error-prone. That's where **Spring for Apache Kafka** comes in, offering a robust abstraction layer that simplifies producer and consumer development while retaining the flexibility of the underlying Kafka client.

In this post, I'll walk you through the essential producer and consumer patterns using Spring Boot. We'll cover configuration, message serialization, error handling, retries, and advanced patterns like batch consumption and manual acknowledgments. Whether you're new to Kafka or looking to refine your existing setup, this guide provides practical, battle-tested code snippets you can use immediately.

## Why Spring for Apache Kafka?

Spring for Apache Kafka (spring-kafka) provides:

- **Declarative configuration** via `application.yml` or `application.properties`.
- **Templated operations** with `KafkaTemplate` for sending messages.
- **Listener containers** that manage consumer lifecycles and threading.
- **Seamless integration** with Spring Boot's auto-configuration.
- **Robust error handling** with `ErrorHandler` and `RetryTemplate`.

Let's dive into the core patterns.

## Setting Up Dependencies

First, add the necessary dependencies to your `pom.xml` (Maven) or `build.gradle` (Gradle).

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>
</dependency>
```

For Gradle:

```gradle
implementation 'org.springframework.kafka:spring-kafka'
```

## Producer Patterns

### Basic Producer Configuration

In your `application.yml`, configure the producer properties:

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
      properties:
        enable.idempotence: true
        acks: all
        retries: 10
```

- `enable.idempotence` ensures exactly-once semantics for producers.
- `acks=all` guarantees that the leader and all in-sync replicas acknowledge the message.
- `retries` handles transient network errors.

### Sending Messages with KafkaTemplate

Create a service that uses `KafkaTemplate` to send messages:

```java
@Service
public class OrderProducer {

    private final KafkaTemplate<String, Order> kafkaTemplate;

    public OrderProducer(KafkaTemplate<String, Order> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void sendOrder(Order order) {
        kafkaTemplate.send("orders", order.getId(), order);
    }
}
```

The `send` method takes the topic name, key, and value. The key determines partitioning; messages with the same key go to the same partition, preserving order.

### Customizing the KafkaTemplate

You can customize the `KafkaTemplate` bean if needed. For example, to set a default topic or add headers:

```java
@Bean
public KafkaTemplate<String, Order> kafkaTemplate(ProducerFactory<String, Order> producerFactory) {
    KafkaTemplate<String, Order> template = new KafkaTemplate<>(producerFactory);
    template.setDefaultTopic("orders-default");
    return template;
}
```

### Asynchronous Sends and Callbacks

By default, `send` is asynchronous. To handle results or errors, use a callback:

```java
ListenableFuture<SendResult<String, Order>> future = kafkaTemplate.send("orders", order);

future.addCallback(new ListenableFutureCallback<SendResult<String, Order>>() {
    @Override
    public void onSuccess(SendResult<String, Order> result) {
        System.out.println("Sent order: " + order.getId() + " with offset: " + result.getRecordMetadata().offset());
    }

    @Override
    public void onFailure(Throwable ex) {
        System.err.println("Failed to send order: " + order.getId() + " due to: " + ex.getMessage());
    }
});
```

In newer Spring versions, you can use `CompletableFuture`:

```java
CompletableFuture<SendResult<String, Order>> future = kafkaTemplate.send("orders", order).completable();
```

### Producer Interceptors and Custom Serializers

If you need to add custom headers or transform messages before sending, implement a `ProducerInterceptor`:

```java
public class TraceProducerInterceptor implements ProducerInterceptor<String, Order> {

    @Override
    public ProducerRecord<String, Order> onSend(ProducerRecord<String, Order> record) {
        // Add a trace header
        record.headers().add("trace-id", UUID.randomUUID().toString().getBytes());
        return record;
    }

    // other methods omitted for brevity
}
```

Register it in the producer properties:

```yaml
spring:
  kafka:
    producer:
      properties:
        interceptor.classes: com.example.TraceProducerInterceptor
```

## Consumer Patterns

### Basic Consumer Configuration

Configure consumer properties in `application.yml`:

```yaml
spring:
  kafka:
    consumer:
      group-id: order-group
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "com.example"
        auto.offset.reset: earliest
        enable.auto.commit: false
```

- `group-id` defines the consumer group; multiple instances with the same group share the load.
- `auto.offset.reset=earliest` starts reading from the beginning if no committed offset exists.
- `enable.auto.commit=false` gives you manual control over offset commits, which we'll discuss later.

### Implementing a Consumer with @KafkaListener

The simplest way to consume messages is the `@KafkaListener` annotation:

```java
@Component
public class OrderConsumer {

    @KafkaListener(topics = "orders", groupId = "order-group")
    public void onOrderReceived(Order order) {
        System.out.println("Received order: " + order);
        // Process the order...
    }
}
```

You can access the message headers and partition info via `ConsumerRecord`:

```java
@KafkaListener(topics = "orders")
public void onOrderReceived(ConsumerRecord<String, Order> record) {
    String key = record.key();
    Order order = record.value();
    int partition = record.partition();
    long offset = record.offset();
    // Process...
}
```

### Batch Consumption

For high-throughput scenarios, you can consume messages in batches:

```java
@KafkaListener(topics = "orders", containerFactory = "batchFactory")
public void onBatch(List<Order> orders) {
    System.out.println("Received " + orders.size() + " orders");
    // Process batch...
}
```

You need to configure a listener container factory that supports batch mode:

```java
@Bean
public ConcurrentKafkaListenerContainerFactory<String, Order> batchFactory(
        ConsumerFactory<String, Order> consumerFactory) {
    ConcurrentKafkaListenerContainerFactory<String, Order> factory = new ConcurrentKafkaListenerContainerFactory<>();
    factory.setConsumerFactory(consumerFactory);
    factory.setBatchListener(true);
    return factory;
}
```

### Manual Acknowledgment

If you need to commit offsets only after successful processing, use manual acknowledgment:

```java
@KafkaListener(topics = "orders")
public void onOrderReceived(ConsumerRecord<String, Order> record, Acknowledgment ack) {
    try {
        // Process the order
        processOrder(record.value());
        ack.acknowledge();
    } catch (Exception e) {
        // Log error, maybe send to DLT
    }
}
```

Remember to set `enable.auto.commit=false` in your consumer config.

### Error Handling and Retry

Spring Kafka provides several mechanisms for handling errors. The simplest is to use a `DefaultErrorHandler` with a `FixedBackOff`:

```java
@Bean
public DefaultErrorHandler errorHandler() {
    FixedBackOff backOff = new FixedBackOff(1000L, 3); // retry 3 times with 1s delay
    return new DefaultErrorHandler(backOff);
}
```

Then attach it to the container factory:

```java
@Bean
public ConcurrentKafkaListenerContainerFactory<String, Order> kafkaListenerContainerFactory(
        ConsumerFactory<String, Order> consumerFactory) {
    ConcurrentKafkaListenerContainerFactory<String, Order> factory = new ConcurrentKafkaListenerContainerFactory<>();
    factory.setConsumerFactory(consumerFactory);
    factory.setCommonErrorHandler(errorHandler());
    return factory;
}
```

For more complex retry logic, you can use `RetryTemplate`:

```java
@Bean
public RetryTemplate retryTemplate() {
    RetryTemplate retryTemplate = new RetryTemplate();
    ExponentialBackOffPolicy backOffPolicy = new ExponentialBackOffPolicy();
    backOffPolicy.setInitialInterval(1000);
    backOffPolicy.setMultiplier(2.0);
    backOffPolicy.setMaxInterval(10000);
    retryTemplate.setBackOffPolicy(backOffPolicy);
    return retryTemplate;
}
```

### Dead Letter Topic (DLT) Pattern

When messages fail after retries, it's common to send them to a Dead Letter Topic for later inspection. Spring Kafka supports this via `@RetryableTopic`:

```java
@RetryableTopic(
    attempts = "4",
    backoff = @Backoff(delay = 1000, multiplier = 2.0),
    autoCreateTopics = "true",
    kafkaTemplate = "kafkaTemplate"
)
@KafkaListener(topics = "orders")
public void onOrderReceived(Order order) {
    // Process order; if it fails, it will be retried and then sent to a DLT
}
```

This automatically creates topics like `orders-retry-0`, `orders-retry-1`, etc., and finally `orders-dlt`. To consume from the DLT:

```java
@KafkaListener(topics = "orders-dlt")
public void onDltMessage(Order order) {
    // Log or alert about the failed message
}
```

### Consumer Seek and Idle Handling

If you need to rewind offsets (e.g., for reprocessing), you can use `SeekToCurrentErrorHandler` or manually seek:

```java
@KafkaListener(topics = "orders")
public void onOrderReceived(ConsumerRecord<String, Order> record, Consumer<?, ?> consumer) {
    // Process...
    if (errorCondition) {
        consumer.seek(new TopicPartition(record.topic(), record.partition()), record.offset());
    }
}
```

For handling idle consumers (e.g., to send heartbeats), implement `ConsumerSeekAware` or use `ContainerStoppingErrorHandler`.

## Advanced Patterns

### Compacted Topics and Keyed Messages

For stateful processing, use compacted topics where only the latest value for each key is retained. Configure the topic with `cleanup.policy=compact` and ensure your producer uses meaningful keys.

### Transactions

Spring Kafka supports transactions to ensure exactly-once semantics across producers and consumers. Enable transactions on the producer:

```yaml
spring:
  kafka:
    producer:
      properties:
        enable.idempotence: true
        transactional.id: tx-orders
```

Then use `@Transactional` on your method:

```java
@Transactional
public void sendOrderAndUpdateDB(Order order) {
    kafkaTemplate.send("orders", order);
    // update database
}
```

### Custom Message Converters

If you need to convert messages to a custom format (e.g., Avro), implement a `MessageConverter`:

```java
@Bean
public MessageConverter messageConverter() {
    return new ByteArrayJsonMessageConverter();
}
```

## Testing Kafka Applications

Spring Kafka provides `@EmbeddedKafka` for integration testing:

```java
@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = {"orders"})
public class OrderConsumerTest {

    @Autowired
    private KafkaTemplate<String, Order> kafkaTemplate;

    @Test
    void testOrderConsumption() throws InterruptedException {
        kafkaTemplate.send("orders", new Order("123", "item"));
        // Verify consumer received the message
    }
}
```

## Monitoring and Observability

Use Spring Boot Actuator to expose Kafka metrics:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
```

You can also integrate with Micrometer to track consumer lag via Kafka's `KafkaConsumerMetrics`.

## Common Pitfalls and Best Practices

- **Avoid heavy processing in the listener thread**; offload to a separate executor if needed.
- **Set appropriate `max.poll.records`** to control batch size and avoid long processing times.
- **Use `spring.kafka.consumer.properties.max.poll.interval.ms`** to prevent consumer rebalancing during long processing.
- **Always close the `KafkaTemplate`** in a `@PreDestroy` method if you create it manually.
- **Handle deserialization exceptions** gracefully; use a custom `ErrorHandler` to avoid infinite loops.
- **Test with `@EmbeddedKafka`** to catch issues early.

## Key Takeaways

- Spring for Apache Kafka abstracts the complexity of Kafka clients, allowing you to focus on business logic.
- Use `KafkaTemplate` for reliable, asynchronous message sending with optional callbacks.
- `@KafkaListener` is the cornerstone for consumer development, supporting batch, manual acknowledgment, and error handling.
- Implement retries with `DefaultErrorHandler` or `@RetryableTopic` to build resilient consumers.
- Leverage dead letter topics to handle poison messages without blocking the main flow.
- For exactly-once semantics, combine idempotent producers with transactional support.
- Always configure proper serializers, trusted packages, and offset management to avoid production surprises.

By mastering these patterns, you can build robust, scalable event-driven microservices with Spring Boot and Apache Kafka. Happy coding!