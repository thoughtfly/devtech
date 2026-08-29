---
title: "Building Reliable Tool Calling for LLM Agents"
date: 2026-08-29
tags: [LLM, Agents, Tool Calling, AI Engineering, Production]
categories: [AI Engineering]
cover: "https://images.unsplash.com/photo-1692598578454-570cb62ecf2f?w=1200&q=80&fit=crop&fm=webp"
description: Learn how to build robust, production-ready tool calling for LLM agents. Covers schemas, error handling, retries, and real-world patterns.
---

## Introduction

Large Language Models have become incredibly capable at understanding context, reasoning through problems, and generating human-like text. But when it comes to actually doing things—calling APIs, querying databases, or manipulating files—LLMs need a bridge to the real world. That bridge is tool calling.

Tool calling allows an LLM to execute external functions by generating structured requests. It is the foundation of modern AI agents, enabling models to go beyond text generation and perform actual work. However, building reliable tool calling in production is far more complex than simply passing a function definition to an LLM and hoping for the best.

In this post, we will explore the patterns, pitfalls, and best practices for building robust tool calling systems. We will cover schema design, error handling strategies, retry logic, and real-world implementation patterns that have proven effective in production environments.

## Why Tool Calling Is Harder Than It Looks

At first glance, tool calling seems straightforward. You define a function, provide its schema to the model, and let it generate the appropriate arguments. The model calls the tool, you execute it, and pass the result back. Done, right?

In practice, several failure modes emerge quickly:

- **Schema drift**: The model generates arguments that do not match your schema exactly, causing validation failures or silent data corruption.
- **Missing tools**: The model requests tools that do not exist in your registry, or fails to call tools that are available.
- **Circular dependencies**: Tools call other tools, creating deep call chains that can loop indefinitely.
- **Timeouts and failures**: External APIs fail, return partial responses, or exceed latency thresholds.
- **Hallucinated arguments**: The model invents parameters that do not exist in the schema.

Each of these issues requires deliberate engineering to address. Let us walk through the solutions.

## Designing Robust Tool Schemas

The foundation of reliable tool calling is a well-designed schema. Your schema defines what the model can do, how it should do it, and what constraints apply. Poor schema design leads to poor model behavior.

### Use Strict Typing

Always define explicit types for every parameter. Avoid using `any` or `object` without a clear structure. When the model knows exactly what type to expect, it generates more accurate arguments.

```java
public class ToolSchema {
    private final String name;
    private final String description;
    private final Map<String, Object> parameters;
    private final Map<String, String> required;
    
    public ToolSchema(String name, String description, 
                      Map<String, Object> parameters, 
                      List<String> requiredFields) {
        this.name = name;
        this.description = description;
        this.parameters = parameters;
        this.required = requiredFields.stream()
            .collect(Collectors.toMap(f -> f, f -> "required"));
    }
}
```

### Provide Rich Descriptions

The model relies heavily on your tool descriptions to decide when and how to call a tool. Vague descriptions lead to missed calls or incorrect usage. Be specific about:

- What the tool does
- When to use it
- What the expected input looks like
- What the output represents

```java
ToolSchema searchIndex = new ToolSchema(
    "search_documents",
    "Searches the document index for relevant content. " +
    "Use this when the user asks about specific documents, " +
    "knowledge base entries, or stored information. " +
    "Returns a list of matching documents with their IDs and snippets.",
    Map.of(
        "query", Map.of("type", "string", 
            "description", "The search query to execute"),
        "limit", Map.of("type", "integer", 
            "description", "Maximum number of results to return", 
            "default", 10),
        "filters", Map.of("type", "object", 
            "description", "Optional filters for document type, date range, etc.")
    ),
    List.of("query")
);
```

### Validate Before Execution

Never trust the model to generate valid arguments. Always validate the generated parameters against your schema before executing the tool. This catches errors early and provides clear feedback.

