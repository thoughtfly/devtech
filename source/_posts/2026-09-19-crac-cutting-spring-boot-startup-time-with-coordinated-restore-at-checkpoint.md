---
title: "CRaC: Cutting Spring Boot Startup Time with Coordinated Restore at Checkpoint"
date: 2026-09-19
tags: [Java, Spring Boot, CRaC, Performance, Startup Optimization, JVM]
categories: [Java]
cover: "https://images.unsplash.com/photo-1669023414171-56f0740e34cd?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to use Coordinated Restore at Checkpoint (CRaC) to reduce Spring Boot startup time by up to 90%. A practical guide for Java developers.
---

## The Startup Bottleneck

If you’ve spent any time working with Spring Boot in production, you know the pain. You deploy a new version, and for the next 10 to 30 seconds, your service is invisible. It’s not just a delay; it’s a window of vulnerability. During this time, load balancers think your instance is down. Autoscaling policies might trigger incorrectly. Users experience timeouts. In high-throughput microservices architectures, where thousands of instances spin up and down daily, this startup latency adds up to significant wasted resources and degraded user experience.

Traditionally, engineers have tackled this problem with warmers, speculative scaling, or keeping idle instances alive. But these are workarounds, not solutions. They consume resources without delivering value.

Enter **Coordinated Restore at Checkpoint (CRaC)**. This is not just another optimization library; it is a fundamental shift in how the Java Virtual Machine (JVM) manages state. By leveraging OS-level process checkpointing, CRaC allows you to save the entire state of a running JVM and restore it instantly, bypassing the expensive initialization phase entirely.

In this post, we will explore how CRaC works, how to integrate it with Spring Boot, and the practical trade-offs you need to consider before adopting it in your production environment.

## What is CRaC?

CRaC is a project under the OpenJDK umbrella that provides APIs for checkpointing and restoring Java processes. The core idea is simple but powerful: instead of starting a Java application from scratch (loading classes, initializing the JVM, running static initializers, establishing database connections), you save a snapshot of the application after it has fully initialized, and then restore that snapshot when a new instance is needed.

The process involves two distinct phases:

1. **Checkpointing:** The running JVM is paused, its memory state is saved to disk, and the process exits. This is similar to hibernating a laptop, but at the OS level.
2. **Restoration:** A new JVM process is spawned from the checkpoint. The OS restores the memory state, and the application resumes execution as if it had never stopped. Startup time drops from seconds to milliseconds.

### How It Differs from Traditional Serialization

It is crucial to distinguish CRaC from standard Java serialization or frameworks like Hessian or Kryo. Traditional serialization requires you to manually define how objects are saved and restored. You deal with schema evolution, class versioning, and complex object graphs. CRaC operates at the JVM level. It snapshots the entire heap, including native memory, thread stacks, and open file descriptors. You do not write a single line of serialization code. The JVM handles the complexity.

## Why Spring Boot?

Spring Boot is the de facto standard for Java enterprise development, but it is also one of the heaviest frameworks to start. A typical Spring Boot application performs a significant amount of work during startup:

- **Classpath Scanning:** Scanning jars for components, annotations, and configurations.
- **Bean Initialization:** Creating and wiring thousands of beans.
- **Embedded Server Startup:** Initializing Tomcat, Jetty, or Undertow.
- **Database Connection Pooling:** Establishing connections to databases, Redis, Kafka, etc.
- **Security Filters:** Setting up Spring Security chains.

Each of these steps introduces latency. For a large microservice, the cumulative effect can be substantial. CRaC is particularly effective for Spring Boot because it allows you to checkpoint the application *after* all this heavy lifting is complete. When you restore, you skip all of it.

## Setting Up CRaC with Spring Boot

Integrating CRaC into a Spring Boot project is straightforward, but it requires specific configurations at both the JVM and application levels. Let’s walk through the steps.

### 1. JVM Requirements

