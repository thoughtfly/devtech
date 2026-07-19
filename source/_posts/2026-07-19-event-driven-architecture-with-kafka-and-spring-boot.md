---
title: "Event-Driven Architecture with Kafka and Spring Boot: A Practical Guide"
date: 2026-07-19
tags: [Apache Kafka, Spring Boot, Event-Driven Architecture, Microservices, Java, Message Queue]
categories: [Java]
cover:
description: Learn how to build a robust event-driven system using Apache Kafka and Spring Boot. Covers architecture, producers, consumers, error handling, and best pract...
---

# Event-Driven Architecture with Kafka and Spring Boot: A Practical Guide

Event-driven architecture (EDA) has become a cornerstone of modern, scalable systems. By decoupling services and enabling asynchronous communication, EDA allows teams to build resilient, responsive applications that can handle massive throughput. Apache Kafka, combined with Spring Boot, provides a powerful yet approachable stack for implementing this pattern.

In this guide, I'll walk through the core concepts of event-driven design, how to set up Kafka with Spring Boot, and share battle-tested patterns for producers, consumers, error handling, and schema management. Whether you're new to Kafka or looking to refine your approach, this post will give you practical, production-ready knowledge.

## Why Event-Driven Architecture?

Traditional synchronous communication (REST, gRPC) creates tight coupling between services. If Service A calls Service B and B is slow or down, A suffers. In an event-driven system, services communicate through events—immutable records of something that happened. 

Key benefits:
- **Decoupling**: Producers and consumers don't need to know about each other
- **Scalability**: Each component can scale independently based on its own load
- **Resilience**: Failures are isolated; events can be replayed
- **Auditability**: Event logs provide a complete history of state changes

## Apache Kafka in a Nutshell

Kafka is a distributed event streaming platform. At its core:
- **Topics**: Categories for events (like database tables)
- **Partitions**: Subdivisions of topics for parallelism
- **Producers**: Publish events to topics
- **Consumers**: Subscribe to topics and process events
- **Brokers**: Servers that store and serve events

Kafka guarantees ordering within a partition and retains events even after consumption (configurable retention period). This makes it ideal for event sourcing, stream processing, and data pipelines.

## Setting Up Spring Boot with Kafka

Spring Boot provides excellent support via `spring-kafka`. Let's start with the basics.

### Dependencies

Add the following to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>
</dependency>
```

### Configuration

In `application.yml`:

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
    consumer:
      group-id: order-service-group
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "*"
```

For local development, start Kafka using Docker:

```bash
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  confluentinc/cp-kafka:latest
```

## Building a Producer

A producer publishes events to a topic. Let's create an order event producer.

### Event Class

```java
public class OrderEvent {
    private String orderId;
    private String customerId;
    private BigDecimal amount;
    private LocalDateTime timestamp;
    // getters, setters, constructors
}
```

### Producer Service

```java
@Service
public class OrderEventProducer {

    private static final Logger log = LoggerFactory.getLogger(OrderEventProducer.class);
    private static final String TOPIC = "order-events";

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public OrderEventProducer(KafkaTemplate<String, OrderEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void publishOrderCreated(OrderEvent event) {
        CompletableFuture<SendResult<String, OrderEvent>> future =
            kafkaTemplate.send(TOPIC, event.getOrderId(), event);
        
        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("Event published successfully: {}, partition: {}, offset: {}",
                    event.getOrderId(),
                    result.getRecordMetadata().partition(),
                    result.getRecordMetadata().offset());
            } else {
                log.error("Failed to publish event: {}", event.getOrderId(), ex);
            }
        });
    }
}
```

**Key points**:
- Use the event's natural key (e.g., `orderId`) as the Kafka key to maintain ordering per entity
- Handle async results properly—never ignore the future
- Log success and failure for observability

## Building a Consumer

Consumers process events. Spring Kafka makes this trivial with `@KafkaListener`.

```java
@Component
public class OrderEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(OrderEventConsumer.class);

    @KafkaListener(topics = "order-events", groupId = "order-service-group")
    public void handleOrderCreated(OrderEvent event, @Header(KafkaHeaders.RECEIVED_KEY) String key) {
        log.info("Received order event: key={}, orderId={}, amount={}",
            key, event.getOrderId(), event.getAmount());
        
        // Process the event - e.g., update inventory, send confirmation
        processOrder(event);
    }

    private void processOrder(OrderEvent event) {
        // Business logic here
    }
}
```

