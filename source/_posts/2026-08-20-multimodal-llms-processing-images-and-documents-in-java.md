---
title: "Multimodal LLMs: Processing Images and Documents in Java"
date: 2026-08-20
tags: [Multimodal LLM, Java, Image Processing, Document Processing, OpenAI, Spring Boot]
categories: [Java]
cover: "https://images.unsplash.com/photo-1687603917313-ccae1a289a9d?w=1200&q=80&fit=crop&fm=webp"
description: Learn to integrate multimodal LLMs in Java for image and document processing. Explore APIs, code examples, and best practices.
---

## Introduction

Imagine a Java application that can 'see' a screenshot, 'read' a scanned invoice, and 'understand' a chart—all without specialized OCR or computer vision pipelines. This is no longer science fiction. Multimodal Large Language Models (LLMs) like GPT-4V, Claude 3, and Gemini have opened up a new frontier: they can process images and documents alongside text, generating insights that were previously impossible to achieve programmatically.

As a Java developer, you might feel left out of the AI revolution, which often seems dominated by Python. But the reality is that Java's robust ecosystem, enterprise-grade stability, and strong typing make it an excellent choice for integrating multimodal AI into production systems. In this post, we'll dive deep into how you can leverage multimodal LLMs in Java to process images and documents. We'll explore the core concepts, walk through practical code examples using popular APIs like OpenAI and Anthropic, and discuss best practices for building scalable, maintainable AI-powered features.

By the end of this article, you'll have a solid understanding of how to:
- Choose the right multimodal model for your use case
- Send images and documents to LLMs from Java
- Parse and use the responses effectively
- Handle common pitfalls like token limits and image encoding

Let's get started!

## Understanding Multimodal LLMs

Before we jump into code, let's clarify what multimodal LLMs are and how they differ from their text-only predecessors.

Traditional LLMs like GPT-3.5 or Llama 2 are trained exclusively on text. They can generate code, answer questions, and summarize documents, but they are blind to images, audio, and other non-text data. Multimodal LLMs, on the other hand, are trained on a mixture of text and visual data (and sometimes audio). They can take in an image and a text prompt, and generate a text response that references the visual content. For example, you can show a model a picture of a broken car engine and ask, "What seems to be the issue?" and it will analyze the image and provide a diagnosis.

This capability is transformative for many industries. In healthcare, models can analyze X-rays. In e-commerce, they can generate product descriptions from images. In finance, they can extract data from receipts and invoices. The possibilities are endless.

### How Do They Work?

Without getting too deep into the architecture, multimodal models typically use a vision encoder (like a Vision Transformer) to convert images into embeddings, which are then fused with text embeddings. This combined representation is fed into a transformer decoder that generates the response. The result is a model that can reason about visual and textual information jointly.

### Popular Multimodal Models

As of 2024, the major players are:
- **OpenAI GPT-4V (Vision)**: Accessible via the Chat Completions API, supports image inputs in base64 or URL form.
- **Anthropic Claude 3**: Supports image (base64) and document (PDF) inputs, known for strong reasoning.
- **Google Gemini**: Offers multimodal support via the Vertex AI API, including images, video, and text.
- **Open-source models**: Like LLaVA, which can be self-hosted.

For Java developers, the easiest path is to use cloud APIs, as they handle the heavy lifting and provide simple REST endpoints. We'll focus on OpenAI and Anthropic, but the concepts apply to any provider.

## Setting Up Your Java Project

Let's create a simple Java project using Maven. We'll use Spring Boot for simplicity, but you can use plain Java if you prefer.

