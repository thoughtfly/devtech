---
title: "Building AI Agents with Spring AI Framework: A Practical Guide"
date: 2026-07-10
tags: [Spring AI, AI Agents, Java, LLM, Spring Boot]
categories: [Java, AI]
cover:
description: Learn to build intelligent AI agents using Spring AI Framework. Covers architecture, tool integration, multi-agent patterns, and production deployment with J...
---

# Building AI Agents with Spring AI Framework: A Practical Guide

The rise of Large Language Models (LLMs) has fundamentally changed how we approach software development. But while LLMs are powerful, they're inherently stateless and limited to text generation. To build truly useful applications, we need **AI agents** — autonomous systems that can reason, use tools, and interact with the world.

Enter **Spring AI**, the Spring ecosystem's answer to integrating AI capabilities into enterprise Java applications. As a seasoned Java developer who has built several production AI systems, I can confidently say Spring AI provides the most pragmatic framework for building AI agents in the Java ecosystem.

In this guide, I'll walk you through building AI agents with Spring AI, from basic concepts to production-ready multi-agent systems. We'll cover real code, architectural patterns, and the lessons I've learned the hard way.

## Why Spring AI for AI Agents?

Before diving into code, let's understand why Spring AI stands out:

- **Familiar Spring paradigms**: If you know Spring Boot, you already know 80% of Spring AI. It uses the same dependency injection, configuration, and abstraction patterns.
- **Vendor independence**: Switch between OpenAI, Anthropic, Ollama, or Azure OpenAI by changing a single property. No code changes needed.
- **Enterprise readiness**: Built-in retry logic, observability with Micrometer, and seamless integration with Spring's transaction management.
- **Tool ecosystem**: First-class support for function calling, RAG (Retrieval-Augmented Generation), and vector databases.

## Setting Up Your Spring AI Project

Let's start with a minimal Spring Boot project. Add the following to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
    <version>1.0.0-M5</version>
</dependency>
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-core</artifactId>
    <version>1.0.0-M5</version>
</dependency>
```

Configure your OpenAI API key in `application.yml`:

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4
          temperature: 0.7
```

## Building Your First AI Agent

An AI agent at its core is a loop: **perceive → reason → act**. Spring AI provides the `ChatClient` abstraction that makes this loop trivial to implement.

### Basic Agent with Tool Support

Let's build an agent that can answer questions about time and weather — tasks requiring real-time data:

```java
@Service
public class SimpleAgent {

    private final ChatClient chatClient;

    public SimpleAgent(ChatClient.Builder builder) {
        this.chatClient = builder
            .defaultSystem("""
                You are a helpful assistant with access to tools.
                Use the provided tools to answer questions accurately.
                If you cannot find the answer, say so.
            """)
            .defaultFunctions("getCurrentTime", "getWeather")
            .build();
    }

    public String ask(String question) {
        return chatClient.prompt()
            .user(question)
            .call()
            .content();
    }
}
```

Now define the tools (functions) the agent can use:

```java
@Component
@Description("Get the current time for a given timezone")
public class GetCurrentTimeFunction implements Function<GetCurrentTimeFunction.Request, GetCurrentTimeFunction.Response> {

    public record Request(String timezone) {}
    public record Response(String time, String timezone) {}

    @Override
    public Response apply(Request request) {
        ZoneId zoneId = ZoneId.of(request.timezone());
        String time = LocalDateTime.now(zoneId)
            .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        return new Response(time, request.timezone());
    }
}
```

```java
@Component
@Description("Get the current weather for a location")
public class GetWeatherFunction implements Function<GetWeatherFunction.Request, GetWeatherFunction.Response> {

    public record Request(String location) {}
    public record Response(String temperature, String condition) {}

    @Override
    public Response apply(Request request) {
        // In production, call a real weather API
        return new Response("22°C", "Sunny");
    }
}
```

The magic happens through **function calling**. The LLM decides when to call which function based on the user's query. Spring AI handles the serialization, invocation, and response integration automatically.

### Memory and Conversation History

Stateless agents are useless for real conversations. Spring AI provides `ChatMemory` implementations:

