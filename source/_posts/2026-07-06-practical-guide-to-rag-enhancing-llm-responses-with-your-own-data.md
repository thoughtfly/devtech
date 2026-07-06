---
title: "Practical Guide to RAG: Enhancing LLM Responses with Your Own Data"
date: 2026-07-06
tags: [RAG, LLM, Java, Spring AI, Vector Database, Embeddings, Retrieval]
categories: [Java]
cover:
description: Learn to build a Retrieval-Augmented Generation (RAG) system to ground LLM outputs in your own data. Covers architecture, chunking, embeddings, retrieval, an...
---

# Practical Guide to RAG: Enhancing LLM Responses with Your Own Data

Large Language Models (LLMs) like GPT-4 or Llama 3 are incredibly powerful, but they come with a fundamental limitation: they only know what they were trained on. If you ask about your company's internal policies, a recent product update, or proprietary data, the model either hallucinates or admits ignorance. This is where **Retrieval-Augmented Generation (RAG)** comes in.

RAG is the most practical and widely adopted pattern for grounding LLM responses in external data sources—without fine-tuning. Instead of retraining the model, you retrieve relevant information from your own knowledge base at query time and feed it as context to the LLM. The result: accurate, up-to-date, and domain-specific answers.

In this guide, I’ll walk you through the core concepts, architecture, and a hands-on implementation using Java and Spring AI. By the end, you’ll have a working RAG pipeline that can answer questions based on your own documents.

---

## Why RAG and Not Fine-Tuning?

Before diving into the how, let’s address the why. When you need to incorporate new or proprietary data into an LLM, you have two main options:

1. **Fine-tuning** – Update the model’s weights on a domain-specific dataset.
2. **RAG** – Retrieve relevant documents at inference time and inject them into the prompt.

| Aspect | Fine-Tuning | RAG |
|--------|-------------|-----|
| Training cost | High (GPU hours, data prep) | None (no model training) |
| Data freshness | Stale after training | Always up-to-date |
| Hallucination risk | Still possible | Reduced (grounded in retrieved docs) |
| Implementation complexity | High (requires ML expertise) | Moderate (pipeline integration) |
| Use case | Custom behavior, style adaptation | Factual question answering, knowledge retrieval |

RAG shines when you need **factual accuracy** and **easy updates**—e.g., a customer support bot that reads the latest product documentation, or an internal Q&A system for your company wiki.

---

## Core Architecture of a RAG System

A typical RAG pipeline consists of two phases: **Indexing** (preparation) and **Retrieval + Generation** (inference).

### Indexing Phase

1. **Load documents** – PDFs, Markdown files, databases, web pages, etc.
2. **Split into chunks** – Break documents into smaller, semantically coherent pieces (e.g., 500 tokens each).
3. **Generate embeddings** – Convert each chunk into a vector using an embedding model (e.g., OpenAI’s `text-embedding-ada-002` or a local model like `BAAI/bge-small-en`).
4. **Store in vector database** – Save embeddings alongside the original text in a vector store (e.g., Pinecone, Weaviate, Qdrant, or in-memory with Chroma).

### Retrieval + Generation Phase

1. **User query** – The user asks a question.
2. **Embed query** – Convert the query into a vector using the same embedding model.
3. **Similarity search** – Query the vector database for the top-k most similar chunks (by cosine similarity or other distance metrics).
4. **Construct prompt** – Combine the retrieved chunks as context with the original query.
5. **Generate answer** – Send the prompt to the LLM and return the response.

