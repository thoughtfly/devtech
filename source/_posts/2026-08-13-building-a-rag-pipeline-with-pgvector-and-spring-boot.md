---
title: "Building a RAG Pipeline with pgvector and Spring Boot"
date: 2026-08-13
tags: [RAG, pgvector, Spring Boot, AI, PostgreSQL]
categories: [Java]
cover: "https://picsum.photos/seed/building-a-rag-pipeline-with-pgvector-and-spring-boot/1200/630.webp"
description: Learn to build a scalable RAG pipeline using PostgreSQL's pgvector extension and Spring Boot. Step-by-step guide with code examples for embeddings, storage,...
---

## Introduction

In the rapidly evolving landscape of AI, Retrieval-Augmented Generation (RAG) has emerged as a powerful pattern to enhance language models with domain-specific knowledge. Instead of fine-tuning a model (which is expensive and static), RAG allows you to retrieve relevant documents at query time and feed them to the LLM as context. This approach improves accuracy, reduces hallucinations, and keeps your knowledge base up-to-date without retraining.

One of the most elegant ways to implement RAG is using **pgvector**, a PostgreSQL extension that adds vector similarity search capabilities. Combined with **Spring Boot**, you get a robust, scalable, and production-ready solution that leverages your existing database infrastructure.

In this comprehensive guide, I'll walk you through building a complete RAG pipeline from scratch using Spring Boot and pgvector. We'll cover:

- Setting up PostgreSQL with pgvector
- Generating embeddings using OpenAI's API (or any compatible model)
- Storing and indexing vectors efficiently
- Implementing similarity search with Spring Data JPA
- Exposing a REST API for querying documents
- Best practices for production deployment

By the end, you'll have a working RAG system that can answer questions based on your own documents.

## Prerequisites

Before we dive in, ensure you have the following:

- Java 17+ and Maven 3.8+
- PostgreSQL 13+ with pgvector extension installed
- An OpenAI API key (or any embedding model endpoint)
- Basic familiarity with Spring Boot and JPA

## 1. Setting Up PostgreSQL with pgvector

First, install the pgvector extension. On Ubuntu/Debian, you can use:

```bash
sudo apt-get install postgresql-14-pgvector
```