```java
@Service
public class ConversationalAgent {

    private final ChatClient chatClient;
    private final ChatMemory chatMemory;

    public ConversationalAgent(ChatClient.Builder builder, ChatMemory chatMemory) {
        this.chatMemory = chatMemory;
        this.chatClient = builder
            .defaultSystem("You are a helpful assistant.")
            .defaultAdvisors(
                new MessageChatMemoryAdvisor(chatMemory)
            )
            .build();
    }

    public String chat(String sessionId, String message) {
        return chatClient.prompt()
            .user(message)
            .advisors(a -> a.param("chat_memory_conversation_id", sessionId))
            .call()
            .content();
    }
}
```

Configure in-memory or Redis-backed memory:

```yaml
spring:
  ai:
    chat:
      memory:
        type: redis  # or 'in-memory' for dev
```

## Advanced Agent Patterns

### ReAct Agents with Spring AI

The ReAct (Reasoning + Acting) pattern is the gold standard for complex agents. Spring AI implements this via `ToolCallback` and a custom prompt template:

```java
@Component
public class ReactAgent {

    private final ChatClient chatClient;

    private static final String REACT_PROMPT = """
        Answer the following questions as best you can.
        You have access to the following tools:
        
        {tools}
        
        Use the following format:
        Question: the input question
        Thought: you should always think about what to do
        Action: the tool to take (one of {tool_names})
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        
        Question: {input}
        Thought:
        """;

    public ReactAgent(ChatClient.Builder builder, List<ToolCallback> toolCallbacks) {
        this.chatClient = builder
            .defaultSystem(REACT_PROMPT)
            .defaultTools(toolCallbacks)
            .build();
    }

    public String execute(String question) {
        return chatClient.prompt()
            .user(u -> u.text(question))
            .call()
            .content();
    }
}
```

### Multi-Agent Orchestration

Complex tasks often require multiple specialized agents. Here's how to orchestrate them:

```java
@Service
public class MultiAgentOrchestrator {

    private final Agent researchAgent;
    private final Agent writingAgent;
    private final Agent factCheckAgent;
    private final ChatClient router;

    public MultiAgentOrchestrator(
            Agent researchAgent,
            Agent writingAgent,
            Agent factCheckAgent,
            ChatClient.Builder builder) {
        this.researchAgent = researchAgent;
        this.writingAgent = writingAgent;
        this.factCheckAgent = factCheckAgent;
        this.router = builder
            .defaultSystem("""
                You are a router agent. Determine which specialist agent should handle the user's request:
                - For research questions: route to 'research'
                - For content creation: route to 'writing'
                - For verification: route to 'factcheck'
                Respond with only the agent name.
            """)
            .build();
    }

    public String handleRequest(String request) {
        String agentName = router.prompt()
            .user(request)
            .call()
            .content();

        return switch (agentName.trim().toLowerCase()) {
            case "research" -> researchAgent.execute(request);
            case "writing" -> writingAgent.execute(request);
            case "factcheck" -> factCheckAgent.execute(request);
            default -> "I'm sorry, I cannot handle this request.";
        };
    }
}
```

### RAG-Enhanced Agents

For agents that need access to private documentation or domain knowledge:

```java
@Service
public class RagAgent {

    private final ChatClient chatClient;
    private final VectorStore vectorStore;

    public RagAgent(ChatClient.Builder builder, VectorStore vectorStore) {
        this.vectorStore = vectorStore;
        this.chatClient = builder
            .defaultSystem("""
                You are a knowledgeable assistant.
                Use the provided context to answer questions accurately.
                If the context doesn't contain relevant information, say so.
            """)
            .defaultAdvisors(
                new VectorStoreChatMemoryAdvisor(vectorStore)
            )
            .build();
    }

    public String ask(String question) {
        return chatClient.prompt()
            .user(question)
            .advisors(a -> a
                .param("chat_memory_conversation_id", "session-1")
                .param("chat_memory_response_size", 3))
            .call()
            .content();
    }
}
```

Configure a vector store (e.g., PostgreSQL with pgvector):

