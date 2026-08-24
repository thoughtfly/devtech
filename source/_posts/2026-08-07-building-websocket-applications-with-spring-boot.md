---
title: "Building Real-Time WebSocket Applications with Spring Boot: A Practical Guide"
date: 2026-08-07
tags: [Spring Boot, WebSocket, STOMP, Real-Time, Java]
categories: [Java]
cover: "https://images.unsplash.com/photo-1546367564-ade1880f8921?w=1200&q=80&fit=crop&fm=webp"
description: Learn to build real-time WebSocket apps with Spring Boot. Covers STOMP, SockJS, message handling, security, and scaling. Includes code examples.
---

## Introduction

In the modern web, users expect real-time interactions: live chat, stock tickers, collaborative editing, and multiplayer games. Traditional HTTP request-response is insufficient for such scenarios, as it requires the client to poll the server repeatedly, leading to latency and inefficiency. WebSockets provide a full-duplex communication channel over a single TCP connection, enabling the server to push data to the client instantly.

Spring Boot, with its `spring-boot-starter-websocket` module, simplifies building WebSocket applications. In this guide, we'll build a feature-rich chat application using Spring Boot, STOMP (Simple Text Oriented Messaging Protocol), and SockJS. We'll cover configuration, message handling, security, and scaling considerations, with practical code examples you can adapt to your own projects.

## Understanding WebSockets and STOMP

WebSocket is a low-level protocol that provides a persistent connection between client and server. However, raw WebSocket messages are just bytes—you need a sub-protocol to define message formats and routing semantics. STOMP is a simple, text-based messaging protocol that works over WebSocket. It defines commands like `CONNECT`, `SEND`, `SUBSCRIBE`, and `MESSAGE`, along with headers and a body. Spring's WebSocket support uses STOMP to provide a message broker that routes messages between clients and server-side handlers.

SockJS is a fallback library that emulates WebSocket behavior when the browser doesn't support it (e.g., older browsers or restrictive proxies). It offers several transport options, such as XHR streaming, JSON-P polling, and iframe. Spring Boot integrates seamlessly with SockJS.

## Setting Up the Project

To get started, create a Spring Boot project with the WebSocket dependency. If you're using Maven, add the following to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>
```

We'll also need the `spring-boot-starter-security` for authentication later, and `spring-boot-starter-thymeleaf` for serving a simple UI (optional).

## Configuring WebSocket Endpoints

First, we need to configure Spring to handle WebSocket connections. Create a configuration class that implements `WebSocketMessageBrokerConfigurer`.

```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Enable a simple in-memory broker for messages sent to /topic and /queue
        config.enableSimpleBroker("/topic", "/queue");
        // Prefix for messages bound for @MessageMapping methods
        config.setApplicationDestinationPrefixes("/app");
        // Prefix for user-specific messages
        config.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // The endpoint for WebSocket connections, with SockJS fallback
        registry.addEndpoint("/ws").withSockJS();
    }
}
```

- `enableSimpleBroker` sets up an in-memory broker that handles messages sent to destinations prefixed with `/topic` (broadcast) and `/queue` (point-to-point).
- `setApplicationDestinationPrefixes` defines the prefix for messages that are routed to `@MessageMapping` methods in controllers.
- `setUserDestinationPrefix` allows sending messages to a specific user via `/user/{username}`.
- The endpoint `/ws` is the URL the client connects to. We enable SockJS for fallback.

## Creating a Message Model

Define a simple POJO to represent chat messages.

```java
public class ChatMessage {
    private String from;
    private String text;
    private String recipient;

    // Constructors, getters, and setters
}
```

## Building the Message Controller

Now, create a controller with `@MessageMapping` methods to handle incoming messages.

```java
@Controller
public class ChatController {

    private final SimpMessagingTemplate messagingTemplate;

