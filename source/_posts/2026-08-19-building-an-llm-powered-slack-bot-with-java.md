---
title: "Building an LLM-Powered Slack Bot with Java: A Step-by-Step Guide"
date: 2026-08-19
tags: [Java, Slack, LLM, Spring Boot, AI, Chatbot]
categories: [Java, AI]
cover: "https://images.unsplash.com/photo-1649443992089-8bf1fc3c42f4?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to build a Slack bot powered by LLM using Java, Spring Boot, and the Slack API. Includes code examples, best practices, and deployment tips.
---

## Introduction

Slack has become the central hub for team communication in countless organizations. But what if your Slack workspace could have an AI-powered assistant that answers questions, drafts messages, and helps with daily tasks? In this guide, I'll walk you through building a Slack bot that leverages a large language model (LLM) using Java. We'll use Spring Boot for the backend, the Slack API for messaging, and an LLM provider like OpenAI or Anthropic for intelligence.

By the end of this tutorial, you'll have a working bot that can:
- Respond to direct messages and mentions
- Maintain conversation context
- Handle asynchronous events
- Be deployed to the cloud or on-premises

Let's dive in!

## Prerequisites

Before we start, make sure you have:
- Java 17 or later
- Maven or Gradle
- A Slack workspace (free tier is fine)
- An API key from an LLM provider (e.g., OpenAI, Anthropic, or a local model via Ollama)
- Basic familiarity with Spring Boot and REST APIs

## Architecture Overview

Our bot will consist of three main components:
1. **Slack Event Adapter**: Receives events from Slack (via WebSocket or HTTP) and normalizes them.
2. **LLM Service**: Calls the LLM API with conversation history and returns a response.
3. **Response Handler**: Sends the response back to Slack.

We'll use the official Slack SDK for Java, which simplifies both WebSocket and HTTP integrations. For the LLM, we'll use a simple REST client to call the API, keeping the implementation provider-agnostic.

## Setting Up the Project

