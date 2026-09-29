---
title: "Building gRPC Services with Java and Spring Boot"
date: 2026-09-29
tags: [gRPC, Java, Spring Boot, Microservices, Protocol Buffers, Backend Development]
categories: [Java]
cover: "https://images.unsplash.com/photo-1687603921109-46401b201195?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to build high-performance gRPC microservices using Java, Spring Boot, and Protocol Buffers with practical examples.
---

## Building gRPC Services with Java and Spring Boot

In the world of modern microservices, communication efficiency is everything. While REST has been the default choice for API development for over a decade, it often falls short when it comes to performance-critical systems. Enter gRPC, a high-performance, open-source universal RPC framework that has become a favorite among engineering teams building scalable distributed systems.

If you are a Java developer looking to leverage the power of gRPC within your Spring Boot applications, you are in the right place. This guide will walk you through building production-ready gRPC services using Java and Spring Boot, covering everything from Protocol Buffers definition to server implementation and client integration.

## Why Choose gRPC Over REST?

Before diving into implementation, it is essential to understand why gRPC deserves a place in your architecture. REST APIs typically use JSON for data serialization, which is human-readable but verbose. In contrast, gRPC uses Protocol Buffers (protobuf), a binary serialization format that is significantly smaller and faster to parse.

The performance gains are substantial. gRPC leverages HTTP/2 for transport, enabling features like multiplexing, flow control, and header compression. This means you can handle thousands of concurrent connections more efficiently than with traditional HTTP/1.1 based REST services.

Additionally, gRPC provides strong typing through your .proto definitions. This eliminates the ambiguity often found in REST APIs and generates type-safe client and server code automatically. For Java developers, this means fewer runtime errors and a smoother development experience.

## Setting Up Your Project

Let us start by creating a Spring Boot project with the necessary dependencies. We will use Maven for this example, but Gradle users can adapt the configuration easily.

First, ensure you have Spring Boot 3.x installed. We will need the grpc-spring-boot-starter library, which provides auto-configuration for gRPC services in Spring Boot applications.

Here is a sample pom.xml configuration:

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>net.devh</groupId>
        <artifactId>grpc-spring-boot-starter</artifactId>
        <version>3.1.0.RELEASE</version>
    </dependency>
    <dependency>
        <groupId>javax.annotation</groupId>
        <artifactId>javax.annotation-api</artifactId>
        <version>1.3.2</version>
    </dependency>
</dependencies>
```

Note that we are using the grpc-spring-boot-starter from the devh.net project, which is the most popular and well-maintained library for integrating gRPC with Spring Boot. It handles the complexity of gRPC server initialization, service registration, and health checks automatically.

## Defining Your API with Protocol Buffers

The foundation of any gRPC service is the .proto file. This file defines your service interface, message types, and RPC methods. Let us create a simple example: a UserService that allows clients to retrieve user information.

Create a file named user_service.proto in your resources directory:

```protobuf
syntax = "proto3";

option java_package = "com.example.grpc";
option java_outer_classname = "UserServiceProto";
option java_multiple_files = true;

service UserService {
    rpc GetUser (GetUserRequest) returns (GetUserResponse) {}
    rpc ListUsers (ListUsersRequest) returns (stream User) {}
}

message GetUserRequest {
    string user_id = 1;
}

message GetUserResponse {
    string id = 1;
    string name = 2;
    string email = 3;
}

message ListUsersRequest {
    int32 page_size = 1;
    string page_token = 2;
}

message User {
    string id = 1;
    string name = 2;
    string email = 3;
}
```

Let us break down what is happening here. The syntax directive specifies Protocol Buffers version 3. The java_package and java_outer_classname options control how the generated Java code will be organized. Setting java_multiple_files to true generates separate Java files for each message type, which is generally preferred for maintainability.

The service definition declares two RPC methods. GetUser is a simple unary RPC that takes a request and returns a single response. ListUsers is a server-side streaming RPC, meaning the server can send multiple responses back to the client over the same connection.

## Generating Java Code from Protobuf

Once you have defined your .proto file, you need to generate the Java code. There are several ways to do this, but the most common approach is using the protobuf-maven-plugin or protobuf-gradle-plugin.

Add the following plugin configuration to your pom.xml:

```xml
<build>
    <extensions>
        <extension>
            <groupId>kr.motd.maven</groupId>
            <artifactId>os-maven-plugin</artifactId>
            <version>1.7.1</version>
        </extension>
    </extensions>
    <plugins>
        <plugin>
            <groupId>org.xolstice.maven.plugins</groupId>
            <artifactId>protobuf-maven-plugin</artifactId>
            <version>0.6.1</version>
            <configuration>
                <protocArtifact>com.google.protobuf:protoc:3.25.1:exe:${os.detected.classifier}</protocArtifact>
                <pluginId>grpc-java</pluginId>
                <pluginArtifact>io.grpc:protoc-gen-grpc-java:1.60.0:exe:${os.detected.classifier}</pluginArtifact>
            </configuration>
            <executions>
                <execution>
                    <goals>
                        <goal>compile</goal>
                        <goal>compile-custom</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