![RAG Architecture](https://example.com/rag-architecture.png)

---

## Setting Up a RAG Pipeline with Spring AI and Java

Spring AI is a relatively new but powerful framework that abstracts away much of the boilerplate for integrating AI models into Java applications. It provides consistent APIs for embedding models, vector stores, and LLM chat clients.

### Prerequisites

- Java 17+
- Maven or Gradle
- An API key for OpenAI (or a local LLM via Ollama)
- A vector database (we’ll use an in-memory `SimpleVectorStore` for prototyping)

### Step 1: Add Dependencies

Add the following to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
    <version>1.0.0-M2</version>
</dependency>
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-pdf-document-reader</artifactId>
    <version>1.0.0-M2</version>
</dependency>
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-transformers-embedding</artifactId>
    <version>1.0.0-M2</version>
</dependency>
```

### Step 2: Configure Application Properties

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        model: gpt-4o-mini
      embedding:
        model: text-embedding-ada-002
```

### Step 3: Build the Indexing Service

```java
import org.springframework.ai.document.Document;
import org.springframework.ai.reader.pdf.PagePdfDocumentReader;
import org.springframework.ai.transformer.splitter.TokenTextSplitter;
import org.springframework.ai.vectorstore.SimpleVectorStore;
import org.springframework.ai.embedding.EmbeddingClient;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DocumentIndexingService {

    private final EmbeddingClient embeddingClient;
    private final SimpleVectorStore vectorStore;

    public DocumentIndexingService(EmbeddingClient embeddingClient) {
        this.embeddingClient = embeddingClient;
        this.vectorStore = new SimpleVectorStore(embeddingClient);
    }

    public void indexPdf(String pdfPath) {
        // 1. Load PDF
        PagePdfDocumentReader reader = new PagePdfDocumentReader(pdfPath);
        List<Document> documents = reader.get();

        // 2. Split into chunks
        TokenTextSplitter splitter = new TokenTextSplitter(500, 100); // chunkSize, overlap
        List<Document> chunks = splitter.apply(documents);

        // 3. Generate embeddings and store
        vectorStore.add(chunks);
        System.out.println("Indexed " + chunks.size() + " chunks.");
    }

    public SimpleVectorStore getVectorStore() {
        return vectorStore;
    }
}
```

### Step 4: Create the RAG Query Service

```java
import org.springframework.ai.chat.ChatClient;
import org.springframework.ai.chat.prompt.PromptTemplate;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class RagQueryService {

    private final ChatClient chatClient;
    private final VectorStore vectorStore;

    private static final String PROMPT_TEMPLATE = """
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.

            Context:
            {context}

            Question: {question}
            """;

    public RagQueryService(ChatClient chatClient, VectorStore vectorStore) {
        this.chatClient = chatClient;
        this.vectorStore = vectorStore;
    }

    public String ask(String question) {
        // 1. Retrieve relevant documents
        SearchRequest request = SearchRequest.query(question)
                .withTopK(3);
        List<Document> results = vectorStore.similaritySearch(request);

        // 2. Build context from retrieved chunks
        String context = results.stream()
                .map(Document::getContent)
                .collect(Collectors.joining("\n\n---\n\n"));

        // 3. Create prompt with context
        PromptTemplate promptTemplate = new PromptTemplate(PROMPT_TEMPLATE);
        Map<String, Object> params = new HashMap<>();
        params.put("context", context);
        params.put("question", question);

        // 4. Generate answer
        return chatClient.call(promptTemplate.create(params)).getResult().getOutput().getContent();
    }
}
```

### Step 5: Expose a REST Endpoint

```java
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/rag")
public class RagController {

    private final RagQueryService ragQueryService;
    private final DocumentIndexingService indexingService;

    public RagController(RagQueryService ragQueryService, DocumentIndexingService indexingService) {
        this.ragQueryService = ragQueryService;
        this.indexingService = indexingService;
    }

    @PostMapping("/index")
    public String index(@RequestParam String pdfPath) {
        indexingService.indexPdf(pdfPath);
        return "Indexing completed.";
    }

    @GetMapping("/ask")
    public String ask(@RequestParam String question) {
        return ragQueryService.ask(question);
    }
}
```

---

## Advanced Considerations for Production RAG

The above example gets you started, but a production-grade RAG system requires deeper thought.

### Chunking Strategy

- **Semantic chunking**: Split at natural boundaries (paragraphs, sections) rather than fixed token counts. Use `SemanticTextSplitter` in Spring AI or libraries like LangChain4j.
- **Overlap**: Add a small overlap (10-20%) between chunks to avoid cutting off important context.
- **Metadata**: Attach metadata (source file, page number, heading) to each chunk for better traceability and filtering.

### Embedding Model Selection

- **OpenAI `text-embedding-ada-002`**: Good quality, but costs money per token.
- **Local models** (e.g., `BAAI/bge-small-en`, `sentence-transformers/all-MiniLM-L6-v2`): Free, privacy-preserving, but slightly lower accuracy.
- **Hybrid search**: Combine vector similarity with keyword search (BM25) for better recall on exact matches. Many vector databases support hybrid search natively.

### Vector Database Choices

| Database | Type | Best For |
|----------|------|----------|
| Pinecone | Managed SaaS | Production, scalability |
| Weaviate | Self-hosted/Cloud | Hybrid search, filtering |
| Qdrant | Self-hosted/Cloud | High performance, filtering |
| Chroma | Embedded | Prototyping, small datasets |
| SimpleVectorStore | In-memory | Demos, testing |

### Prompt Engineering for RAG

- **Instruction clarity**: Tell the LLM to use only the provided context and to admit ignorance.
- **Source citation**: Ask the model to cite the source chunk (e.g., "According to section 3.2 of the employee handbook...").
- **Few-shot examples**: Include examples of good answers in the system prompt.

### Handling Large Documents

- **Hierarchical indexing**: Index both chunk-level and document-level embeddings. Retrieve document-level first, then chunk-level within that document.
- **Summarization**: For very long contexts, summarize chunks before retrieval or use a re-ranking step.

---

## Testing and Evaluation

How do you know your RAG system is working well? Don’t rely on gut feeling—measure.

### Key Metrics

- **Hit rate**: Percentage of queries where the retrieved chunks contain the correct answer.
- **Mean Reciprocal Rank (MRR)**: How high the correct chunk ranks in the retrieval results.
- **Answer correctness**: Compare generated answers against ground truth (often done with an LLM-as-judge).

### Evaluation Framework

```java
// Pseudo-code for automated evaluation
List<EvaluationPair> testSet = List.of(
    new EvaluationPair("What is the refund policy?", "Refunds are available within 30 days"),
    new EvaluationPair("Who is the CEO?", "John Doe")
);

for (EvaluationPair pair : testSet) {
    String answer = ragService.ask(pair.question());
    double score = computeSimilarity(answer, pair.expectedAnswer());
    System.out.println("Score: " + score);
}
```

### Common Pitfalls

- **Chunking too small**: Loses context; model can’t understand the flow.
- **Chunking too large**: Dilutes relevance; retrieval becomes fuzzy.
- **Not filtering by metadata**: Retrieves chunks from wrong documents.
- **Ignoring query rewriting**: User queries are often ambiguous. Use an LLM to rephrase the query before embedding (e.g., "Tell me about refunds" → "What is the refund policy for online purchases?").

---

## Real-World Use Cases

1. **Customer Support Chatbot** – Index product manuals and FAQ pages. The bot answers with specific instructions.
2. **Internal Knowledge Base** – Connect to Confluence, Notion, or SharePoint. Employees ask natural language questions.
3. **Legal Document Review** – Retrieve relevant clauses from contracts. Ensure citations are accurate.
4. **Medical Research** – Ground answers in peer-reviewed papers. Reduce hallucination in clinical decision support.

---

## Key Takeaways

- **RAG is the most practical way to ground LLM responses in your own data** without fine-tuning.
- **The pipeline has two phases**: indexing (chunk → embed → store) and retrieval + generation (query → search → prompt → answer).
- **Spring AI simplifies RAG in Java** with consistent APIs for embedding, vector stores, and chat clients.
- **Chunking strategy matters**: use semantic splitting with overlap and metadata.
- **Choose the right vector database** based on scale, features, and operational overhead.
- **Evaluate systematically** with hit rate, MRR, and answer correctness to avoid silent failures.
- **Production RAG requires more**: query rewriting, hybrid search, re-ranking, and careful prompt engineering.

RAG is not a silver bullet, but when implemented thoughtfully, it transforms a generic LLM into a domain expert that speaks with authority about your data. Start small, measure everything, and iterate.