---
title: "Building a Coding Assistant Backend with Java and LLMs"
date: 2026-09-14
tags: [Java, Spring Boot, LLM, AI, Backend Development, API Design]
categories: [Java, AI Engineering]
cover: "https://images.unsplash.com/photo-1605379399642-870262d3d051?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to build a production-ready coding assistant backend using Java, Spring Boot, and LLMs. Includes architecture, code examples, and best practices.
---

## Building a Coding Assistant Backend with Java and LLMs

The landscape of developer tools is shifting dramatically. Coding assistants like GitHub Copilot, Amazon CodeWhisperer, and Cursor have fundamentally changed how we write, review, and debug code. But what happens when you need to build your own? Whether it’s for internal tooling, a niche language focus, or keeping sensitive code within your infrastructure, building a coding assistant backend with Java and Large Language Models (LLMs) is a powerful endeavor.

In this post, we’ll dive deep into the architecture, implementation, and best practices for creating a robust coding assistant backend using Java. We’ll cover everything from selecting the right LLM providers to handling streaming responses, managing context windows, and ensuring security.

### Why Java for LLM-Powered Applications?

You might wonder why choose Java when Python dominates the AI/ML space. The answer lies in enterprise requirements. Java offers:

- **Type Safety**: Critical for maintaining large codebases where LLM outputs interact with your application logic
- **Performance**: Modern Java (17+) with GraalVM and virtual threads provides excellent throughput
- **Ecosystem**: Rich libraries for HTTP clients, streaming, and enterprise integration
- **Scalability**: Battle-tested at scale in production environments
- **Tooling**: Superior IDE support, debugging, and monitoring capabilities

### Architecture Overview

A coding assistant backend needs to handle several key responsibilities:

1. **Request Processing**: Accept code snippets, questions, and context from users
2. **LLM Integration**: Communicate with LLM providers (OpenAI, Anthropic, etc.)
3. **Context Management**: Maintain conversation history and relevant code context
4. **Response Streaming**: Deliver real-time responses to users
5. **Security & Validation**: Sanitize inputs and outputs, manage API keys

Here’s a high-level architecture:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  Java Backend│────▶│   LLM API   │
│  (IDE/Web)  │◀────│  (Spring     │◀────│ (OpenAI/    │
│             │     │   Boot)      │     │  Anthropic) │
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Context     │
                     │  Store       │
                     │  (Redis/     │
                     │  In-Memory)  │
                     └──────────────┘
```

### Setting Up the Project

Let’s start with a Spring Boot project. We’ll use Maven for dependency management and include the necessary libraries for HTTP communication, streaming, and LLM integration.

```xml
<dependencies>
    <!-- Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- Spring WebFlux for reactive streaming -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
    
    <!-- OpenAI Java SDK -->
    <dependency>
        <groupId>com.theokanning.openai-gpt3-java</groupId>
        <artifactId>client</artifactId>
        <version>0.18.1</version>
    </dependency>
    
    <!-- Jackson for JSON processing -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
    </dependency>
    
    <!-- Lombok for boilerplate reduction -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

### Core Service: LLM Integration

The heart of our coding assistant is the LLM integration service. We need to handle different providers and support streaming responses for a better user experience.

```java
@Service
@RequiredArgsConstructor
public class LlmAssistantService {
    
    private final OpenAiApi openAiApi;
    private final ContextManager contextManager;
    private final LlmConfig llmConfig;
    
    /**
     * Process a coding request and return a streaming response
     */
    public Flux<ChatResponseChunk> streamCodingResponse(
            String userId,
            String codeContext,
            String userQuery,
            Language language) {
        
        // Build conversation history with context
        List<ChatCompletionMessage> messages = 
            contextManager.getMessages(userId);
        
        // Add system prompt for coding assistant
        messages.add(0, ChatCompletionMessage.builder()
            .role("system")
            .content(buildSystemPrompt(language))
            .build());
        
        // Add current code context if provided
        if (StringUtils.hasText(codeContext)) {
            messages.add(ChatCompletionMessage.builder()
                .role("user")
                .content("Here is the relevant code context:\n" + codeContext)
                .build());
        }
        
        // Add user query
        messages.add(ChatCompletionMessage.builder()
            .role("user")
            .content(userQuery)
            .build());
        
        // Create chat completion request
        ChatCompletionRequest request = ChatCompletionRequest.builder()
            .model(llmConfig.getModel())
            .messages(messages)
            .temperature(llmConfig.getTemperature())
            .maxTokens(llmConfig.getMaxTokens())
            .stream(true)
            .build();
        
        // Stream response
        return Flux.create(sink -> {
            openAiApi.createChatCompletion(request, 
                new ChatCompletionCallback() {
                    @Override
                    public void onData(String data) {
                        try {
                            ChatResponseChunk chunk = 
                                parseChunk(data);
                            sink.next(chunk);
                        } catch (Exception e) {
                            sink.error(e);
                        }
                    }
                    
                    @Override
                    public void onError(Exception e) {
                        sink.error(e);
                    }
                    
                    @Override
                    public void onCompleted() {
                        // Update context with new messages
                        contextManager.addMessages(userId, messages);
                        sink.complete();
                    }
                });
        });
    }
    
    private String buildSystemPrompt(Language language) {
        return String.format("""
            You are an expert Java developer assistant.
            Language: %s
            
            Guidelines:
            1. Provide clear, concise code explanations
            2. Follow best practices and design patterns
            3. Include comments for complex logic
            4. Suggest improvements when applicable
            5. Maintain security and performance considerations
            """, language);
    }
    
    private ChatResponseChunk parseChunk(String data) {
        // Parse SSE data and extract chunk
        // Implementation depends on LLM provider
        return new ChatResponseChunk(data);
    }
}
```

