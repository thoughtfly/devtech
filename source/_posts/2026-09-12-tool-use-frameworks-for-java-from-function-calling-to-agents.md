---
title: "Tool-Use Frameworks for Java: From Function Calling to Agents"
date: 2026-09-12
tags: [Java, LLM, Agents, Tool-Use, Function Calling, Spring AI, LangChain4j]
categories: [Java]
cover: "https://images.unsplash.com/photo-1604403428907-673e7f4cd341?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to build LLM-powered agents in Java using tool-use frameworks, function calling, and practical code examples.
---

## The Java Developer’s Guide to Building LLM Agents

If you’ve spent any time in the Java ecosystem recently, you’ve likely noticed a surge of interest in Large Language Models (LLMs) and how to integrate them into enterprise applications. For years, Java has been the backbone of backend systems—robust, type-safe, and battle-tested. But when it comes to AI-driven features, the conversation has often centered around Python. That’s changing fast.

Today, we’re exploring how Java developers can build **tool-use frameworks** that empower LLMs to call external functions, access APIs, and make decisions—transforming simple chatbots into **autonomous agents**.

Whether you’re evaluating **Spring AI**, **LangChain4j**, or building custom integrations, this post will walk you through the architecture, patterns, and code needed to go from basic function calling to full-blown agent loops.

## Why Tool-Use Matters in Java

LLMs are incredibly capable at generating text, but they’re **stateless** and **hallucinate**. They don’t have real-time access to your database, your company’s knowledge base, or your internal APIs. Without tool-use, an LLM is just a fancy autocomplete engine.

**Tool-use** bridges this gap. It allows the model to:
- Call a function to fetch real-time data (e.g., current stock price)
- Execute a database query
- Trigger a workflow in your system
- Retrieve information from a vector store

In Java, this is particularly powerful because you can leverage the entire ecosystem—Spring Boot, Hibernate, Kafka, Kubernetes operators—while benefiting from the reasoning capabilities of modern LLMs.

## Core Concepts: Function Calling vs. Agents

Before diving into frameworks, let’s clarify two often-confused terms:

### Function Calling
**Function calling** (also known as tool calling) is the mechanism by which an LLM decides to invoke a specific function with structured arguments. The model doesn’t execute the function itself; it returns a structured request (usually JSON) that your code then executes.

Example:
```
User: "What’s the weather in Tokyo?"
Model: {"function": "get_weather", "arguments": {"city": "Tokyo"}}
```
Your Java code then calls `getWeather("Tokyo")` and feeds the result back to the model.

### Agents
An **agent** is a system that uses function calling in a **loop**. The agent:
1. Receives a user prompt
2. Decides which tool(s) to call
3. Executes the tool
4. Observes the result
5. Decides what to do next (call another tool, answer, or ask for clarification)

Agents are more autonomous and can handle complex, multi-step tasks.

## The Java Ecosystem: Key Frameworks

Two frameworks dominate the Java landscape for building tool-use systems:

1. **Spring AI** – Backed by VMware/Pivotal, integrates naturally with Spring Boot.
2. **LangChain4j** – A pure Java port of Python’s LangChain, focused on flexibility and composability.

Both support function calling and agent patterns. Let’s explore how to use them.

## Setting Up Spring AI for Tool Calling

Spring AI provides a `FunctionCallback` abstraction that makes it easy to expose Java methods to LLMs.

### Step 1: Add Dependencies

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

### Step 2: Define Your Tool

```java
@Component
public class WeatherTool {

    @Function
    public String getWeather(@Description("City name") String city) {
        // In production, call a real weather API
        return "Sunny, 22°C in " + city;
    }
}
```

### Step 3: Configure the Chat Client

```java
@Configuration
public class AiConfig {

    @Bean
    public ChatClient chatClient(ChatClient.Builder builder) {
        return builder.build();
    }

    @Bean
    public FunctionCallback weatherFunctionCallback(WeatherTool weatherTool) {
        return MethodToolCallback.builder()
                .toolObject(weatherTool)
                .methodName("getWeather")
                .build();
    }
}
```

### Step 4: Use the Tool in a Prompt

```java
@Service
public class WeatherService {

    private final ChatClient chatClient;
    private final FunctionCallback weatherCallback;

    public WeatherService(ChatClient chatClient,
                          FunctionCallback weatherCallback) {
        this.chatClient = chatClient;
        this.weatherCallback = weatherCallback;
    }

    public String askWeather(String question) {
        return chatClient.prompt()
                .functions(weatherCallback)
                .user(question)
                .call()
                .content();
    }
}
```

When you call `askWeather("What’s the weather in Tokyo?")`, Spring AI will:
1. Send the prompt to OpenAI with the function definition
2. Receive a function call request
3. Execute `getWeather("Tokyo")`
4. Send the result back to the model
5. Return a natural language answer

## Building Agents with LangChain4j

LangChain4j takes a more modular approach. Agents are built using **Tool** annotations and a **ToolExecutor**.

### Step 1: Add Dependencies

```xml
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-spring-boot-starter</artifactId>
</dependency>
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-open-ai-spring-boot-starter</artifactId>
</dependency>
```

### Step 2: Define Tools

```java
@Tool(description = "Get current weather for a city")
public String getWeather(@P("City name") String city) {
    return "Sunny, 22°C in " + city;
}

@Tool(description = "Calculate the total price of items")
public double calculateTotal(@P("List of item prices") List<Double> prices) {
    return prices.stream().mapToDouble(Double::doubleValue).sum();
}
```

### Step 3: Create an Agent

