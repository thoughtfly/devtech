---
title: "Building a Local RAG System with Ollama and LangChain4j"
date: 2026-08-16
tags: [RAG, Ollama, LangChain4j, Java, LLM, AI]
categories: [Java]
cover: "https://picsum.photos/seed/building-a-local-rag-system-with-ollama-and-langchain4j/1200/630.webp"
description: Learn to build a fully local RAG system using Ollama and LangChain4j. Step-by-step guide with code examples, embeddings, and retrieval in Java.
---

## Introduction

In the rapidly evolving landscape of AI, Retrieval-Augmented Generation (RAG) has emerged as a powerful technique to enhance the capabilities of Large Language Models (LLMs) by grounding them with external knowledge. While cloud-based solutions are popular, there's a growing need for local, privacy-preserving, and cost-effective alternatives. Enter **Ollama** and **LangChain4j**.

Ollama simplifies running LLMs locally, and LangChain4j brings the power of LangChain to the JVM. In this guide, we'll build a fully local RAG system using these two tools. You'll learn how to ingest documents, generate embeddings, store them in a vector store, and query the system with a natural language interface—all without any cloud dependencies.

By the end, you'll have a solid understanding of the components involved and a working Java application you can extend for your own use cases.

## Prerequisites

Before diving in, ensure you have the following installed:

