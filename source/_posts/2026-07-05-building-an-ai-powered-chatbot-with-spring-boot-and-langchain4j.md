---
title: "Building an AI-Powered Chatbot with Spring Boot and LangChain4j"
date: 2026-07-05
tags: [Spring Boot, LangChain4j, Chatbot, AI, Java, LLM]
categories: [Java, AI]
cover:
description: Learn how to build an intelligent chatbot using Spring Boot and LangChain4j, including setup, LLM integration, RAG, memory, and deployment best practices.
---

# Building an AI-Powered Chatbot with Spring Boot and LangChain4j

Artificial intelligence is no longer a futuristic concept—it's a practical tool that developers can integrate into their applications today. Chatbots powered by large language models (LLMs) have become a cornerstone of customer support, internal knowledge bases, and interactive experiences. But how do you build one that's robust, maintainable, and scalable using the Java ecosystem?

Enter **LangChain4j**, a Java library that brings the power of LangChain to the JVM. Combined with **Spring Boot**, you can create production-ready AI chatbots with minimal boilerplate. In this guide, I'll walk you through building a complete chatbot from scratch, covering everything from setup to advanced features like memory and Retrieval-Augmented Generation (RAG).

## Why Spring Boot and LangChain4j?

Spring Boot is the de facto standard for building microservices and web applications in Java. It provides dependency injection, auto-configuration, and a mature ecosystem. LangChain4j bridges the gap between Java and LLMs, offering:

- **Unified API** for multiple LLM providers (OpenAI, Google Vertex AI, HuggingFace, local models)
- **Prompt templates** for structured interactions
- **Memory** for maintaining conversation context
- **RAG** support via document loaders and vector stores
- **Tool/function calling** for executing actions

Together, they allow you to focus on business logic rather than plumbing.

## Project Setup

Let's start by creating a Spring Boot project. You can use [Spring Initializr](https://start.spring.io/) or your favorite IDE.

### Dependencies

Add these to your `pom.xml`:

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j</artifactId>
        <version>0.33.0</version>
    </dependency>
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j-open-ai</artifactId>
        <version>0.33.0</version>
    </dependency>
    <!-- For RAG with local embedding -->
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j-embeddings-all-minilm-l6-v2</artifactId>
        <version>0.33.0</version>
    </dependency>
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j-elasticsearch</artifactId>
        <version>0.33.0</version>
    </dependency>
</dependencies>
```

### Configuration

Set your OpenAI API key in `application.properties`:

```properties
openai.api.key=sk-your-key-here
openai.model=gpt-4
langchain4j.open-ai.chat-model.api-key=${openai.api.key}
langchain4j.open-ai.chat-model.model-name=${openai.model}
```

For production, use environment variables or a secrets manager.

## Building the Core Chatbot

### 1. The Chat Service

Create a service that handles the conversation:

```java
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class ChatService {

    private final Assistant assistant;

    public ChatService(@Value("${openai.api.key}") String apiKey,
                       @Value("${openai.model}") String modelName) {
        
        OpenAiChatModel model = OpenAiChatModel.builder()
                .apiKey(apiKey)
                .modelName(modelName)
                .temperature(0.7)
                .build();

        ChatMemory memory = MessageWindowChatMemory.builder()
                .maxMessages(10)
                .build();

        this.assistant = AiServices.builder(Assistant.class)
                .chatLanguageModel(model)
                .chatMemory(memory)
                .build();
    }

    public String chat(String message) {
        return assistant.answer(message);
    }

    interface Assistant {
        String answer(String userMessage);
    }
}
```

This creates an LLM-powered assistant with a sliding window memory of the last 10 messages.

### 2. REST Controller

Expose the chatbot via a simple API:

```java
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ChatResponse chat(@RequestBody ChatRequest request) {
        String answer = chatService.chat(request.message());
        return new ChatResponse(answer);
    }

    record ChatRequest(String message) {}
    record ChatResponse(String response) {}
}
```

### 3. Testing the Bot

Start the application and send a request:

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Spring Boot?"}'
```

You'll get a detailed AI-generated response.

## Adding Memory and Context

Basic chatbots forget past messages. LangChain4j provides several memory implementations:

| Memory Type | Behavior |
|-------------|----------|
| `MessageWindowChatMemory` | Keeps last N messages |
| `TokenWindowChatMemory` | Keeps messages within token limit |
| `ChatMemoryProvider` | Creates session-based memory |

For multi-user support, use a `ChatMemoryProvider`:

```java
import dev.langchain4j.memory.chat.ChatMemoryProvider;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;

ChatMemoryProvider memoryProvider = chatId -> MessageWindowChatMemory.builder()
        .id(chatId)
        .maxMessages(20)
        .build();

Assistant assistant = AiServices.builder(Assistant.class)
        .chatLanguageModel(model)
        .chatMemoryProvider(memoryProvider)
        .build();
```

Now each user gets their own conversation history.

## Enhancing with RAG (Retrieval-Augmented Generation)

RAG allows your chatbot to answer questions based on your own documents. Here's how to implement it:

### 1. Document Ingestion