```java
@Service
public class AgentService {

    private final ChatLanguageModel chatModel;
    private final ToolProvider toolProvider;

    public AgentService(ChatLanguageModel chatModel,
                        ToolProvider toolProvider) {
        this.chatModel = chatModel;
        this.toolProvider = toolProvider;
    }

    public String chat(String userMessage) {
        // Build the agent
        Agent agent = Agent.builder()
                .chatLanguageModel(chatModel)
                .tools(toolProvider.getTools())
                .build();

        // Execute the agent
        return agent.chat(userMessage);
    }
}
```

LangChain4j handles the agent loop internally. The agent will call tools as needed until it can answer the user’s question.

## Advanced Pattern: Multi-Step Agents

Real-world agents often need to chain multiple tool calls. For example:
1. Search for a product
2. Get its price
3. Check inventory
4. Place an order

### Spring AI: Manual Agent Loop

Spring AI doesn’t include a built-in agent loop, so you implement it:

```java
public String multiStepAgent(String prompt) {
    String conversationHistory = prompt;
    
    for (int i = 0; i < 5; i++) { // Max iterations
        ChatResponse response = chatClient.prompt()
                .functions(weatherCallback, orderCallback)
                .system(conversationHistory)
                .call()
                .chatResponse();

        if (response.hasToolCalls()) {
            ToolResponse toolResponse = executeToolCalls(response.toolCalls());
            conversationHistory += "\nTool result: " + toolResponse;
        } else {
            return response.getResult().getOutput().getContent();
        }
    }
    return "Max iterations reached";
}
```

### LangChain4j: Built-In Agent

LangChain4j’s agent abstraction handles this automatically:

```java
Agent agent = Agent.builder()
        .chatLanguageModel(chatModel)
        .tools(searchTool, orderTool, inventoryTool)
        .maxIterations(10)
        .build();

String result = agent.chat("Find the cheapest laptop and add it to cart");
```

## Best Practices for Java Tool-Use

### 1. Type Safety with Java
Java’s strong typing is a superpower here. Define clear interfaces for your tools:

```java
public interface Tool {
    String getName();
    String getDescription();
    Object execute(Map<String, Object> arguments);
}
```

### 2. Error Handling
Always handle exceptions in tool execution. A failed tool call shouldn’t crash the agent.

```java
@Tool(description = "Fetch user data")
public String getUser(@P("userId") String userId) {
    try {
        return userService.findById(userId);
    } catch (Exception e) {
        return "Error: " + e.getMessage();
    }
}
```

### 3. Security Considerations
- **Validate inputs**: LLMs can be tricked into passing malicious arguments.
- **Restrict tools**: Only expose safe, read-only tools in production.
- **Audit calls**: Log all tool invocations for compliance.

### 4. Performance
Tool calls add latency. Cache results when possible and use async execution for independent tools.

## When to Use Which Framework

| Use Case | Recommended Framework |
|----------|----------------------|
| Spring Boot project | Spring AI |
| Need maximum flexibility | LangChain4j |
| Simple function calling | Either |
| Complex agent workflows | LangChain4j (built-in agent) |
| Integration with Spring ecosystem | Spring AI |
| Microservices architecture | LangChain4j |

## Real-World Example: Customer Support Agent

Let’s build a practical example—a customer support agent that can:
1. Look up order status
2. Process refunds
3. Escalate to a human

### Using Spring AI

```java
@Component
public class CustomerSupportTools {

    @Function
    public String getOrderStatus(@Description("Order ID") String orderId) {
        Order order = orderService.findById(orderId);
        return order.getStatus().toString();
    }

    @Function
    public String processRefund(@Description("Order ID") String orderId,
                                @Description("Reason") String reason) {
        refundService.process(orderId, reason);
        return "Refund processed for order " + orderId;
    }

    @Function
    public String escalate(@Description("Reason for escalation") String reason) {
        escalationService.createTicket(reason);
        return "Escalated to human agent";
    }
}
```

### Using LangChain4j

```java
@Tool(description = "Look up order status")
public String getOrderStatus(@P("Order ID") String orderId) {
    return orderService.findById(orderId).getStatus().toString();
}

@Tool(description = "Process a refund")
public String processRefund(@P("Order ID") String orderId,
                            @P("Reason") String reason) {
    refundService.process(orderId, reason);
    return "Refund processed";
}
```

Both approaches yield the same result: an LLM that can interact with your business logic.

## The Future of Java AI Development

The Java ecosystem is catching up rapidly. With projects like **Spring AI** gaining traction and **LangChain4j** maturing, Java developers now have first-class support for building AI-powered applications.

Key trends to watch:
- **Multi-modal agents**: Tools that can process images, audio, and video
- **RAG (Retrieval-Augmented Generation)**: Integrating vector databases for knowledge retrieval
- **Agent-to-agent communication**: Agents that can collaborate
- **Local LLM support**: Running models on-premise for privacy

## Key Takeaways

- **Tool-use** bridges the gap between LLM reasoning and real-world data/actions
- **Spring AI** integrates seamlessly with Spring Boot, ideal for enterprise Java
- **LangChain4j** offers a flexible, modular approach with built-in agent support
- **Function calling** lets LLMs request data from your Java services
- **Agents** use function calling in loops to solve complex, multi-step tasks
- Always prioritize **type safety**, **error handling**, and **security** in tool implementations
- The Java AI ecosystem is maturing rapidly—now is the time to start building

Whether you’re enhancing an existing application with AI features or building a new agent-driven platform, Java now has the tools to compete with Python in the AI space. Start small with function calling, then evolve to agents as your requirements grow.