- **Java 17+** (we'll use Java 21 features for demonstration)
- **Maven** (or Gradle, but we'll use Maven)
- **Ollama** – [Download and install](https://ollama.com/download) for your OS

Once Ollama is installed, pull the models we'll need:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

`llama3.2` is a powerful chat model, and `nomic-embed-text` is a high-quality embedding model. Both run locally.

## Understanding RAG

RAG combines a retrieval system with a generative model. The process works in two phases:

1. **Indexing**: Documents are split into chunks, each chunk is converted into a vector embedding, and the embeddings are stored in a vector database.
2. **Querying**: A user query is embedded, similar vectors are retrieved, and the retrieved context is fed to the LLM along with the query to generate an answer.

This approach ensures the model has access to relevant, up-to-date information without retraining.

## Setting Up the Project

Create a new Maven project and add the LangChain4j dependencies. We'll use the `langchain4j` and `langchain4j-ollama` modules, along with a vector store. For simplicity, we'll use the in-memory `EmbeddingStore` from LangChain4j, but you can easily swap it for a persistent store like Pinecone or Weaviate.

**pom.xml**

```xml
<dependencies>
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j</artifactId>
        <version>0.35.0</version>
    </dependency>
    <dependency>
        <groupId>dev.langchain4j</groupId>
        <artifactId>langchain4j-ollama</artifactId>
        <version>0.35.0</version>
    </dependency>
    <!-- For logging (optional) -->
    <dependency>
        <groupId>org.slf4j</groupId>
        <artifactId>slf4j-simple</artifactId>
        <version>2.0.13</version>
    </dependency>
</dependencies>
```

Now, let's write the core code.

## Building the RAG Pipeline

We'll create a class `LocalRagSystem` that handles document ingestion and querying.

### Step 1: Initialize Models and Embedding Store

First, we need to set up the chat model and embedding model using Ollama's API.

```java
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.model.ollama.OllamaEmbeddingModel;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.parser.TextDocumentParser;
import dev.langchain4j.data.document.loader.FileSystemDocumentLoader;
import dev.langchain4j.chain.ConversationalRetrievalChain;

public class LocalRagSystem {
    private static final String OLLAMA_BASE_URL = "http://localhost:11434";
    private static final String CHAT_MODEL = "llama3.2";
    private static final String EMBEDDING_MODEL = "nomic-embed-text";

    public static void main(String[] args) {
        // Initialize models
        OllamaChatModel chatModel = OllamaChatModel.builder()
                .baseUrl(OLLAMA_BASE_URL)
                .modelName(CHAT_MODEL)
                .temperature(0.7)
                .build();

        OllamaEmbeddingModel embeddingModel = OllamaEmbeddingModel.builder()
                .baseUrl(OLLAMA_BASE_URL)
                .modelName(EMBEDDING_MODEL)
                .build();

        // Create embedding store (in-memory)
        InMemoryEmbeddingStore<TextSegment> embeddingStore = new InMemoryEmbeddingStore<>();

        // ... rest of the code
    }
}
```

### Step 2: Ingest Documents

We'll load a text document from the filesystem, split it into chunks, embed each chunk, and store it.

```java
import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;

// Inside main method after initializing models

// Load document (e.g., "data/sample.txt")
Document document = FileSystemDocumentLoader.loadDocument("data/sample.txt", new TextDocumentParser());

// Split document into chunks of 500 characters with overlap
List<TextSegment> segments = DocumentSplitters.recursive(500, 50).split(document);

// Ingest segments into embedding store
EmbeddingStoreIngestor ingestor = EmbeddingStoreIngestor.builder()
        .embeddingModel(embeddingModel)
        .embeddingStore(embeddingStore)
        .build();
ingestor.ingest(segments);

System.out.println("Ingested " + segments.size() + " segments.");
```

### Step 3: Create Conversational Retrieval Chain

Now we'll build a chain that retrieves relevant segments and feeds them to the chat model.

```java
import dev.langchain4j.chain.ConversationalRetrievalChain;
import dev.langchain4j.retriever.EmbeddingStoreRetriever;

// Inside main method after ingestion

EmbeddingStoreRetriever retriever = EmbeddingStoreRetriever.builder()
        .embeddingStore(embeddingStore)
        .embeddingModel(embeddingModel)
        .maxResults(5) // retrieve top 5 segments
        .build();

ConversationalRetrievalChain chain = ConversationalRetrievalChain.builder()
        .chatLanguageModel(chatModel)
        .retriever(retriever)
        .build();

// Now we can ask questions
String answer = chain.execute("What is the main topic of the document?");
System.out.println(answer);
```

### Full Example Code

Combine everything into a single class. Here's the complete `LocalRagSystem.java`:

```java
import dev.langchain4j.chain.ConversationalRetrievalChain;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.loader.FileSystemDocumentLoader;
import dev.langchain4j.data.document.parser.TextDocumentParser;
import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.model.ollama.OllamaEmbeddingModel;
import dev.langchain4j.retriever.EmbeddingStoreRetriever;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;

import java.util.List;

public class LocalRagSystem {
    private static final String OLLAMA_BASE_URL = "http://localhost:11434";
    private static final String CHAT_MODEL = "llama3.2";
    private static final String EMBEDDING_MODEL = "nomic-embed-text";

    public static void main(String[] args) {
        // 1. Initialize models
        OllamaChatModel chatModel = OllamaChatModel.builder()
                .baseUrl(OLLAMA_BASE_URL)
                .modelName(CHAT_MODEL)
                .temperature(0.7)
                .build();

        OllamaEmbeddingModel embeddingModel = OllamaEmbeddingModel.builder()
                .baseUrl(OLLAMA_BASE_URL)
                .modelName(EMBEDDING_MODEL)
                .build();

        // 2. Create embedding store
        EmbeddingStore<TextSegment> embeddingStore = new InMemoryEmbeddingStore<>();

        // 3. Load and ingest document
        Document document = FileSystemDocumentLoader.loadDocument("data/sample.txt", new TextDocumentParser());
        List<TextSegment> segments = DocumentSplitters.recursive(500, 50).split(document);

        EmbeddingStoreIngestor ingestor = EmbeddingStoreIngestor.builder()
                .embeddingModel(embeddingModel)
                .embeddingStore(embeddingStore)
                .build();
        ingestor.ingest(segments);
        System.out.println("Ingested " + segments.size() + " segments.");

        // 4. Build retrieval chain
        EmbeddingStoreRetriever retriever = EmbeddingStoreRetriever.builder()
                .embeddingStore(embeddingStore)
                .embeddingModel(embeddingModel)
                .maxResults(5)
                .build();

        ConversationalRetrievalChain chain = ConversationalRetrievalChain.builder()
                .chatLanguageModel(chatModel)
                .retriever(retriever)
                .build();

        // 5. Ask questions
        String question = "What is the main topic of the document?";
        String answer = chain.execute(question);
        System.out.println("Question: " + question);
        System.out.println("Answer: " + answer);
    }
}
```

## Testing the System

Create a sample text file at `data/sample.txt` with some content, e.g., about the history of Java. Then run the application. You should see output like:

```
Ingested 4 segments.
Question: What is the main topic of the document?
Answer: The main topic of the document is the history and evolution of the Java programming language.
```

The system retrieves relevant chunks and generates a coherent answer. To test further, ask follow-up questions.

## How It Works Under the Hood

Let's break down what happens when you ask a question:

1. **Query Embedding**: The query is converted into a vector using `nomic-embed-text`.
2. **Similarity Search**: The vector is compared to all stored segment embeddings using cosine similarity. The top `maxResults` segments are returned.
3. **Prompt Construction**: The retrieved segments are inserted into a prompt template along with the original question. LangChain4j's `ConversationalRetrievalChain` handles this automatically.
4. **Generation**: The chat model (`llama3.2`) processes the prompt and generates an answer.

This process ensures the answer is grounded in the provided documents.

## Customizing the Pipeline

### Changing the Chunk Size

The `DocumentSplitters.recursive(500, 50)` splits documents into chunks of 500 characters with a 50-character overlap. You can tune these based on your data. Smaller chunks are more precise but may lose context; larger chunks retain context but may be less relevant.

### Using a Persistent Vector Store

For production, you'll want a persistent store. LangChain4j supports many, including Pinecone, Weaviate, and Chroma. Here's an example with Chroma (requires running Chroma separately):

```java
import dev.langchain4j.store.embedding.chroma.ChromaEmbeddingStore;

ChromaEmbeddingStore embeddingStore = ChromaEmbeddingStore.builder()
        .baseUrl("http://localhost:8000")
        .collectionName("my_collection")
        .build();
```

### Adding Memory

The `ConversationalRetrievalChain` automatically maintains chat memory. You can control it by passing a `ChatMemory` object.

## Performance Considerations

Running models locally is resource-intensive. Here are some tips:

- **Use a smaller chat model** like `llama3.2:1b` for faster responses if accuracy is less critical.
- **Quantize models** – Ollama supports quantizations like `q4_K_M` to reduce memory usage.
- **Batch embedding** – When ingesting many documents, process them in batches to avoid memory spikes.

## Troubleshooting Common Issues

- **Ollama not reachable**: Ensure Ollama is running (`ollama serve`).
- **Model not found**: Pull the model first (`ollama pull llama3.2`).
- **Out of memory**: Reduce chunk size or use a smaller model.

## Conclusion

In this post, we've built a fully local RAG system using Ollama and LangChain4j. We covered the essential components: document ingestion, embedding, retrieval, and generation. The code is simple yet extensible, allowing you to integrate various vector stores and models.

Local RAG systems offer significant advantages in terms of privacy, cost, and control. With the tools we've used, you can build powerful AI applications entirely on your own hardware.

## Key Takeaways

- **RAG** enhances LLMs by retrieving relevant context from documents, improving accuracy and relevance.
- **Ollama** provides an easy way to run LLMs and embedding models locally.
- **LangChain4j** offers a Java-friendly API to build RAG pipelines with minimal boilerplate.
- **In-memory stores** are great for prototyping; switch to persistent stores for production.
- **Tuning chunk size and retrieval parameters** can significantly impact answer quality.
- **Local RAG** ensures data privacy and reduces dependency on cloud services.

Now, go ahead and build your own local RAG system. Happy coding!