### Consumer Configuration

For fine-grained control, define a `ConcurrentKafkaListenerContainerFactory`:

```java
@Configuration
public class KafkaConsumerConfig {

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, OrderEvent>
            orderKafkaListenerContainerFactory(ConsumerFactory<String, OrderEvent> consumerFactory) {
        ConcurrentKafkaListenerContainerFactory<String, OrderEvent> factory =
            new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        factory.setConcurrency(3); // Number of threads
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        return factory;
    }
}
```

## Error Handling and Retries

Failures happen. A consumer might throw an exception due to a database error or invalid data. How you handle this defines your system's resilience.

### Dead Letter Topic (DLT)

Spring Kafka supports automatic DLT handling:

```java
@RetryableTopic(
    attempts = "4",
    backoff = @Backoff(delay = 1000, multiplier = 2.0),
    autoCreateTopics = "true",
    dltTopicSuffix = "-dlt"
)
@KafkaListener(topics = "order-events", groupId = "order-service-group")
public void handleOrderCreated(OrderEvent event) {
    // processing logic
}

@DltHandler
public void handleDlt(OrderEvent event, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
    log.error("Event moved to DLT: topic={}, event={}", topic, event);
    // Alert, log, or store for manual intervention
}
```

This configuration will retry 3 times (total 4 attempts) with exponential backoff, then send the failed event to a `-dlt` topic.

### Manual Acknowledgment

For more control, use manual acknowledgment:

```java
@KafkaListener(topics = "order-events", groupId = "order-service-group")
public void handleOrderCreated(OrderEvent event, Acknowledgment ack) {
    try {
        processOrder(event);
        ack.acknowledge();
    } catch (Exception e) {
        // Log and decide: retry later, skip, or send to DLT
        ack.nack(1000); // Requeue after 1 second
    }
}
```

## Schema Management with Avro

As your system grows, event schemas evolve. Using Avro with Schema Registry provides compatibility guarantees.

### Setup

Add dependencies:

```xml
<dependency>
    <groupId>io.confluent</groupId>
    <artifactId>kafka-avro-serializer</artifactId>
    <version>7.3.0</version>
</dependency>
<dependency>
    <groupId>org.apache.avro</groupId>
    <artifactId>avro</artifactId>
    <version>1.11.1</version>
</dependency>
```

### Avro Schema

```avro
{
  "type": "record",
  "name": "OrderEvent",
  "namespace": "com.example.events",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "customerId", "type": "string"},
    {"name": "amount", "type": "double"},
    {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
  ]
}
```

### Producer with Avro

```java
@Service
public class AvroOrderEventProducer {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public void publishOrderCreated(OrderEvent event) {
        // Avro-generated class used automatically
        kafkaTemplate.send("order-events-avro", event.getOrderId().toString(), event);
    }
}
```

Schema Registry ensures that producers and consumers use compatible schemas, preventing runtime errors from schema drift.

## Idempotent Consumers

In distributed systems, events can be delivered more than once (at-least-once semantics). Your consumers must be idempotent.

### Pattern: Idempotency Key

```java
@Repository
public class ProcessedEventRepository {

    public boolean isAlreadyProcessed(String eventId) {
        // Check database for eventId
    }

    public void markProcessed(String eventId) {
        // Insert into processed_events table
    }
}

@Component
public class IdempotentOrderConsumer {

    private final ProcessedEventRepository repository;

    @KafkaListener(topics = "order-events")
    public void handle(OrderEvent event) {
        String eventId = event.getOrderId() + "-" + event.getTimestamp();
        
        if (repository.isAlreadyProcessed(eventId)) {
            return; // Already processed
        }
        
        processOrder(event);
        repository.markProcessed(eventId);
    }
}
```

This ensures that even if the same event is consumed twice, the side effects happen only once.

## Testing Kafka Producers and Consumers

Testing asynchronous systems requires special care. Spring Kafka provides excellent test support.

### Unit Testing a Producer