### Context Management

One of the most challenging aspects of building a coding assistant is managing context. LLMs have token limits, and we need to maintain conversation history while staying within those bounds.

```java
@Component
@RequiredArgsConstructor
public class ContextManager {
    
    private final RedisTemplate<String, String> redisTemplate;
    private static final int MAX_TOKENS = 4000;
    private static final String CONTEXT_KEY_PREFIX = "context:";
    
    /**
     * Get conversation history for a user
     */
    public List<ChatCompletionMessage> getMessages(String userId) {
        String key = CONTEXT_KEY_PREFIX + userId;
        String historyJson = redisTemplate.opsForValue().get(key);
        
        if (historyJson == null) {
            return new ArrayList<>();
        }
        
        return objectMapper.readValue(historyJson, 
            new TypeReference<List<ChatCompletionMessage>>() {});
    }
    
    /**
     * Add messages to conversation history
     */
    public void addMessages(String userId, 
                           List<ChatCompletionMessage> newMessages) {
        String key = CONTEXT_KEY_PREFIX + userId;
        List<ChatCompletionMessage> history = getMessages(userId);
        
        // Add new messages
        history.addAll(newMessages);
        
        // Trim to fit within token limit
        history = trimToTokenLimit(history, MAX_TOKENS);
        
        // Save back to Redis
        redisTemplate.opsForValue().set(key, 
            objectMapper.writeValueAsString(history),
            Duration.ofHours(2));
    }
    
    /**
     * Estimate tokens and trim history
     */
    private List<ChatCompletionMessage> trimToTokenLimit(
            List<ChatCompletionMessage> messages, 
            int maxTokens) {
        
        List<ChatCompletionMessage> trimmed = new ArrayList<>();
        int totalTokens = 0;
        
        // Start from the end to keep recent context
        for (int i = messages.size() - 1; i >= 0; i--) {
            ChatCompletionMessage msg = messages.get(i);
            int msgTokens = estimateTokens(msg.getContent());
            
            if (totalTokens + msgTokens <= maxTokens) {
                trimmed.add(0, msg); // Add to beginning to maintain order
                totalTokens += msgTokens;
            }
        }
        
        return trimmed;
    }
    
    private int estimateTokens(String text) {
        // Rough estimate: 1 token ≈ 4 characters
        return (int) Math.ceil((double) text.length() / 4);
    }
}
```

### REST Controller

Now let’s expose our service through a REST controller with streaming support.

```java
@RestController
@RequestMapping("/api/assistant")
@RequiredArgsConstructor
public class AssistantController {
    
    private final LlmAssistantService assistantService;
    private final ContextManager contextManager;
    
    /**
     * Stream coding assistance response
     */
    @PostMapping(value = "/chat/stream", 
                produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamChat(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody ChatRequest request) {
        
        return assistantService.streamCodingResponse(
                userId,
                request.getCodeContext(),
                request.getQuery(),
                request.getLanguage())
            .map(chunk -> ServerSentEvent.builder(chunk.getContent())
                .event("message")
                .build())
            .doOnComplete(() -> 
                log.info("Stream completed for user: {}", userId))
            .doOnError(error -> 
                log.error("Stream error for user: {}", userId, error));
    }
    
    /**
     * Get conversation history
     */
    @GetMapping("/history")
    public ResponseEntity<List<ChatCompletionMessage>> getHistory(
            @RequestHeader("X-User-Id") String userId) {
        return ResponseEntity.ok(
            contextManager.getMessages(userId));
    }
    
    /**
     * Clear conversation history
     */
    @DeleteMapping("/history")
    public ResponseEntity<Void> clearHistory(
            @RequestHeader("X-User-Id") String userId) {
        String key = "context:" + userId;
        redisTemplate.delete(key);
        return ResponseEntity.noContent().build();
    }
}
```

### Request and Response Models

Let’s define the data models for our API.

```java
@Data
@Builder
public class ChatRequest {
    private String query;
    private String codeContext;
    private Language language;
    private Integer maxTokens;
    private Double temperature;
}

@Data
@Builder
public class ChatResponseChunk {
    private String content;
    private Boolean isComplete;
    private Long finishReason;
}

@Data
@Builder
public class ChatCompletionMessage {
    private String role;
    private String content;
}

public enum Language {
    JAVA, PYTHON, TYPESCRIPT, KOTLIN, GO, RUST
}
```

### Security Considerations

When building a coding assistant, security is paramount. Here are key considerations:

