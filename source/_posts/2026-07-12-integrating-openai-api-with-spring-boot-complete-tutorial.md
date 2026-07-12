---
title: "Integrating OpenAI API with Spring Boot: Complete Tutorial"
date: 2026-07-12
tags: [OpenAI, Spring Boot, Java, API Integration, GPT]
categories: [Java]
cover:
description: Learn how to integrate OpenAI's GPT API with Spring Boot. Step-by-step guide with code examples, best practices, and error handling for production-ready apps.
---

# Integrating OpenAI API with Spring Boot: Complete Tutorial

Large language models like GPT-4 are transforming how we build intelligent applications. Whether you're adding chat capabilities, content generation, or code analysis, integrating OpenAI's API into a Spring Boot backend is a powerful combination. In this tutorial, I'll walk you through a production-ready integration, covering everything from setup to error handling and streaming responses.

## Why Spring Boot + OpenAI?

Spring Boot is the de facto standard for Java microservices. It provides mature tools for HTTP clients, configuration management, and resilience patterns. Pairing it with OpenAI's API lets you build scalable AI-powered features without managing infrastructure.

## Prerequisites

- Java 17+ (I'll use Java 21 features where appropriate)
- Spring Boot 3.x
- An OpenAI API key (sign up at [platform.openai.com](https://platform.openai.com))
- Basic familiarity with REST APIs and Spring Boot

## Step 1: Project Setup

Create a new Spring Boot project using [Spring Initializr](https://start.spring.io/) or your preferred method. Add these dependencies:

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
    <dependency>
        <groupId>com.theokanning.openai-gpt3-java</groupId>
        <artifactId>service</artifactId>
        <version>0.18.2</version>
    </dependency>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

I use `webflux` for non-blocking HTTP calls, which is essential for streaming responses. The `openai-gpt3-java` library is a well-maintained client, but we'll also build a custom client to understand the internals.

## Step 2: Configuration

Add your API key to `application.yml`:

```yaml
openai:
  api-key: ${OPENAI_API_KEY}
  model: gpt-4
  max-tokens: 2048
  temperature: 0.7

spring:
  jackson:
    property-naming-strategy: SNAKE_CASE
```

Create a configuration class:

```java
@Configuration
@ConfigurationProperties(prefix = "openai")
@Data
public class OpenAIConfig {
    private String apiKey;
    private String model;
    private int maxTokens;
    private double temperature;
}
```

**Pro tip**: Never hardcode API keys. Use environment variables or a vault like HashiCorp Vault.

## Step 3: Building the HTTP Client

We'll use Spring's `WebClient` for reactive HTTP calls. Create a bean:

```java
@Configuration
public class OpenAIClientConfig {

    @Bean
    public WebClient openAIWebClient(OpenAIConfig config) {
        return WebClient.builder()
                .baseUrl("https://api.openai.com/v1")
                .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + config.getApiKey())
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .build();
    }
}
```

## Step 4: Creating the Request/Response Models

OpenAI's chat completion endpoint expects a specific structure. Let's model it:

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatCompletionRequest {
    private String model;
    private List<Message> messages;
    private int maxTokens;
    private double temperature;
    private boolean stream;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Message {
    private String role; // "system", "user", "assistant"
    private String content;
}

@Data
public class ChatCompletionResponse {
    private String id;
    private String object;
    private long created;
    private String model;
    private List<Choice> choices;
    private Usage usage;
}

@Data
public class Choice {
    private int index;
    private Message message;
    private String finishReason;
}

@Data
public class Usage {
    private int promptTokens;
    private int completionTokens;
    private int totalTokens;
}
```

## Step 5: The Service Layer

Now the core logic. We'll create a service that handles both synchronous and streaming requests.

### Synchronous Chat

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class OpenAIService {

    private final WebClient openAIWebClient;
    private final OpenAIConfig openAIConfig;

    public ChatCompletionResponse chat(List<Message> messages) {
        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model(openAIConfig.getModel())
                .messages(messages)
                .maxTokens(openAIConfig.getMaxTokens())
                .temperature(openAIConfig.getTemperature())
                .stream(false)
                .build();

        return openAIWebClient.post()
                .uri("/chat/completions")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(ChatCompletionResponse.class)
                .block(); // Blocking for simplicity; use reactive in production
    }
}
```

### Streaming Chat (Server-Sent Events)

For real-time responses, OpenAI supports streaming. We'll use Flux:

```java
public Flux<String> streamChat(List<Message> messages) {
    ChatCompletionRequest request = ChatCompletionRequest.builder()
            .model(openAIConfig.getModel())
            .messages(messages)
            .maxTokens(openAIConfig.getMaxTokens())
            .temperature(openAIConfig.getTemperature())
            .stream(true)
            .build();

    return openAIWebClient.post()
            .uri("/chat/completions")
            .bodyValue(request)
            .retrieve()
            .bodyToFlux(String.class)
            .filter(data -> !data.equals("[DONE]"))
            .map(this::parseStreamData);
}

private String parseStreamData(String raw) {
    // OpenAI sends "data: {...}" lines
    if (raw.startsWith("data: ")) {
        String json = raw.substring(6);
        // Parse and extract content delta
        // For brevity, assume we have a stream parser
        return extractContentFromDelta(json);
    }
    return "";
}
```

**Note**: Streaming with WebClient requires careful parsing. Consider using the `openai-gpt3-java` library's streaming support for production.

## Step 6: REST Controller

Expose endpoints for your frontend:

```java
@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class AIController {

    private final OpenAIService openAIService;

    @PostMapping("/chat")
    public ResponseEntity<ChatCompletionResponse> chat(@RequestBody ChatRequest request) {
        List<Message> messages = request.getMessages();
        ChatCompletionResponse response = openAIService.chat(messages);
        return ResponseEntity.ok(response);
    }

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> streamChat(@RequestBody ChatRequest request) {
        return openAIService.streamChat(request.getMessages());
    }
}

@Data
public class ChatRequest {
    private List<Message> messages;
}
```

## Step 7: Error Handling

OpenAI API can return various errors (rate limits, authentication, etc.). Implement a global exception handler:

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(WebClientResponseException.class)
    public ResponseEntity<ErrorResponse> handleWebClientException(WebClientResponseException ex) {
        log.error("OpenAI API error: {}", ex.getResponseBodyAsString());
        ErrorResponse error = new ErrorResponse(
                ex.getStatusCode().value(),
                "AI service error. Please try again later."
        );
        return ResponseEntity.status(ex.getStatusCode()).body(error);
    }

    @ExceptionHandler(OpenAIServiceException.class)
    public ResponseEntity<ErrorResponse> handleServiceException(OpenAIServiceException ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ErrorResponse(500, ex.getMessage()));
    }
}

@Data
@AllArgsConstructor
public class ErrorResponse {
    private int status;
    private String message;
}
```

Create a custom exception:

```java
public class OpenAIServiceException extends RuntimeException {
    public OpenAIServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}
```

## Step 8: Rate Limiting and Retries

OpenAI enforces rate limits. Use Spring Retry and resilience4j:

```yaml
resilience4j.retry:
  configs:
    default:
      max-attempts: 3
      wait-duration: 2s
      retry-exceptions:
        - org.springframework.web.client.HttpServerErrorException
```

Add retry to your service:

```java
@Retryable(value = OpenAIServiceException.class, maxAttempts = 3, backoff = @Backoff(delay = 2000))
public ChatCompletionResponse chat(List<Message> messages) {
    // ... implementation
}
```

## Step 9: Testing the Integration

Write a simple integration test:

```java
@SpringBootTest
@AutoConfigureMockMvc
class AIControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void testChat() throws Exception {
        String request = """
                {
                    "messages": [
                        {"role": "user", "content": "Hello, who are you?"}
                    ]
                }
                """;

        mockMvc.perform(post("/api/ai/chat")
                .contentType(MediaType.APPLICATION_JSON)
                .content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.choices[0].message.content").isNotEmpty());
    }
}
```

For mocking the external API, use WireMock or MockServer.

## Step 10: Production Considerations

1. **Caching**: Cache common responses (e.g., greetings) to reduce costs and latency.
2. **Logging**: Log prompts and responses (anonymized) for debugging and compliance.
3. **Cost Management**: Track token usage per user/request.
4. **Security**: Validate input length and content to prevent prompt injection.
5. **Monitoring**: Set up alerts for API errors and latency spikes.

## Advanced: Using the Official Java Library

If you prefer a battle-tested client, use the `openai-gpt3-java` library:

```java
@Service
public class OpenAILibraryService {

    private final OpenAiService service;

    public OpenAILibraryService(OpenAIConfig config) {
        this.service = new OpenAiService(config.getApiKey(), Duration.ofSeconds(30));
    }

    public String chat(String userMessage) {
        ChatCompletionRequest request = ChatCompletionRequest.builder()
                .model("gpt-4")
                .messages(List.of(
                        new ChatMessage(ChatMessageRole.SYSTEM.value(), "You are a helpful assistant."),
                        new ChatMessage(ChatMessageRole.USER.value(), userMessage)
                ))
                .maxTokens(2048)
                .temperature(0.7)
                .build();

        ChatCompletionResult result = service.createChatCompletion(request);
        return result.getChoices().get(0).getMessage().getContent();
    }
}
```

This library handles serialization, streaming, and error mapping out of the box.

## Key Takeaways

- **Use Spring WebClient** for non-blocking HTTP calls to OpenAI's API, enabling streaming responses.
- **Model the API contract** with proper DTOs for request/response mapping.
- **Implement robust error handling** with retries and rate limiting to handle OpenAI's throttling.
- **Consider streaming** for better user experience when generating long responses.
- **Secure your API key** and monitor usage to control costs.
- **Test thoroughly** with mocked external services to avoid hitting API limits during development.

Integrating OpenAI with Spring Boot is straightforward once you understand the patterns. Start with the synchronous approach, then add streaming and resilience as needed. The combination of Java's robustness and AI's flexibility opens up endless possibilities for your applications.