For other platforms, refer to the [official pgvector documentation](https://github.com/pgvector/pgvector).

Then, enable the extension in your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Now, let's create a table to store our documents and their embeddings. We'll design it to hold both the original text and the vector representation:

```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536)  -- 1536 dimensions for OpenAI embeddings
);

-- Create an index for fast similarity search (IVFFlat or HNSW)
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);
```

**Note**: The vector dimension must match your embedding model. OpenAI's `text-embedding-ada-002` produces 1536 dimensions. If you use a different model, adjust accordingly.

For production, consider using HNSW index for better performance at scale:

```sql
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
```

## 2. Project Setup

Create a new Spring Boot project using [Spring Initializr](https://start.spring.io/) with the following dependencies:

- Spring Web
- Spring Data JPA
- PostgreSQL Driver
- Validation

Add the pgvector JDBC support to your `pom.xml`:

```xml
<dependency>
    <groupId>com.pgvector</groupId>
    <artifactId>pgvector</artifactId>
    <version>0.1.4</version>
</dependency>
```

Also, include the OpenAI Java client (optional, but handy):

```xml
<dependency>
    <groupId>com.theokanning.openai-gpt3-java</groupId>
    <artifactId>service</artifactId>
    <version>0.18.2</version>
</dependency>
```

Configure your `application.properties`:

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/ragdb
spring.datasource.username=postgres
spring.datasource.password=password
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true

openai.api-key=${OPENAI_API_KEY}
```

## 3. Defining the Entity and Repository

Let's create a JPA entity that maps to our `documents` table. The `PgVector` type from the pgvector library handles the vector column.

```java
import com.pgvector.PGvector;
import jakarta.persistence.*;

@Entity
@Table(name = "documents")
public class Document {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "text")
    private String content;

    @Column(columnDefinition = "vector(1536)")
    private PGvector embedding;

    // Constructors, getters, setters...
    
    public Document() {}

    public Document(String content, PGvector embedding) {
        this.content = content;
        this.embedding = embedding;
    }

    // getters and setters omitted for brevity
}
```

Now, the repository. Spring Data JPA doesn't natively support vector similarity search, so we'll write a custom query using JPQL or native SQL. Here's how:

```java
import com.pgvector.PGvector;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {

    @Query(value = "SELECT * FROM documents ORDER BY embedding <=> :queryVector LIMIT :limit", nativeQuery = true)
    List<Document> findNearestNeighbors(@Param("queryVector") PGvector queryVector, @Param("limit") int limit);
}
```

The `<=>` operator is pgvector's cosine distance operator. We also support inner product (`<#>`) and Euclidean distance (`<->`).

## 4. Embedding Service

We need a service that converts text into embeddings using an LLM provider. Here's a simple implementation using OpenAI's API:

```java
import com.theokanning.openai.embedding.Embedding;
import com.theokanning.openai.embedding.EmbeddingRequest;
import com.theokanning.openai.service.OpenAiService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EmbeddingService {

    private final OpenAiService openAiService;

    public EmbeddingService(@Value("${openai.api-key}") String apiKey) {
        this.openAiService = new OpenAiService(apiKey);
    }

    public List<Float> generateEmbedding(String text) {
        EmbeddingRequest request = EmbeddingRequest.builder()
                .model("text-embedding-ada-002")
                .input(List.of(text))
                .build();
        List<Embedding> embeddings = openAiService.createEmbeddings(request).getData();
        return embeddings.get(0).getEmbedding();
    }
}
```

**Important**: Batch your embedding requests to reduce API calls and costs. For large document sets, consider using async processing.

## 5. Document Service

Now, let's create a service that handles document ingestion and retrieval:

```java
import com.pgvector.PGvector;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.SQLException;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final EmbeddingService embeddingService;

    public DocumentService(DocumentRepository documentRepository, EmbeddingService embeddingService) {
        this.documentRepository = documentRepository;
        this.embeddingService = embeddingService;
    }

    @Transactional
    public Document storeDocument(String content) {
        try {
            List<Float> embeddingValues = embeddingService.generateEmbedding(content);
            PGvector embedding = new PGvector(embeddingValues);
            Document doc = new Document(content, embedding);
            return documentRepository.save(doc);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to store document", e);
        }
    }

    @Transactional(readOnly = true)
    public List<Document> searchDocuments(String query, int limit) {
        try {
            List<Float> queryEmbedding = embeddingService.generateEmbedding(query);
            PGvector queryVector = new PGvector(queryEmbedding);
            return documentRepository.findNearestNeighbors(queryVector, limit);
        } catch (SQLException e) {
            throw new RuntimeException("Failed to search documents", e);
        }
    }
}
```

## 6. REST Controller

Expose endpoints for adding documents and querying them:

```java
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/rag")
public class RagController {

    private final DocumentService documentService;

    public RagController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @PostMapping("/documents")
    public ResponseEntity<Document> addDocument(@RequestBody String content) {
        Document saved = documentService.storeDocument(content);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/search")
    public ResponseEntity<List<Document>> search(@RequestParam String query, 
                                                 @RequestParam(defaultValue = "5") int limit) {
        List<Document> results = documentService.searchDocuments(query, limit);
        return ResponseEntity.ok(results);
    }
}
```

## 7. Integrating with an LLM for RAG

The search results alone are not the final answer. The true power of RAG comes from feeding these retrieved documents into an LLM to generate a coherent response. Let's add a method to the `DocumentService` that does this:

```java
import com.theokanning.openai.completion.chat.*;

public String generateAnswer(String query) {
    // Retrieve top-k relevant documents
    List<Document> docs = searchDocuments(query, 5);
    
    // Build the prompt with context
    StringBuilder context = new StringBuilder();
    for (Document doc : docs) {
        context.append(doc.getContent()).append("\n---\n");
    }

    String systemPrompt = "You are a helpful assistant. Use the following context to answer the user's question. If the answer is not in the context, say you don't know.";
    String userPrompt = "Context:\n" + context + "\n\nQuestion: " + query;

    // Call ChatGPT
    ChatCompletionRequest request = ChatCompletionRequest.builder()
            .model("gpt-3.5-turbo")
            .messages(List.of(
                new ChatMessage(ChatMessageRole.SYSTEM.value(), systemPrompt),
                new ChatMessage(ChatMessageRole.USER.value(), userPrompt)
            ))
            .maxTokens(200)
            .build();

    ChatCompletionResult result = openAiService.createChatCompletion(request);
    return result.getChoices().get(0).getMessage().getContent();
}
```

Add this method to the controller:

```java
@GetMapping("/ask")
public ResponseEntity<String> ask(@RequestParam String question) {
    String answer = documentService.generateAnswer(question);
    return ResponseEntity.ok(answer);
}
```

## 8. Testing the Pipeline

Let's test with some sample data. Start your PostgreSQL and Spring Boot app, then:

```bash
# Add a document
curl -X POST http://localhost:8080/api/rag/documents \
  -H "Content-Type: text/plain" \
  -d "Spring Boot is a popular Java framework for building microservices. It simplifies configuration and deployment."

# Search
curl "http://localhost:8080/api/rag/search?query=What+is+Spring+Boot?"

# Ask a question
curl "http://localhost:8080/api/rag/ask?question=What+is+Spring+Boot?"
```

The `/ask` endpoint should return a natural language answer based on the stored content.

## 9. Performance Optimization and Best Practices

### Indexing Strategy

- **IVFFlat** is faster to build and uses less memory, but requires tuning `lists` parameter. A good starting point is `lists = sqrt(number_of_rows)`.
- **HNSW** offers better query performance and doesn't need tuning, but uses more memory.

For production, I recommend HNSW for datasets up to millions of vectors.

### Chunking

Don't store entire documents as one embedding. Large documents lose semantic meaning when compressed into a single vector. Instead, chunk your documents into smaller pieces (e.g., 500-1000 tokens) with some overlap. This improves retrieval accuracy significantly.

### Caching Embeddings

If you have a static knowledge base, cache the embeddings to avoid regenerating them. You can store the embedding in a separate column or use a hash of the content to check if it already exists.

### Async Processing

For bulk ingestion, use `@Async` methods or a message queue like RabbitMQ to process embeddings in parallel and avoid blocking the main thread.

### Security

- Never expose your OpenAI API key in client-side code. Use environment variables or secrets management.
- Validate user input to prevent prompt injection attacks.

## 10. Advanced: Hybrid Search

Pure vector search sometimes misses exact keyword matches. Consider adding full-text search (FTS) for hybrid retrieval. PostgreSQL supports both:

```sql
ALTER TABLE documents ADD COLUMN tsv tsvector;
UPDATE documents SET tsv = to_tsvector('english', content);
CREATE INDEX idx_tsv ON documents USING gin(tsv);
```

Then combine both scores in your query. This approach is more robust for real-world applications.

## Key Takeaways

- **RAG is a game-changer** for building domain-specific AI applications without fine-tuning.
- **pgvector + Spring Boot** provides a seamless way to add vector similarity search to your existing Java stack.
- **Use the right index**: HNSW for large datasets, IVFFlat for smaller ones.
- **Chunk your documents** to improve retrieval precision.
- **Always cache embeddings** to save API costs.
- **Combine vector search with full-text search** for hybrid retrieval that handles both semantic and exact matches.
- **Security is critical**: protect API keys and sanitize inputs.

Now you have a fully functional RAG pipeline. Experiment with different embedding models, chunk sizes, and index parameters to optimize for your specific use case. Happy coding!