Create a new Spring Boot project using [Spring Initializr](https://start.spring.io/) with dependencies: Web, WebSocket, and Lombok. Then, add the Slack SDK and an HTTP client (we'll use WebClient from Spring WebFlux).

Here's a snippet of our `pom.xml`:

```xml
<dependencies>
    <dependency>
        <groupId>com.slack.api</groupId>
        <artifactId>slack-api-client</artifactId>
        <version>1.39.0</version>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

## Slack App Configuration

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app.
2. Choose "From scratch" and give it a name.
3. Under **Event Subscriptions**, enable events and set the request URL to `https://your-domain.com/slack/events` (we'll implement this endpoint later).
4. Subscribe to the following bot events:
   - `message.channels` (messages in public channels)
   - `message.im` (direct messages)
   - `app_mention` (when the bot is mentioned)
5. Add the `chat:write` and `app_mentions:read` OAuth scopes.
6. Install the app to your workspace and copy the Bot User OAuth Token.

## Implementing the Slack Event Adapter

We'll create a controller that receives HTTP POST requests from Slack. Slack sends a URL verification challenge when you first set up the endpoint, so we need to handle that.

```java
@RestController
@RequestMapping("/slack")
public class SlackEventController {

    @PostMapping("/events")
    public ResponseEntity<?> handleEvent(@RequestBody String requestBody) {
        // Parse JSON to check for URL verification
        JsonNode root = new ObjectMapper().readTree(requestBody);
        if (root.has("challenge")) {
            return ResponseEntity.ok(root.get("challenge").asText());
        }
        // Process event asynchronously
        eventProcessor.processEvent(requestBody);
        return ResponseEntity.ok("");
    }
}
```

To avoid blocking Slack's retry logic, we return an empty 200 response immediately and process the event asynchronously. We'll use a `@Async` method or a message queue for that.

## Connecting to Slack via WebSocket

While HTTP is fine for most cases, WebSocket is more efficient for real-time interactions. The Slack SDK provides a `SocketModeClient` that handles the connection automatically.

```java
@Configuration
public class SlackConfig {

    @Bean
    public SocketModeClient socketModeClient(AppConfig config) {
        var client = new SocketModeClient(config.getSlackAppToken());
        client.addListener(EventsApiType.APP_MENTION, (event, ctx) -> {
            // Handle mention
        });
        client.addListener(EventsApiType.MESSAGE_IM, (event, ctx) -> {
            // Handle DM
        });
        return client;
    }
}
```

To use Socket Mode, you need to enable it in your Slack app settings and generate an App-Level Token with `connections:write` scope.

## Integrating the LLM

Now for the core logic. We'll create an `LLMService` that takes a list of messages and returns a response. For flexibility, we'll support multiple providers via an interface.

```java
public interface LLMService {
    String generateResponse(List<ChatMessage> messages) throws Exception;
}
```

Here's an implementation using OpenAI's API with WebClient:

```java
@Service
public class OpenAIService implements LLMService {

    private final WebClient webClient;
    private final String apiKey;

    public OpenAIService(@Value("${openai.api-key}") String apiKey) {
        this.apiKey = apiKey;
        this.webClient = WebClient.builder()
                .baseUrl("https://api.openai.com/v1")
                .defaultHeader("Authorization", "Bearer " + apiKey)
                .build();
    }

    @Override
    public String generateResponse(List<ChatMessage> messages) {
        Map<String, Object> request = Map.of(
            "model", "gpt-4o-mini",
            "messages", messages.stream().map(msg -> Map.of(
                "role", msg.role(),
                "content", msg.content()
            )).toList()
        );

        return webClient.post()
                .uri("/chat/completions")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(JsonNode.class)
                .map(json -> json.get("choices").get(0).get("message").get("content").asText())
                .block();
    }
}
```

We can similarly implement an Anthropic service or a local Ollama service. The key is to keep the interface clean so we can swap providers easily.

## Maintaining Conversation Context

To have meaningful conversations, we need to keep track of context. We'll store conversation history per user or channel in memory (for simplicity) or in a database for production.

```java
@Component
public class ConversationStore {

    private final Map<String, List<ChatMessage>> conversations = new ConcurrentHashMap<>();

    public void addMessage(String key, String role, String content) {
        conversations.computeIfAbsent(key, k -> new ArrayList<>()).add(new ChatMessage(role, content));
    }

    public List<ChatMessage> getHistory(String key) {
        return conversations.getOrDefault(key, new ArrayList<>());
    }

    public void clearHistory(String key) {
        conversations.remove(key);
    }
}
```

When a new message arrives, we append it to the history and send the last N messages to the LLM (to avoid token limits). We can also include a system prompt to set the bot's behavior.

## Sending Responses Back to Slack

After getting the LLM response, we send it back using Slack's `chat.postMessage` method. We'll use the `MethodsClient` from the SDK.

```java
@Component
public class SlackMessageSender {

    private final MethodsClient methodsClient;

    public SlackMessageSender(@Value("${slack.bot-token}") String botToken) {
        this.methodsClient = Slack.getInstance().methods(botToken);
    }

    public void sendMessage(String channel, String text) {
        try {
            methodsClient.chatPostMessage(r -> r
                .channel(channel)
                .text(text)
            );
        } catch (IOException e) {
            // Log error
        }
    }
}
```

## Handling Different Event Types

We need to handle various scenarios:
- **Direct messages**: The bot should respond to any DM.
- **Mentions in channels**: The bot should respond when mentioned.
- **Message edits or deletes**: We can ignore those for simplicity.

We'll create an `EventProcessor` class that parses the event and routes it accordingly.

```java
@Component
public class EventProcessor {

    @Async
    public void processEvent(String requestBody) {
        JsonNode root = new ObjectMapper().readTree(requestBody);
        String type = root.path("event").path("type").asText();
        if ("message".equals(type) && !root.path("event").path("bot_id").isMissingNode()) {
            // Ignore messages from bots to avoid loops
            return;
        }
        String channel = root.path("event").path("channel").asText();
        String userId = root.path("event").path("user").asText();
        String text = root.path("event").path("text").asText();
        // Remove mention from text if present
        String cleanText = text.replaceAll("<@[A-Z0-9]+>", "").trim();
        
        // Store user message
        conversationStore.addMessage(channel, "user", cleanText);
        
        // Get history and call LLM
        List<ChatMessage> history = conversationStore.getHistory(channel);
        String response = llmService.generateResponse(history);
        
        // Store bot response and send
        conversationStore.addMessage(channel, "assistant", response);
        slackMessageSender.sendMessage(channel, response);
    }
}
```

## Adding a System Prompt

To make the bot more useful, we can prepend a system message that defines its persona. For example:

```java
ChatMessage systemMessage = new ChatMessage("system", "You are a helpful assistant for a software development team. Answer questions about code, debugging, and best practices. Keep responses concise.");
```

We'll include this as the first message in the history when calling the LLM.

## Deployment Considerations

### Configuration

Store sensitive data like API keys and tokens in environment variables or a secrets manager. In Spring Boot, use `application.yml` with placeholders:

```yaml
slack:
  bot-token: ${SLACK_BOT_TOKEN}
  app-token: ${SLACK_APP_TOKEN}
openai:
  api-key: ${OPENAI_API_KEY}
```

### Scalability

If your bot gains popularity, you'll want to:
- Move conversation history to Redis or a database.
- Use a message queue (e.g., RabbitMQ) to decouple event processing.
- Implement rate limiting to avoid hitting LLM API limits.

### Error Handling

Implement retry logic for transient errors (e.g., network timeouts). Use Spring Retry or a simple loop with exponential backoff.

## Testing the Bot

Before deploying, test locally using Slack's Socket Mode. Run your Spring Boot app, and in your Slack workspace, send a DM to your bot. You should see a response after a few seconds (depending on LLM latency).

## Full Example: Putting It All Together

Here's a simplified version of the main application class:

```java
@SpringBootApplication
@EnableAsync
public class SlackBotApplication {

    public static void main(String[] args) {
        SpringApplication.run(SlackBotApplication.class, args);
    }
}
```

And the `application.yml`:

```yaml
server:
  port: 8080

slack:
  bot-token: ${SLACK_BOT_TOKEN}
  app-token: ${SLACK_APP_TOKEN}

openai:
  api-key: ${OPENAI_API_KEY}
```

## Conclusion

Building an LLM-powered Slack bot in Java is a rewarding project that combines modern AI with a popular communication platform. With the steps above, you can create a bot that answers questions, assists with tasks, and integrates seamlessly into your team's workflow. The same pattern can be extended to other platforms like Microsoft Teams or Discord.

Remember to start small—get a basic bot responding to mentions—then add features like conversation memory, multi-provider support, and advanced commands. The possibilities are endless!

## Key Takeaways

- Use the official Slack SDK for Java to handle events and messaging.
- Choose Socket Mode for development simplicity and HTTP endpoints for production if you need public URLs.
- Abstract the LLM provider behind an interface to allow swapping between OpenAI, Anthropic, or local models.
- Manage conversation context carefully to avoid token limits and maintain coherent interactions.
- Secure your tokens and API keys using environment variables or a secrets manager.
- Plan for scalability by using external storage for conversation history and async processing for events.

Happy coding! Now go build something amazing for your team.