1. **API Key Management**: Never hardcode API keys. Use environment variables or a secrets manager.

```yaml
# application.yml
llm:
  api-key: ${LLM_API_KEY}
  base-url: ${LLM_BASE_URL}
  model: gpt-4
  temperature: 0.3
  max-tokens: 2000
```

2. **Input Sanitization**: Validate and sanitize user inputs to prevent injection attacks.

```java
@Component
public class InputValidator {
    
    public void validateChatRequest(ChatRequest request) {
        if (request == null || StringUtils.isBlank(request.getQuery())) {
            throw new IllegalArgumentException("Query is required");
        }
        
        if (request.getQuery().length() > 10000) {
            throw new IllegalArgumentException("Query too long");
        }
        
        // Check for suspicious patterns
        if (containsMaliciousPattern(request.getQuery())) {
            throw new SecurityException("Invalid input detected");
        }
    }
    
    private boolean containsMaliciousPattern(String input) {
        // Implement pattern matching for injection attacks
        return false; // Simplified for example
    }
}
```

3. **Rate Limiting**: Protect your backend and LLM API from abuse.

```java
@Configuration
public class RateLimitConfig {
    
    @Bean
    public RateLimiter rateLimiter() {
        return RateLimiter.of("assistantApi", 
            RateLimiterConfig.custom()
                .limitForPeriod(100)
                .limitRefreshPeriod(Duration.ofMinutes(1))
                .timeoutDuration(Duration.ofSeconds(5))
                .build());
    }
}
```

### Performance Optimization

1. **Connection Pooling**: Configure HTTP client connection pooling for better performance.

```java
@Configuration
public class WebClientConfig {
    
    @Bean
    public WebClient webClient() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.SO_KEEPALIVE, true)
            .poolFactory(() -> new PoolingHttpClientConnectionManager());
        
        return WebClient.builder()
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }
}
```

2. **Caching**: Cache frequent responses to reduce LLM API calls.

```java
@Service
@RequiredArgsConstructor
public class CachingLlmService {
    
    private final LlmAssistantService llmService;
    private final CacheManager cacheManager;
    
    @Cacheable(value = "assistantResponses", key = "#userId + '#' + #query")
    public String getCachedResponse(String userId, String query) {
        // This would need to be adapted for streaming
        return llmService.getNonStreamingResponse(userId, query);
    }
}
```

### Testing Strategy

Testing an LLM-powered service requires a different approach. We need to test:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test with mock LLM responses
3. **Contract Tests**: Ensure API contracts are maintained

```java
@SpringBootTest
@ActiveProfiles("test")
class AssistantControllerTest {
    
    @Autowired
    private WebTestClient webTestClient;
    
    @MockBean
    private LlmAssistantService assistantService;
    
    @Test
    void shouldStreamCodingResponse() {
        // Arrange
        ChatResponseChunk chunk = ChatResponseChunk.builder()
            .content("Here's the solution:")
            .build();
        
        when(assistantService.streamCodingResponse(
            any(), any(), any(), any()))
            .thenReturn(Flux.just(chunk));
        
        // Act & Assert
        webTestClient.post()
            .uri("/api/assistant/chat/stream")
            .header("X-User-Id", "test-user")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(new ChatRequest("Fix this bug", null, JAVA))
            .accept(MediaType.TEXT_EVENT_STREAM)
            .exchange()
            .expectStatus().isOk()
            .expectBody()
            .jsonPath("$.data.content").isEqualTo("Here's the solution:");
    }
}
```

### Deployment Considerations

1. **Containerization**: Package your application with Docker for consistent deployments.

```dockerfile
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

2. **Health Checks**: Implement health checks for Kubernetes or container orchestration.

```java
@RestController
public class HealthController {
    
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        Map<String, String> status = Map.of(
            "status", "UP",
            "service", "coding-assistant"
        );
        return ResponseEntity.ok(status);
    }
}
```

3. **Monitoring**: Integrate with monitoring tools like Prometheus and Grafana.

```java
@Configuration
public class MonitoringConfig {
    
    @Bean
    public MeterRegistryCustomizer<MeterRegistry> metricsCommonTags() {
        return registry -> registry.config()
            .commonTags("application", "coding-assistant");
    }
}
```

### Key Takeaways

- **Architecture Matters**: Design your backend with clear separation of concerns between LLM integration, context management, and API layer
- **Streaming is Essential**: Use reactive programming with WebFlux for real-time responses that improve user experience
- **Context Management**: Implement smart token management to maintain conversation history within LLM limits
- **Security First**: Always validate inputs, manage API keys securely, and implement rate limiting
- **Testing Strategy**: Combine unit tests with mock-based integration tests for reliable coverage
- **Performance Optimization**: Use connection pooling, caching, and proper HTTP client configuration
- **Production Readiness**: Include health checks, monitoring, and containerization for smooth deployments

Building a coding assistant backend with Java and LLMs is challenging but rewarding. By following these patterns and best practices, you can create a robust, scalable, and secure service that enhances developer productivity. The key is to start with a solid architecture, iterate based on user feedback, and continuously improve your context management and response quality.