---
title: "Hands-On: Building MCP Servers and Clients in Java"
date: 2026-09-06
tags: [Java, MCP, LLM, AI, Spring Boot]
categories: [Java]
cover: "https://picsum.photos/seed/hands-on-building-mcp-servers-and-clients-in-java/1200/630.webp"
description: Learn how to build Model Context Protocol servers and clients in Java. Step-by-step guide with code examples for integrating LLMs with external tools.
---

## Introduction

The Model Context Protocol (MCP) has emerged as a standard way to connect AI models with external tools and data sources. If you're a Java developer looking to integrate MCP into your applications, this hands-on guide will walk you through building both servers and clients.

MCP enables LLMs to interact with your Java services in a standardized way, making it easier to expose tools, resources, and prompts to AI applications.

## What is MCP?

MCP is an open protocol that standardizes how applications provide context to LLMs. It defines a client-server architecture where:

- **Servers** expose tools, resources, and prompts
- **Clients** connect to servers and request access to these capabilities

## Setting Up Your Java Project

Let's start with a Spring Boot project structure:

```java
// pom.xml dependencies
<dependencies>
    <dependency>
        <groupId>io.modelcontextprotocol</groupId>
        <artifactId>mcp-server-sdk</artifactId>
        <version>0.9.0</version>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
</dependencies>
```

## Building an MCP Server

Here's how to create a basic MCP server in Java:

```java
@RestController
public class McpServerController {
    
    @PostMapping("/mcp/tools")
    public ResponseEntity<List<Tool>> getTools() {
        List<Tool> tools = Arrays.asList(
            new Tool("get_weather", "Get weather information")
        );
        return ResponseEntity.ok(tools);
    }
    
    @PostMapping("/mcp/call")
    public ResponseEntity<CallToolResult> callTool(@RequestBody CallToolRequest request) {
        // Implement tool logic
        return ResponseEntity.ok(new CallToolResult("sunny"));
    }
}
```

## Creating an MCP Client

The client connects to servers and invokes tools:

```java
@Component
public class McpClient {
    
    private final WebClient webClient;
    
    public McpClient(WebClient.Builder builder) {
        this.webClient = builder.baseUrl("http://localhost:8080").build();
    }
    
    public String callTool(String toolName, Map<String, Object> arguments) {
        return webClient.post()
            .uri("/mcp/call")
            .bodyValue(new CallToolRequest(toolName, arguments))
            .retrieve()
            .bodyToMono(CallToolResult.class)
            .block();
    }
}
```

## Key Takeaways

- MCP provides a standardized way to connect LLMs with Java services
- Servers expose tools and resources; clients consume them
- Spring Boot makes MCP integration straightforward
- The protocol enables secure, structured communication between AI and your applications