First, generate a project via [Spring Initializr](https://start.spring.io/) with dependencies for Spring Web and Lombok. Then, add the following dependencies to your `pom.xml`:

```xml
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.12.0</version>
</dependency>
<dependency>
    <groupId>org.json</groupId>
    <artifactId>json</artifactId>
    <version>20240303</version>
</dependency>
```

We'll use OkHttp for making HTTP requests and the JSON library for parsing responses. Alternatively, you could use Spring's `RestTemplate` or WebClient, but OkHttp is lightweight and easy to use.

Next, set up your API keys. For OpenAI, get an API key from [platform.openai.com](https://platform.openai.com/). For Anthropic, get one from [console.anthropic.com](https://console.anthropic.com/). Store them in environment variables or a configuration file—never hardcode them.

## Sending an Image to GPT-4V from Java

Let's start with a simple example: sending an image to GPT-4V and getting a description.

### Step 1: Encode the Image

The API expects the image as a base64-encoded string. In Java, you can do this easily:

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;

public class ImageUtils {
    public static String encodeImageToBase64(String filePath) throws Exception {
        byte[] bytes = Files.readAllBytes(Path.of(filePath));
        return Base64.getEncoder().encodeToString(bytes);
    }
}
```

### Step 2: Build the Request

The OpenAI API uses a chat completions endpoint with a `messages` array. Each message can have `content` that is a list of parts, each part being either `text` or `image_url`. Here's how to construct the JSON:

```java
import org.json.JSONArray;
import org.json.JSONObject;

public class OpenAIClient {
    private static final String API_URL = "https://api.openai.com/v1/chat/completions";
    private final String apiKey;

    public OpenAIClient(String apiKey) {
        this.apiKey = apiKey;
    }

    public String analyzeImage(String imageBase64, String prompt) throws Exception {
        JSONObject requestBody = new JSONObject();
        requestBody.put("model", "gpt-4-vision-preview");
        requestBody.put("max_tokens", 1024);

        JSONArray messages = new JSONArray();
        JSONObject message = new JSONObject();
        message.put("role", "user");

        JSONArray content = new JSONArray();
        content.put(new JSONObject().put("type", "text").put("text", prompt));
        content.put(new JSONObject()
                .put("type", "image_url")
                .put("image_url", new JSONObject()
                        .put("url", "data:image/png;base64," + imageBase64)));

        message.put("content", content);
        messages.put(message);
        requestBody.put("messages", messages);

        // Make HTTP request with OkHttp
        String responseBody = sendRequest(requestBody.toString());
        return extractContent(responseBody);
    }

    private String sendRequest(String jsonBody) throws Exception {
        okhttp3.Request request = new okhttp3.Request.Builder()
                .url(API_URL)
                .addHeader("Authorization", "Bearer " + apiKey)
                .post(okhttp3.RequestBody.create(jsonBody, okhttp3.MediaType.parse("application/json")))
                .build();

        try (okhttp3.Response response = new okhttp3.OkHttpClient().newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new RuntimeException("API request failed: " + response.body().string());
            }
            return response.body().string();
        }
    }

    private String extractContent(String responseBody) {
        JSONObject json = new JSONObject(responseBody);
        return json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content");
    }
}
```

### Step 3: Use It

Now, let's put it together in a simple main method:

```java
public class Main {
    public static void main(String[] args) throws Exception {
        String apiKey = System.getenv("OPENAI_API_KEY");
        OpenAIClient client = new OpenAIClient(apiKey);

        String image = ImageUtils.encodeImageToBase64("src/main/resources/cat.png");
        String response = client.analyzeImage(image, "Describe this image in detail.");
        System.out.println(response);
    }
}
```

Run it, and you should get a text description of the image. That's the core of it! The same pattern applies to other providers, with slight variations in request format.

## Processing Documents with Anthropic Claude 3

Anthropic's Claude 3 models are particularly good at document understanding. They can take PDFs and images as base64 input. Let's see how to send a PDF to Claude 3 from Java.

### The Request Format

The API endpoint is `https://api.anthropic.com/v1/messages`. The request includes a `messages` array, and each message can have `content` with `type: "image"` and `source` containing the base64 data and media type.

Here's a client for Claude 3:

```java
import org.json.JSONArray;
import org.json.JSONObject;

public class AnthropicClient {
    private static final String API_URL = "https://api.anthropic.com/v1/messages";
    private final String apiKey;

    public AnthropicClient(String apiKey) {
        this.apiKey = apiKey;
    }

    public String analyzeDocument(String base64Content, String mediaType, String prompt) throws Exception {
        JSONObject requestBody = new JSONObject();
        requestBody.put("model", "claude-3-opus-20240229");
        requestBody.put("max_tokens", 1024);

        JSONArray messages = new JSONArray();
        JSONObject message = new JSONObject();
        message.put("role", "user");

        JSONArray content = new JSONArray();
        content.put(new JSONObject().put("type", "text").put("text", prompt));
        content.put(new JSONObject()
                .put("type", "image")
                .put("source", new JSONObject()
                        .put("type", "base64")
                        .put("media_type", mediaType) // "image/png" or "application/pdf"
                        .put("data", base64Content)));

        message.put("content", content);
        messages.put(message);
        requestBody.put("messages", messages);

        String responseBody = sendRequest(requestBody.toString());
        return extractText(responseBody);
    }

    private String sendRequest(String jsonBody) throws Exception {
        okhttp3.Request request = new okhttp3.Request.Builder()
                .url(API_URL)
                .addHeader("x-api-key", apiKey)
                .addHeader("anthropic-version", "2023-06-01")
                .post(okhttp3.RequestBody.create(jsonBody, okhttp3.MediaType.parse("application/json")))
                .build();
        // ... same as before
    }

    private String extractText(String responseBody) {
        JSONObject json = new JSONObject(responseBody);
        return json.getJSONArray("content").getJSONObject(0).getString("text");
    }
}
```

### Example: Extracting Invoice Data

Suppose you have a scanned invoice PDF. You can ask Claude to extract key fields:

```java
String pdfBase64 = ImageUtils.encodeImageToBase64("invoice.pdf");
String prompt = "Extract the invoice number, date, total amount, and vendor name from this document. Return as JSON.";
String result = client.analyzeDocument(pdfBase64, "application/pdf", prompt);
System.out.println(result);
```

The model will return a JSON object with the requested fields. This is incredibly powerful for automating data entry tasks.

## Practical Tips for Java Integration

Now that you've seen the basics, let's discuss some best practices to make your integration production-ready.

### 1. Handle Large Files

Base64 encoding increases the size by about 33%. If you're dealing with large PDFs or high-res images, you might hit API limits (e.g., OpenAI's max image size is 20MB). Consider resizing or compressing images before sending. Use Java's `ImageIO` to scale images:

```java
BufferedImage original = ImageIO.read(new File("input.png"));
BufferedImage resized = new BufferedImage(800, 600, BufferedImage.TYPE_INT_RGB);
Graphics2D g = resized.createGraphics();
g.drawImage(original, 0, 0, 800, 600, null);
g.dispose();
ImageIO.write(resized, "png", new File("resized.png"));
```

### 2. Token Limits and Cost Management

Multimodal requests consume more tokens than text-only ones. Each image can cost hundreds of tokens depending on resolution. Be mindful of your usage. Set `max_tokens` to a reasonable value to avoid unexpected costs. Implement a retry mechanism with exponential backoff for rate limits.

### 3. Error Handling

Always check the response status and handle errors gracefully. The APIs might return 400 for invalid requests, 401 for bad keys, 429 for rate limits, and 500 for server errors. Create a custom exception hierarchy for your AI client.

### 4. Caching Responses

If you're processing the same image multiple times (e.g., for testing), cache the results in memory or a database to avoid redundant API calls.

### 5. Use Spring Boot for Production

In a real application, you'd likely wrap these clients as Spring components and use `@Value` to inject API keys. Here's a quick example:

```java
@Service
public class DocumentAnalysisService {
    @Value("${anthropic.api-key}")
    private String apiKey;

    public String analyzeDocument(String base64Content, String mediaType, String prompt) {
        AnthropicClient client = new AnthropicClient(apiKey);
        return client.analyzeDocument(base64Content, mediaType, prompt);
    }
}
```

## Advanced Use Cases

Beyond simple image description, multimodal LLMs can power complex features:

- **Visual Question Answering**: "Is the product damaged in this image?"
- **Document Comparison**: "Compare the terms in these two contracts."
- **Chart Understanding**: "What is the trend in this line chart?"
- **Accessibility**: Generate alt text for images automatically.

### Example: Building a Chatbot with Image Input

You can extend your Spring Boot app to accept image uploads via REST, process them with the LLM, and return responses. Here's a controller snippet:

```java
@RestController
public class ChatController {
    private final DocumentAnalysisService service;

    public ChatController(DocumentAnalysisService service) {
        this.service = service;
    }

    @PostMapping("/analyze")
    public String analyze(@RequestParam("file") MultipartFile file,
                          @RequestParam("prompt") String prompt) throws Exception {
        String base64 = Base64.getEncoder().encodeToString(file.getBytes());
        String mediaType = file.getContentType();
        return service.analyzeDocument(base64, mediaType, prompt);
    }
}
```

## Conclusion

In this post, we've explored how to integrate multimodal LLMs into Java applications. We've seen how to send images to GPT-4V, process PDFs with Claude 3, and implement best practices for production. The ability to process images and documents opens up a world of possibilities for Java developers, from automating workflows to enhancing user experiences.

Remember, the key is to start small, experiment, and iterate. The AI landscape is evolving rapidly, and the skills you learn today will serve you well in the future.

## Key Takeaways

- Multimodal LLMs can process images and documents alongside text, enabling Java applications to 'see' and 'read'.
- Use cloud APIs like OpenAI GPT-4V, Anthropic Claude 3, or Google Gemini for easy integration; they handle the heavy lifting.
- Encode images and documents as base64 strings and send them via HTTP POST requests with JSON payloads.
- Handle large files by compressing or resizing, and be mindful of token costs.
- Implement robust error handling, retries, and caching for production-grade applications.
- Java's ecosystem (Spring Boot, Maven, etc.) is perfectly suited for building AI-powered features.

Now, go ahead and build something amazing with multimodal AI in Java!