Load documents and store them in a vector database (we'll use Elasticsearch):

```java
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.loader.FileSystemDocumentLoader;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.AllMiniLmL6V2EmbeddingModel;
import dev.langchain4j.store.embedding.elasticsearch.ElasticsearchEmbeddingStore;
import org.springframework.stereotype.Service;

@Service
public class DocumentIngestionService {

    public void ingestDocuments(String directoryPath) {
        List<Document> documents = FileSystemDocumentLoader.loadDocuments(directoryPath);
        
        AllMiniLmL6V2EmbeddingModel embeddingModel = new AllMiniLmL6V2EmbeddingModel();
        ElasticsearchEmbeddingStore embeddingStore = ElasticsearchEmbeddingStore.builder()
                .serverUrl("http://localhost:9200")
                .indexName("chatbot_docs")
                .build();

        List<TextSegment> segments = documents.stream()
                .flatMap(doc -> DocumentSplitter.split(doc, 500, 50).stream())
                .collect(Collectors.toList());

        List<Embedding> embeddings = embeddingModel.embedAll(segments).content();
        embeddingStore.addAll(embeddings, segments);
    }
}
```

### 2. RAG-Enabled Assistant

Create a service that retrieves relevant documents before answering:

```java
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.rag.content.retriever.ContentRetriever;
import dev.langchain4j.rag.content.retriever.EmbeddingStoreContentRetriever;

@Service
public class RagChatService {

    private final RagAssistant assistant;

    public RagChatService(@Value("${openai.api.key}") String apiKey) {
        OpenAiChatModel model = OpenAiChatModel.withApiKey(apiKey);
        
        EmbeddingStore<TextSegment> embeddingStore = ElasticsearchEmbeddingStore.builder()
                .serverUrl("http://localhost:9200")
                .indexName("chatbot_docs")
                .build();

        ContentRetriever retriever = EmbeddingStoreContentRetriever.builder()
                .embeddingStore(embeddingStore)
                .embeddingModel(new AllMiniLmL6V2EmbeddingModel())
                .maxResults(3)
                .minScore(0.6)
                .build();

        this.assistant = AiServices.builder(RagAssistant.class)
                .chatLanguageModel(model)
                .contentRetriever(retriever)
                .build();
    }

    public String chat(String message) {
        return assistant.answer(message);
    }

    interface RagAssistant {
        @SystemMessage("You are a helpful assistant. Answer based on the provided context.")
        @UserMessage("{{userMessage}}")
        String answer(@V("userMessage") String userMessage);
    }
}
```

Now your chatbot can answer questions about your internal documentation!

## Tool Calling: Let the Chatbot Act

LangChain4j supports tool/function calling, allowing your chatbot to execute actions. Let's create a weather tool:

```java
import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

@Component
public class WeatherTools {

    @Tool("Get the current weather for a given city")
    public String getWeather(String city) {
        // In real life, call a weather API
        return "The weather in " + city + " is sunny, 22°C.";
    }
}
```

Register the tools with your assistant:

```java
Assistant assistant = AiServices.builder(Assistant.class)
        .chatLanguageModel(model)
        .tools(new WeatherTools())
        .build();
```

Now the chatbot can answer "What's the weather in Paris?" by calling your tool.

## Production Considerations

### 1. Rate Limiting and Cost Control

Use Spring's `@RateLimiter` or a dedicated library:

```java
@PostMapping
@RateLimiter(name = "chatbot")
public ChatResponse chat(@RequestBody ChatRequest request) {
    return new ChatResponse(chatService.chat(request.message()));
}
```

Configure rate limits in `application.properties`:

```properties
resilience4j.ratelimiter.instances.chatbot.limit-for-period=10
resilience4j.ratelimiter.instances.chatbot.limit-refresh-period=1m
```

### 2. Monitoring and Observability

Add metrics with Micrometer:

```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;

@Service
public class MonitoredChatService {
    
    private final Timer chatTimer;
    
    public MonitoredChatService(MeterRegistry registry, ChatService chatService) {
        this.chatTimer = registry.timer("chat.request.duration");
        this.chatService = chatService;
    }
    
    public String chat(String message) {
        return chatTimer.record(() -> chatService.chat(message));
    }
}
```

### 3. Streaming Responses

For better UX, stream tokens as they're generated:

```java
import dev.langchain4j.model.StreamingResponseHandler;
import dev.langchain4j.model.output.Response;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

public SseEmitter streamChat(String message) {
    SseEmitter emitter = new SseEmitter(30000L);
    
    model.generate(message, new StreamingResponseHandler<AiMessage>() {
        @Override
        public void onNext(String token) {
            try {
                emitter.send(SseEmitter.event().data(token));
            } catch (IOException e) {
                emitter.completeWithError(e);
            }
        }

        @Override
        public void onComplete(Response<AiMessage> response) {
            emitter.complete();
        }

        @Override
        public void onError(Throwable error) {
            emitter.completeWithError(error);
        }
    });
    
    return emitter;
}
```

### 4. Security

Never expose your API key in client-side code. Use a backend proxy:

```java
@Bean
public FilterRegistrationBean<ApiKeyFilter> apiKeyFilter() {
    FilterRegistrationBean<ApiKeyFilter> registration = new FilterRegistrationBean<>();
    registration.setFilter(new ApiKeyFilter());
    registration.addUrlPatterns("/api/chat/*");
    return registration;
}
```

## Complete Architecture

Here's a high-level view of a production system:

```yaml
services:
  chatbot-app:
    image: your-chatbot:latest
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - elasticsearch
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
```

## Key Takeaways

- **LangChain4j + Spring Boot** provides a powerful foundation for AI chatbots with minimal boilerplate.
- **Memory** is essential for coherent conversations—use `ChatMemoryProvider` for multi-user scenarios.
- **RAG** enables your chatbot to answer questions based on your own documents, improving accuracy and relevance.
- **Tool calling** extends chatbot capabilities beyond text generation, allowing real-world actions.
- **Production readiness** requires rate limiting, monitoring, streaming, and security measures.
- Start simple with a basic assistant, then incrementally add features like memory, RAG, and tools.

Building an AI-powered chatbot is no longer a daunting task. With Spring Boot and LangChain4j, you can focus on creating value rather than wrestling with infrastructure. Start small, iterate, and let your users guide the next features.