    public ChatController(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    // Broadcast to all users subscribed to /topic/public
    @MessageMapping("/chat")
    @SendTo("/topic/public")
    public ChatMessage sendMessage(ChatMessage message) {
        return message;
    }

    // Send a private message to a specific user
    @MessageMapping("/private")
    public void sendPrivate(ChatMessage message) {
        messagingTemplate.convertAndSendToUser(
            message.getRecipient(), "/queue/private", message);
    }
}
```

- `@SendTo` automatically sends the return value to the specified destination (broadcast).
- For private messages, we use `SimpMessagingTemplate.convertAndSendToUser` which routes to `/user/{recipient}/queue/private`. The client must subscribe to `/user/queue/private` (with the user prefix).

## Client-Side JavaScript

On the client side, we use the `sockjs-client` and `stompjs` libraries. Here's a simple HTML/JS snippet:

```html
<script src="https://cdn.jsdelivr.net/npm/sockjs-client@1/dist/sockjs.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/stompjs@2.3.3/lib/stomp.min.js"></script>
```

```javascript
const socket = new SockJS('/ws');
const stompClient = Stomp.over(socket);

stompClient.connect({}, function(frame) {
    console.log('Connected: ' + frame);

    // Subscribe to public topic
    stompClient.subscribe('/topic/public', function(message) {
        showMessage(JSON.parse(message.body));
    });

    // Subscribe to private queue (requires authentication)
    stompClient.subscribe('/user/queue/private', function(message) {
        showPrivateMessage(JSON.parse(message.body));
    });
});

function sendMessage() {
    const message = {
        from: document.getElementById('from').value,
        text: document.getElementById('text').value
    };
    stompClient.send("/app/chat", {}, JSON.stringify(message));
}

function sendPrivate() {
    const message = {
        from: document.getElementById('from').value,
        recipient: document.getElementById('recipient').value,
        text: document.getElementById('text').value
    };
    stompClient.send("/app/private", {}, JSON.stringify(message));
}
```

Note: The `/user` prefix in the subscription is handled by Spring; the client subscribes to `/user/queue/private` and Spring resolves it to the specific user's queue based on the authenticated principal.

## Handling User Authentication

For private messages, we need to identify the user. Spring Security integrates well with WebSockets. Let's add security configuration.

First, add the security dependency:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

Create a security configuration class:

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable()) // For simplicity; consider CSRF for production
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/ws/**").permitAll() // Allow WebSocket handshake
                .anyRequest().authenticated()
            )
            .formLogin(); // Simple form login for demo
        return http.build();
    }
}
```

Then, in the WebSocket configuration, add authentication to the handshake. Spring Security automatically propagates the `Principal` to the WebSocket session if the user is authenticated (e.g., via session). To ensure the user is authenticated, you can add an interceptor:

```java
@Override
public void configureClientInboundChannel(ChannelRegistration registration) {
    registration.interceptors(new ChannelInterceptor() {
        @Override
        public Message<?> preSend(Message<?> message, MessageChannel channel) {
            StompHeaderAccessor accessor = StompHeaderAccessor.wrap(message);
            if (StompCommand.CONNECT.equals(accessor.getCommand())) {
                // Custom authentication logic here
                // For example, validate token and set user
            }
            return message;
        }
    });
}
```

For a real application, you might use a token-based authentication (e.g., JWT) passed in the STOMP headers. Spring Security's `WebSocketAuthenticationManager` can be customized.

## Broadcasting System Events

You can also send messages from the server to clients without a client request. For example, when a user joins, you can broadcast a system notification. Use `SimpMessagingTemplate` anywhere in your application, like a service or event listener.

```java
@Service
public class UserPresenceService {

    private final SimpMessagingTemplate messagingTemplate;

    public UserPresenceService(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void userJoined(String username) {
        ChatMessage message = new ChatMessage("system", username + " has joined", null);
        messagingTemplate.convertAndSend("/topic/public", message);
    }
}
```

## Error Handling and Heartbeats

STOMP supports error frames and heartbeats. Spring automatically sends heartbeats to keep the connection alive. You can customize the heartbeat interval in the STOMP client, but the server-side is configured via the broker. For the simple broker, you can set heartbeat values:

```java
config.enableSimpleBroker("/topic", "/queue")
    .setHeartbeatValue(new long[] {10000, 10000});
```

To handle errors globally, you can add a `@MessageExceptionHandler` in a controller:

```java
@MessageExceptionHandler
@SendTo("/topic/errors")
public String handleException(Exception e) {
    return e.getMessage();
}
```

## Scaling WebSockets with a Message Broker

The simple in-memory broker works for a single instance, but it doesn't support multi-node deployment. For horizontal scaling, you need a full-featured broker like RabbitMQ or Apache ActiveMQ Artemis. Spring Boot supports these via `spring-boot-starter-reactor-netty` and `spring-messaging`. Here's an example with RabbitMQ:

```yaml
spring:
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
```

And configure the broker:

```java
@Override
public void configureMessageBroker(MessageBrokerRegistry config) {
    config.enableStompBrokerRelay("/topic", "/queue")
        .setRelayHost("localhost")
        .setRelayPort(61613)
        .setClientLogin("guest")
        .setClientPasscode("guest");
    config.setApplicationDestinationPrefixes("/app");
}
```

This uses the STOMP protocol to connect to the external broker, which then handles message routing and fan-out across instances. Your application instances can connect to the same broker, allowing messages to be sent from one instance to clients connected to another.

## Testing WebSocket Endpoints

Spring Boot provides `spring-boot-starter-test` with WebSocket testing support. You can use `WebSocketStompClient` to connect and send/receive messages in a test.

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class ChatControllerTest {

    @Autowired
    private WebSocketStompClient stompClient;

    @Test
    public void testPublicChat() throws Exception {
        // Connect to the WebSocket endpoint
        StompSession session = stompClient.connect("ws://localhost:{port}/ws", new StompSessionHandlerAdapter() {})
            .get(1, TimeUnit.SECONDS);

        // Subscribe to the topic
        session.subscribe("/topic/public", new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return ChatMessage.class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                // Assert the message
            }
        });