```java
@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = { "order-events" })
class OrderEventProducerTest {

    @Autowired
    private KafkaTemplate<String, OrderEvent> kafkaTemplate;

    @Autowired
    private OrderEventProducer producer;

    @Test
    void shouldPublishEvent() {
        OrderEvent event = new OrderEvent("123", "cust1", BigDecimal.TEN);
        
        producer.publishOrderCreated(event);
        
        // Verify using TestUtils
        ConsumerRecord<String, OrderEvent> record =
            KafkaTestUtils.getSingleRecord(kafkaTemplate.consumerFactory().getConsumer(), "order-events");
        assertThat(record.value().getOrderId()).isEqualTo("123");
    }
}
```

### Integration Testing a Consumer

```java
@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = { "order-events" })
class OrderEventConsumerTest {

    @Autowired
    private KafkaTemplate<String, OrderEvent> kafkaTemplate;

    @SpyBean
    private OrderEventConsumer consumer;

    @Test
    void shouldProcessEvent() {
        OrderEvent event = new OrderEvent("123", "cust1", BigDecimal.TEN);
        
        kafkaTemplate.send("order-events", event.getOrderId(), event);
        
        await().atMost(5, TimeUnit.SECONDS)
            .untilAsserted(() -> 
                verify(consumer, times(1)).handleOrderCreated(any()));
    }
}
```

## Monitoring and Observability

In production, you need to know what's happening. Integrate with Micrometer and expose metrics.

### Metrics Configuration

```yaml
spring:
  kafka:
    producer:
      properties:
        metrics.sample.window.ms: 30000
    consumer:
      properties:
        metrics.sample.window.ms: 30000
```

Spring Boot auto-configures Micrometer metrics for Kafka. Expose them via Actuator:

```bash
curl localhost:8080/actuator/metrics/kafka.producer.record.send.total
```

### Distributed Tracing

Use Spring Cloud Sleuth to trace events across services:

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-sleuth</artifactId>
</dependency>
```

Headers like `X-B3-TraceId` are automatically propagated through Kafka headers.

## Production Best Practices

1. **Use compacted topics for state**: If you need the latest state per key (e.g., customer profile), use log compaction.
2. **Partition count**: Start with more partitions than consumers. You can increase later but never decrease.
3. **Replication factor**: At least 3 for production to tolerate broker failures.
4. **Monitor consumer lag**: Use tools like Burrow or Kafka Lag Exporter to detect slow consumers.
5. **Graceful shutdown**: Implement `@PreDestroy` to close producers and consumers cleanly.
6. **Security**: Enable SSL and SASL authentication in production.

## Putting It All Together: A Real-World Example

Let's model a simple order processing pipeline:

1. **Order Service** publishes `OrderCreated` event
2. **Inventory Service** consumes, reserves stock, publishes `InventoryReserved` or `InventoryFailed`
3. **Payment Service** consumes `InventoryReserved`, processes payment, publishes `PaymentCompleted`
4. **Shipping Service** consumes `PaymentCompleted`, creates shipment

Each service is a separate Spring Boot application with its own Kafka producer/consumer. The event flow is asynchronous, resilient, and scalable.

```java
// Inventory Service Consumer
@Component
public class InventoryConsumer {

    @KafkaListener(topics = "order-events")
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            reserveStock(event.getProductId(), event.getQuantity());
            inventoryEventProducer.publishInventoryReserved(
                new InventoryReservedEvent(event.getOrderId()));
        } catch (OutOfStockException e) {
            inventoryEventProducer.publishInventoryFailed(
                new InventoryFailedEvent(event.getOrderId(), "Out of stock"));
        }
    }
}
```

This pattern allows each service to scale independently. If the inventory service is down, orders are still accepted—they'll be processed when inventory comes back online.

## Key Takeaways

- **Event-driven architecture decouples services** and improves resilience, scalability, and auditability
- **Spring Boot + Kafka** provides an ergonomic stack with `@KafkaListener`, `KafkaTemplate`, and auto-configuration
- **Always handle errors gracefully**: Use retries, dead letter topics, and manual acknowledgment for production systems
- **Schema management with Avro and Schema Registry** prevents breaking changes and ensures compatibility
- **Consumers must be idempotent** to handle at-least-once delivery semantics
- **Test with `@EmbeddedKafka`** to validate producer/consumer behavior without external dependencies
- **Monitor consumer lag and metrics** in production to detect issues early

Event-driven architecture isn't just a buzzword—it's a proven pattern for building systems that can grow with your business. With Kafka and Spring Boot, you have all the tools you need to implement it successfully. Start small, validate your event schemas early, and iterate.