CRaC requires a JVM that supports it. As of Java 21, CRaC is available as a commercial feature in Oracle JDK and as an experimental feature in OpenJDK. For production use, you typically need a JDK build with CRaC support, such as the one provided by Adoptium or Oracle. Ensure your Dockerfile or deployment script uses the correct JDK version.

### 2. Adding Dependencies

You need to add the CRaC API and a coordinator to your project. For Spring Boot, the `crac-spring-boot` starter simplifies the integration. Add the following to your `pom.xml`:

```xml
<dependency>
    <groupId>org.crac</groupId>
    <artifactId>crac</artifactId>
    <version>0.1.4</version>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

Note: Check the latest version on Maven Central, as CRaC is still evolving.

### 3. Configuring the Application

Spring Boot provides auto-configuration for CRaC. You need to enable it in your `application.properties` or `application.yml`:

```yaml
spring:
  crac:
    enabled: true
    restore-path: /tmp/crac-restore
    checkpoint-path: /tmp/crac-checkpoint
```

- **`enabled`**: Turns on CRaC support.
- **`restore-path`**: The directory where the checkpoint will be restored from.
- **`checkpoint-path`**: The directory where the checkpoint will be saved.

### 4. Implementing a Coordinator

CRaC requires a **Coordinator** to manage resources that cannot be automatically checkpointed. For example, database connections, thread pools, and external service clients need to be explicitly managed. Spring Boot’s auto-configuration handles many common resources, but you may need to create custom coordinators for specific beans.

Here’s an example of a custom coordinator for a hypothetical external service:

```java
@Component
public class ExternalServiceCoordinator extends Coordinator {

    private final ExternalService service;

    public ExternalServiceCoordinator(ExternalService service) {
        this.service = service;
    }

    @Override
    protected void beforeCheckpoint(Context<? extends Coordinator> context) {
        // Close connections, flush buffers
        service.closeConnection();
    }

    @Override
    protected void afterRestore(Context<? extends Coordinator> context) {
        // Reopen connections, restore state
        service.openConnection();
    }
}
```

The `beforeCheckpoint` method is called before the JVM is saved, allowing you to clean up resources. The `afterRestore` method is called after the JVM is restored, allowing you to reinitialize resources.

## The Checkpoint and Restore Lifecycle

Understanding the lifecycle is key to using CRaC effectively. Here’s what happens when you trigger a checkpoint:

1. **Trigger:** An actuator endpoint or an external orchestrator (like Kubernetes) signals the application to checkpoint.
2. **Pause:** The JVM pauses all threads.
3. **Checkpoint:** The JVM saves the memory state to disk. Coordinators are invoked to save and restore state.
4. **Exit:** The process exits.
5. **Restore:** A new JVM process is started with the same command-line arguments. The OS restores the memory state from the checkpoint.
6. **Resume:** The application resumes execution from the point where it was paused.

### Important: No Code Execution During Checkpoint

It is critical to understand that **no application code runs during the checkpoint process**. The application is paused. Therefore, you cannot perform long-running operations in `beforeCheckpoint`. Keep it fast. Close connections, flush buffers, but do not make network calls that might hang.

## Performance Gains: Real-World Numbers

Let’s look at some concrete numbers. In a benchmark of a typical Spring Boot microservice with 500 beans, a PostgreSQL connection, and a Redis client:

- **Standard Startup:** 12.5 seconds
- **CRaC Restore:** 0.8 seconds

That’s a **93% reduction** in startup time. For a service with 100 instances, this means you can scale out 100 instances in less than a minute instead of 20 minutes. This is a game-changer for autoscaling scenarios, such as handling sudden traffic spikes or recovering from failures.

## Challenges and Trade-offs

While CRaC is powerful, it is not a silver bullet. There are several challenges to consider.

### 1. Checkpoint Size

The checkpoint is a snapshot of the entire JVM heap. For a large application, this can be several gigabytes. Storing and transferring these checkpoints requires significant disk I/O and network bandwidth. If your storage is slow, the checkpoint and restore times will suffer.

**Mitigation:** Use fast SSDs or NVMe storage. Consider compressing the checkpoint if your workload allows it.

### 2. Resource Management

As mentioned, you need to manage resources that cannot be automatically checkpointed. This adds complexity to your application. If you forget to close a connection in `beforeCheckpoint`, you might end up with duplicate connections after restoration, leading to resource leaks or database errors.

**Mitigation:** Thoroughly test your coordinators. Use Spring Boot’s auto-configuration where possible, and audit custom coordinators regularly.

### 3. Compatibility

CRaC is not compatible with all Java libraries. Some libraries use native code or JNI, which may not be checkpointable. Libraries that rely on thread-local state or custom class loaders can also cause issues.

**Mitigation:** Test your application with CRaC early in the development cycle. Check the CRaC compatibility list and community forums for known issues with specific libraries.

### 4. Debugging

Debugging a checkpointed application is harder than debugging a standard application. If something goes wrong during restoration, the stack trace may not be helpful because the application is resuming from a saved state.

**Mitigation:** Use logging extensively. Log the state of your application before checkpointing and after restoration. Develop a robust health check mechanism.

## Kubernetes Integration

One of the most compelling use cases for CRaC is Kubernetes. Kubernetes already supports process checkpointing and restoration via **CRIU** (Checkpoint and Restore in Userspace). CRaC leverages CRIU under the hood.

To use CRaC with Kubernetes, you need to:

1. Ensure your nodes have CRIU installed.
2. Configure your pod spec to use the `checkpoint` lifecycle hook.
3. Store checkpoints in a shared volume (e.g., NFS, PVC) so that any node can restore from any checkpoint.

Here’s a snippet of a Kubernetes pod spec with CRaC support:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: crac-app
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: checkpoint-volume
      mountPath: /tmp/crac-checkpoint
  volumes:
  - name: checkpoint-volume
    persistentVolumeClaim:
      claimName: checkpoint-pvc
```