```java
public class ToolValidator {
    public ValidationResult validate(ToolCall call, ToolSchema schema) {
        List<String> errors = new ArrayList<>();
        
        // Check required fields
        for (String required : schema.getRequiredFields()) {
            if (!call.getArguments().containsKey(required)) {
                errors.add("Missing required field: " + required);
            }
        }
        
        // Validate types
        for (Map.Entry<String, Object> entry : call.getArguments().entrySet()) {
            String fieldName = entry.getKey();
            Object value = entry.getValue();
            Object fieldSchema = schema.getParameters().get(fieldName);
            
            if (fieldSchema != null) {
                String expectedType = (String) ((Map) fieldSchema).get("type");
                if (!matchesType(value, expectedType)) {
                    errors.add("Field '" + fieldName + "' should be " + 
                               expectedType + " but got " + value.getClass().getName());
                }
            }
        }
        
        return new ValidationResult(errors.isEmpty(), errors);
    }
}
```

## Handling Tool Execution Errors

Even with perfect schemas, tools will fail. APIs return errors, databases timeout, and external services become unavailable. Your agent needs to handle these failures gracefully.

### Implement Retry Logic

Not all failures are permanent. Transient errors—network timeouts, rate limits, temporary service disruptions—should be retried with exponential backoff.

```java
public class ToolExecutor {
    private static final int MAX_RETRIES = 3;
    private static final long BASE_DELAY_MS = 1000;
    
    public ToolResult executeWithRetry(ToolCall call, ToolSchema schema) {
        int attempt = 0;
        Exception lastException = null;
        
        while (attempt < MAX_RETRIES) {
            try {
                return executeTool(call, schema);
            } catch (Exception e) {
                lastException = e;
                attempt++;
                
                if (attempt >= MAX_RETRIES) {
                    break;
                }
                
                long delay = BASE_DELAY_MS * (1L << (attempt - 1));
                Thread.sleep(delay);
            }
        }
        
        return ToolResult.failure("Tool execution failed after " + 
                                  MAX_RETRIES + " attempts", lastException);
    }
}
```

### Distinguish Error Types

Not all errors should be retried. Permanent failures—invalid arguments, missing tools, permission denied—should fail fast. Transient failures—timeouts, rate limits, service unavailable—should be retried.

```java
public enum ErrorType {
    PERMANENT,
    TRANSIENT,
    UNKNOWN
}

public class ToolError {
    private final ErrorType type;
    private final String message;
    private final Exception cause;
    
    public static ToolError permanent(String message, Exception cause) {
        return new ToolError(ErrorType.PERMANENT, message, cause);
    }
    
    public static ToolError transient_(String message, Exception cause) {
        return new ToolError(ErrorType.TRANSIENT, message, cause);
    }
}
```

### Provide Structured Error Responses

When a tool fails, return structured error information that the model can understand and respond to. This allows the agent to adapt its strategy rather than getting stuck in a failure loop.

```java
public class ToolResult {
    private final boolean success;
    private final Object data;
    private final ToolError error;
    
    public static ToolResult success(Object data) {
        return new ToolResult(true, data, null);
    }
    
    public static ToolResult failure(String message, Exception cause) {
        return new ToolResult(false, null, ToolError.permanent(message, cause));
    }
}
```

## Managing Tool Call Chains

Agents often need to call multiple tools in sequence. One tool might provide data that another tool needs. Managing these call chains requires careful state tracking and cycle detection.

### Track Call State

Maintain a clear record of which tools have been called, with what arguments, and what results were returned. This allows the agent to avoid redundant calls and detect circular dependencies.

```java
public class CallState {
    private final List<ToolCallRecord> callHistory;
    private final Map<String, Object> context;
    
    public static class ToolCallRecord {
        private final String toolName;
        private final Map<String, Object> arguments;
        private final ToolResult result;
        private final long timestamp;
    }
}
```

### Detect Circular Dependencies

If tool A calls tool B, and tool B calls tool A, you have a circular dependency. Detect and break these cycles before they cause infinite loops.

```java
public class CycleDetector {
    private final Set<String> visitedTools;
    private final Set<String> inCurrentPath;
    
    public boolean hasCycle(String toolName, CallState state) {
        if (inCurrentPath.contains(toolName)) {
            return true;
        }
        
        if (visitedTools.contains(toolName)) {
            return false;
        }
        
        inCurrentPath.add(toolName);
        
        // Check if this tool calls tools that lead back to itself
        for (String calledTool : getCalledTools(toolName, state)) {
            if (hasCycle(calledTool, state)) {
                return true;
            }
        }
        
        inCurrentPath.remove(toolName);
        visitedTools.add(toolName);
        return false;
    }
}
```

### Limit Call Depth