        // Send a message
        ChatMessage message = new ChatMessage("user1", "hello", null);
        session.send("/app/chat", message);

        // Wait for the response
        Thread.sleep(1000);
    }
}
```

You'll need to configure the `WebSocketStompClient` bean in your test configuration.

## Best Practices and Pitfalls

- **Connection Limits**: WebSocket connections are long-lived; monitor server resources. Use connection limits and idle timeouts.
- **Security**: Always authenticate WebSocket connections. Never trust client-provided usernames for routing; derive from the session.
- **Session Management**: Track user sessions to handle disconnections and clean up resources. Use `SessionConnectedEvent` and `SessionDisconnectEvent` listeners.
- **Message Size**: Set a reasonable limit on message size to prevent memory issues (e.g., in Spring Boot properties).
- **Backpressure**: If the client is slow, the server may buffer messages. Consider using a reliable broker with message persistence.

## Conclusion

WebSockets with Spring Boot provide a robust foundation for real-time features. By leveraging STOMP and SockJS, you get a standardized messaging framework with fallback support. With security integration and scalable broker options, you can build production-grade applications. The key is to understand the message flow and choose the right broker for your scale.

## Key Takeaways

- **WebSocket + STOMP**: Use STOMP for a structured messaging protocol over WebSocket; Spring Boot's `@EnableWebSocketMessageBroker` simplifies setup.
- **Configuration**: Define broker destinations (`/topic`, `/queue`) and application prefixes (`/app`) to route messages correctly.
- **Server-Side**: Use `@MessageMapping` controllers and `SimpMessagingTemplate` for broadcasting and point-to-point messaging.
- **Client-Side**: Integrate SockJS and STOMP libraries; subscribe to `/user/queue` for private messages.
- **Security**: Authenticate users via Spring Security; customize the WebSocket channel for token-based auth.
- **Scaling**: Replace the simple broker with a STOMP relay (RabbitMQ/Artemis) for multi-instance deployments.
- **Testing**: Use `WebSocketStompClient` for integration tests to verify message flow.
- **Operational Care**: Monitor connection limits, set message size limits, and handle session lifecycle events.