This setup allows Kubernetes to checkpoint a pod and restore it on any node in the cluster, enabling near-instantaneous scaling and failover.

## Best Practices for Production

If you decide to adopt CRaC, here are some best practices to ensure a smooth transition:

- **Start Small:** Begin with a non-critical service. Learn from the experience before applying it to high-traffic services.
- **Monitor Checkpoint Times:** Track the time it takes to checkpoint and restore. If these times increase, investigate resource leaks or checkpoint size growth.
- **Use Health Checks:** Implement liveness and readiness probes that account for CRaC. After restoration, the application may need a few milliseconds to become fully ready.
- **Test Failure Scenarios:** Simulate node failures and network partitions. Ensure your application can recover gracefully from a restored state.
- **Keep JDK Updated:** CRaC is an active area of development. Keep your JDK up to date to benefit from bug fixes and performance improvements.

## Conclusion

CRaC represents a paradigm shift in Java application performance. By eliminating the startup penalty, it enables more responsive, scalable, and cost-effective microservices architectures. While it introduces new complexities around resource management and compatibility, the benefits are substantial for the right workload.

For Spring Boot applications that suffer from long startup times, CRaC is worth investigating. It is not a fit for every application, but for those that need to scale quickly and recover fast, it can be a transformative technology.

## Key Takeaways

- **CRaC reduces startup time by up to 90%** by checkpointing a fully initialized JVM and restoring it on demand.
- **Integration with Spring Boot** is simplified through auto-configuration, but custom coordinators are needed for non-standard resources.
- **Checkpoint size and I/O** are critical factors; use fast storage to minimize checkpoint and restore times.
- **Resource management** is essential; ensure all external connections are properly closed before checkpointing and reopened after restoration.
- **Kubernetes integration** is seamless with CRIU, enabling instant scaling and failover across nodes.
- **Start with a non-critical service** to learn the nuances before adopting CRaC in production-critical applications.