Set a maximum depth for tool call chains. If the agent has not completed its task within a reasonable number of tool calls, it should stop and report failure. This prevents runaway agents from consuming excessive resources.

```java
public class AgentConfig {
    private final int maxToolCalls;
    private final int maxCallDepth;
    private final Duration timeout;
    
    public AgentConfig(int maxToolCalls, int maxCallDepth, Duration timeout) {
        this.maxToolCalls = maxToolCalls;
        this.maxCallDepth = maxCallDepth;
        this.timeout = timeout;
    }
}
```

## Implementing the Agent Loop

The agent loop is the core execution engine. It coordinates model inference, tool calling, and result processing in a continuous cycle until the task is complete or a stopping condition is met.

### The Basic Loop Structure

```java
public class AgentLoop {
    private final LLMClient llmClient;
    private final ToolRegistry toolRegistry;
    private final AgentConfig config;
    
    public AgentResult run(Task task) {
        List<Message> messages = new ArrayList<>();
        messages.add(new Message(Role.USER, task.getPrompt()));
        
        int toolCallCount = 0;
        int depth = 0;
        
        while (toolCallCount < config.getMaxToolCalls() && depth < config.getMaxCallDepth()) {
            // Get model response
            Response response = llmClient.complete(messages);
            messages.add(response.getMessage());
            
            // Check for tool calls
            if (response.hasToolCalls()) {
                toolCallCount++;
                depth++;
                
                // Execute tools
                List<ToolResult> results = executeTools(
                    response.getToolCalls(), toolRegistry
                );
                
                // Add tool results to messages
                for (int i = 0; i < response.getToolCalls().size(); i++) {
                    messages.add(new ToolResultMessage(results.get(i)));
                }
            } else {
                // No more tool calls, task complete
                return new AgentResult(true, response.getContent(), messages);
            }
        }
        
        // Max calls or depth reached
        return new AgentResult(false, null, messages);
    }
}
```

### Parallel Tool Execution

When multiple tools can be called independently, execute them in parallel to reduce latency. This is especially important when tools call external APIs with significant round-trip times.

```java
public class ParallelExecutor {
    public List<ToolResult> executeParallel(
        List<ToolCall> calls, ToolRegistry registry
    ) {
        return calls.parallelStream()
            .map(call -> executeTool(call, registry))
            .collect(Collectors.toList());
    }
}
```

## Real-World Patterns

### Pattern 1: Fallback Tools

When a primary tool fails, automatically try a fallback tool with modified arguments. This is useful when you have multiple ways to accomplish the same task.

```yaml
tools:
  - name: search_primary
    fallback: search_backup
    retry: true
  - name: search_backup
    fallback: null
    retry: false
```

### Pattern 2: Tool Chaining

When one tool depends on the output of another, chain them together. The agent should understand that tool B requires data from tool A.

```java
public class ToolDependency {
    private final String dependentTool;
    private final String requiredField;
    private final String sourceField;
}
```

### Pattern 3: Context Caching

Cache tool results that are likely to be needed again. This avoids redundant API calls and improves response times.

```java
public class ResultCache {
    private final Map<String, ToolResult> cache;
    private final Duration ttl;
    
    public ToolResult getOrCompute(String key, Supplier<ToolResult> computation) {
        return cache.computeIfAbsent(key, k -> {
            ToolResult result = computation.get();
            cache.put(k, result);
            return result;
        });
    }
}
```

## Key Takeaways

- **Schema design is critical**: Well-defined, strictly typed schemas with rich descriptions lead to more accurate tool calls and fewer validation failures.
- **Always validate**: Never trust the model to generate valid arguments. Validate every tool call against your schema before execution.
- **Handle errors gracefully**: Distinguish between permanent and transient errors. Retry transient failures with exponential backoff, but fail fast on permanent errors.
- **Manage call chains**: Track tool call state, detect circular dependencies, and limit call depth to prevent runaway agents.
- **Parallel execution**: Execute independent tools in parallel to reduce latency and improve throughput.
- **Cache results**: Cache frequently used tool results to avoid redundant API calls and improve response times.
- **Structured feedback**: Return structured error information that the model can understand and adapt to, rather than generic failure messages.

Building reliable tool calling for LLM agents requires careful attention to schema design, error handling, and execution patterns. By following these practices, you can build agent systems that are robust, efficient, and ready for production use.