```yaml
spring:
  ai:
    vectorstore:
      pgvector:
        index-type: HNSW
        distance-type: COSINE_DISTANCE
        initialize-schema: true
```

## Production Considerations

### Observability with Micrometer

Spring AI automatically instruments agents with Micrometer. Add the following to see metrics:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
  metrics:
    tags:
      application: ai-agent
```

Key metrics to monitor:
- `spring.ai.chat.requests` - total requests
- `spring.ai.chat.tokens` - token usage (critical for cost management)
- `spring.ai.tool.calls` - tool invocation frequency
- `spring.ai.chat.duration` - response latency

### Error Handling and Retries

LLMs are notoriously unreliable. Configure robust retry:

```yaml
spring:
  ai:
    retry:
      max-attempts: 3
      backoff:
        initial-interval: 1000ms
        multiplier: 2
        max-interval: 10000ms
```

### Rate Limiting

Protect your API keys and backend services:

```java
@Bean
public RateLimiter rateLimiter() {
    return RateLimiter.create(10); // 10 requests per second
}

// Use in agent
public String ask(String question) {
    return rateLimiter.tryAcquire() 
        ? chatClient.prompt().user(question).call().content()
        : "Service busy, please try again later.";
}
```

### Testing AI Agents

Testing LLM-based systems requires a different approach. Use Spring AI's test utilities:

```java
@SpringBootTest
@AutoConfigureMockMvc
class AgentTest {

    @Autowired
    private SimpleAgent agent;

    @Test
    void testTimeQuery() {
        String response = agent.ask("What time is it in London?");
        assertThat(response).contains("2024");
        assertThat(response).contains("London");
    }

    @Test
    void testToolUsage() {
        // Verify the agent actually calls tools
        when(weatherService.getWeather(any())).thenReturn(new Weather("25°C", "Cloudy"));
        
        String response = agent.ask("What's the weather in Paris?");
        assertThat(response).contains("25°C");
        verify(weatherService).getWeather(eq("Paris"));
    }
}
```

## Real-World Architecture

Here's a production-ready architecture I've used successfully:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  API Gateway │────▶│  Agent Router │────▶│  Specialist │
│  (Spring     │     │  (Spring AI)  │     │  Agents     │
│   Cloud)     │     │              │     │  (Pool)     │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Vector Store │
                    │  (PostgreSQL) │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Tool        │
                    │  Executor    │
                    │  (Redis Queue)│
                    └──────────────┘
```

Key components:
- **API Gateway**: Rate limiting, authentication, request validation
- **Agent Router**: Determines which specialist agent to invoke
- **Specialist Agents**: Focused agents for specific domains (code, docs, data)
- **Vector Store**: Long-term memory and RAG context
- **Tool Executor**: Async tool execution with timeout and retry

## Common Pitfalls and Solutions

1. **Token limit exceeded**: Use `ChatClient` with `maxTokens` and chunking for large documents
2. **Tool hallucination**: Always validate tool inputs with explicit schemas
3. **Conversation drift**: Implement periodic summarization of conversation history
4. **Cost explosion**: Set per-request token limits and monitor aggressively
5. **Latency**: Use streaming responses (`chatClient.prompt().stream()`) for better UX

## Key Takeaways

- **Spring AI provides a production-ready foundation** for building AI agents in Java, leveraging familiar Spring patterns like dependency injection and auto-configuration.
- **Function calling is the backbone** of agent capabilities — define tools as Spring beans and let the LLM decide when to use them.
- **Memory management** is critical for conversational agents; use `ChatMemory` implementations for conversation history and vector stores for long-term knowledge.
- **Multi-agent architectures** scale better than monolithic agents; use a router agent to delegate to specialists.
- **Observability and cost management** are non-negotiable in production — leverage Micrometer metrics and set strict token limits.
- **Testing AI agents** requires a shift from deterministic assertions to behavior verification and integration tests with mock LLM responses.

Building AI agents with Spring AI feels like cheating — it handles all the complex orchestration while letting you focus on what makes your application unique. The framework is maturing rapidly, and I expect it to become the standard for Java-based AI development.

Now go build something intelligent.