When you run mvn compile, the plugin will generate Java classes for your messages and a stub class for your service. These generated classes are the backbone of your gRPC implementation.

## Implementing the gRPC Service

Now that we have our generated code, let us implement the actual service logic. Create a class that extends your generated service base class and annotate it with @GrpcService.

```java
package com.example.grpc;

import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@GrpcService
public class UserServiceImpl extends UserServiceGrpc.UserServiceImplBase {

    private static final Logger log = LoggerFactory.getLogger(UserServiceImpl.class);
    
    private final Map<String, User> userStore = new ConcurrentHashMap<>();

    public UserServiceImpl() {
        // Initialize with some sample data
        userStore.put("1", User.newBuilder()
            .setId("1")
            .setName("Alice Johnson")
            .setEmail("alice@example.com")
            .build());
        userStore.put("2", User.newBuilder()
            .setId("2")
            .setName("Bob Smith")
            .setEmail("bob@example.com")
            .build());
    }

    @Override
    public void getUser(GetUserRequest request, StreamObserver GetUserResponse> responseObserver) {
        String userId = request.getUserId();
        log.info("Received request for user: {}", userId);
        
        User user = userStore.get(userId);
        if (user == null) {
            responseObserver.onError(new RuntimeException("User not found: " + userId));
        } else {
            GetUserResponse response = GetUserResponse.newBuilder()
                .setId(user.getId())
                .setName(user.getName())
                .setEmail(user.getEmail())
                .build();
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }

    @Override
    public void listUsers(ListUsersRequest request, StreamObserver User> responseObserver) {
        log.info("Received request to list users with page size: {}", request.getPageSize());
        
        List Users> users = new ArrayList<>(userStore.values());
        int pageSize = request.getPageSize() > 0 ? request.getPageSize() : users.size();
        
        for (int i = 0; i < Math.min(pageSize, users.size()); i++) {
            responseObserver.onNext(users.get(i));
        }
        
        responseObserver.onCompleted();
    }
}
```

Notice the use of @GrpcService annotation. This tells Spring Boot to register this class as a gRPC service. The class extends UserServiceImplBase, which is generated from your proto file and provides the skeleton implementation for your RPC methods.

Each RPC method receives a StreamObserver as the second parameter. This observer is used to send responses back to the client. For unary RPCs like GetUser, you call onNext with your response and then onCompleted. For streaming RPCs like ListUsers, you can call onNext multiple times before calling onCompleted.

## Configuring gRPC Server Properties

Spring Boot provides several properties to configure your gRPC server. Add these to your application.properties file:

```properties
# gRPC Server Configuration
grpc.server.port=9090
grpc.server.max-inbound-message-size=4194304
grpc.server.max-outbound-message-size=4194304

# Enable gRPC health checking
grpc.server.health.enabled=true

# Logging
logging.level.io.grpc=INFO
logging.level.com.example.grpc=DEBUG
```

The max-inbound-message-size and max-outbound-message-size properties control the maximum message sizes your server will accept or send. Setting these appropriately is important for preventing abuse and managing resource usage.

## Creating a gRPC Client

While the server implementation is important, you also need to know how to call gRPC services from other Java applications. Spring Boot makes this straightforward with the grpc-spring-boot-starter client support.

Add the client starter to your pom.xml:

```xml
<dependency>
    <groupId>net.devh</groupId>
    <artifactId>grpc-client-spring-boot-starter</artifactId>
    <version>3.1.0.RELEASE</version>
</dependency>
```

Then configure your client in application.properties:

```properties
grpc.client.user-service.name=user-service
grpc.client.user-service.address=static://localhost:9090
grpc.client.user-service.negotiation-type=plaintext
```

Now you can inject and use the gRPC client in your services:

```java
package com.example.client;

import com.example.grpc.GetUserRequest;
import com.example.grpc.GetUserResponse;
import com.example.grpc.ListUsersRequest;
import com.example.grpc.UserServiceGrpc;
import io.grpc.stub.StreamObserver;
import org.springframework.stereotype.Service;

@Service
public class UserGrpcClientService {

    private final UserServiceGrpc.UserServiceBlockingStub blockingStub;
    private final UserServiceGrpc.UserServiceStub asyncStub;

    public UserGrpcClientService(UserServiceGrpc.UserServiceBlockingStub blockingStub,
                                 UserServiceGrpc.UserServiceStub asyncStub) {
        this.blockingStub = blockingStub;
        this.asyncStub = asyncStub;
    }

    public GetUserResponse getUser(String userId) {
        GetUserRequest request = GetUserRequest.newBuilder()
            .setUserId(userId)
            .build();
        return blockingStub.getUser(request);
    }

    public void listUsersAsync(int pageSize) {
        ListUsersRequest request = ListUsersRequest.newBuilder()
            .setPageSize(pageSize)
            .build();
        
        asyncStub.listUsers(request, new StreamObserver User>() {
            @Override
            public void onNext(User user) {
                System.out.println("Received user: " + user.getName());
            }

            @Override
            public void onCompleted() {
                System.out.println("User listing completed");
            }

            @Override
            public void onError(Throwable t) {
                System.err.println("Error listing users: " + t.getMessage());
            }
        });
    }
}
```

The blocking stub is used for simple, synchronous calls, while the async stub allows you to make non-blocking requests with callbacks. Choose the appropriate stub based on your use case and threading model.

## Testing Your gRPC Service

Testing gRPC services is slightly different from testing REST endpoints. You can use the generated client stubs to test your server implementation directly, or you can use tools like grpcurl for command-line testing.

Here is a simple unit test using JUnit 5:

```java
package com.example.grpc;

import io.grpc.inprocess.InProcessServerBuilder;
import io.grpc.inprocess.InProcessChannelBuilder;
import io.grpc.testing.GrpcCleanupRule;
import org.junit.Rule;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

public class UserServiceImplTest {

    @Rule
    public final GrpcCleanupRule grpcCleanup = new GrpcCleanupRule();

    @Test
    public void getUser_returnsUserWhenFound() throws Exception {
        // Create in-process server and channel
        String serverName = InProcessServerBuilder.generateName();
        grpcCleanup.register(InProcessServerBuilder.forName(serverName)
            .directExecutor()
            .addService(new UserServiceImpl())
            .build()
            .start());

        io.grpc.Channel channel = grpcCleanup.register(
            InProcessChannelBuilder.forName(serverName).directExecutor().build());

        UserServiceGrpc.UserServiceBlockingStub stub = UserServiceGrpc.newBlockingStub(channel);

        // Test the service
        GetUserRequest request = GetUserRequest.newBuilder()
            .setUserId("1")
            .build();
        GetUserResponse response = stub.getUser(request);

        assertNotNull(response);
        assertEquals("1", response.getId());
        assertEquals("Alice Johnson", response.getName());
        assertEquals("alice@example.com", response.getEmail());
    }
}
```

The GrpcCleanupRule ensures that your server and channel are properly cleaned up after each test, preventing resource leaks.

## Handling Errors and Metadata

In production systems, proper error handling is crucial. gRPC uses status codes to indicate success or failure. You can throw StatusRuntimeException with appropriate status codes to communicate errors to clients.

```java
import io.grpc.Status;
import io.grpc.StatusRuntimeException;

// In your service method
if (userId == null || userId.isEmpty()) {
    throw new StatusRuntimeException(Status.INVALID_ARGUMENT.withDescription("User ID is required"));
}
```

You can also pass metadata between client and server using ServerCallStreamObserver and ClientCallStreamObserver. This is useful for adding custom headers, tracing information, or authentication tokens.

## Key Takeaways

- gRPC offers superior performance compared to REST for microservices communication, especially in high-throughput scenarios
- Protocol Buffers provide strong typing and efficient serialization, reducing payload size and parsing overhead
- The grpc-spring-boot-starter library simplifies integration of gRPC with Spring Boot applications
- Streaming RPCs enable efficient data transfer for large datasets and real-time updates
- Proper error handling with gRPC status codes ensures robust client-server communication
- In-process testing with GrpcCleanupRule makes unit testing gRPC services straightforward
- Configuration of message size limits and server properties is essential for production readiness

Building gRPC services with Java and Spring Boot is a powerful combination that delivers performance, type safety, and developer productivity. As your microservices architecture grows, gRPC will serve you well in handling the demands of modern distributed systems.