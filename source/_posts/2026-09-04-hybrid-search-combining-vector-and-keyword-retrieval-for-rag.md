---
title: "Hybrid Search: Combining Vector and Keyword Retrieval for RAG"
date: 2026-09-04
tags: [RAG, Hybrid Search, Vector Search, LLM, Java, Elasticsearch]
categories: [Java]
cover: "https://images.unsplash.com/photo-1637937459053-c788742455be?w=1200&q=80&fit=crop&fm=webp"
description: Learn how hybrid search combines vector and keyword retrieval to build more accurate, robust RAG systems. Includes Java examples and best practices.
---

## The Search for Better Context

If you have built a Retrieval-Augmented Generation (RAG) pipeline, you have likely encountered a frustrating paradox: semantic search finds the "right" vibe but misses the exact facts, while keyword search finds the exact terms but misses the meaning. 

Vector search has revolutionized information retrieval. By converting text into high-dimensional embeddings, we can find documents that are semantically similar to a query. However, pure vector search has blind spots. It struggles with exact string matches, numerical comparisons, and domain-specific jargon. On the other hand, traditional keyword search (BM25) is precise but lacks semantic understanding.

The solution? Hybrid Search. By combining the semantic richness of vector embeddings with the precision of lexical keyword matching, we can build RAG systems that are both accurate and robust. In this post, we will explore why hybrid search is essential, how it works under the hood, and how to implement it using Java and Elasticsearch.

## Why Pure Vector Search Isn’t Enough

To understand the value of hybrid search, we must first appreciate the limitations of vector-only approaches. When you rely solely on cosine similarity between embeddings, you introduce several risks:

### 1. The Exact Match Problem
Imagine your knowledge base contains a specific product ID like `SKU-9928-X`. A user asks, "What is the return policy for SKU-9928-X?" A vector model might embed "return policy" and "SKU-9928-X" into vectors that are close to other product IDs or general return policy documents, but it may not prioritize the exact string match. Keyword search, using BM25, will rank the document containing the exact string `SKU-9928-X` much higher.

### 2. Numerical and Factual Precision
Vector embeddings are notoriously poor at handling numbers. If a user queries for "revenue in 2023," the vector might retrieve documents about "financial growth" or "yearly reports," but it might miss the specific table containing the exact number `1,234,567`. Keyword search can pinpoint the digits, while vector search captures the context.

### 3. Hallucination Risk
If the vector search retrieves a document that is semantically similar but factually incorrect or outdated, the LLM may generate a confident but wrong answer. Hybrid search reduces this risk by ensuring that the most relevant, precise documents are included in the context window.

### 4. Domain-Specific Jargon
In technical domains, acronyms and specialized terms are common. A vector model trained on general web text might not understand that "API" and "Application Programming Interface" are the same thing, or it might treat them as distinct concepts. Keyword search handles these acronyms perfectly.

## The Power of Combination: How Hybrid Search Works

Hybrid search does not simply average the results of two different queries. It uses a sophisticated ranking algorithm to combine scores from both vector and keyword retrievers. The most common approach involves two main components:

### Vector Retrieval (Dense Search)
This uses a pre-trained embedding model (like BERT, E5, or OpenAI’s text-embedding-ada-002) to convert the query and documents into vectors. The system calculates the cosine similarity between the query vector and document vectors. This captures semantic meaning and intent.

### Keyword Retrieval (Sparse Search)
This uses traditional information retrieval algorithms like BM25 (Best Matching 25). BM25 ranks documents based on the frequency of query terms in the document, adjusted for document length and term rarity. This captures exact matches and lexical relevance.

### Score Fusion
The final step is combining the scores. There are several strategies:

- **Reciprocal Rank Fusion (RRF):** This is the most popular method. It combines the ranks from both retrievers without needing to normalize the raw scores. The formula is:
  \[
  RRF(d) = \sum_{r \in R} \frac{1}{k + rank_r(d)}
  \]
  Where \( R \) is the set of retrievers, \( k \) is a constant (usually 60), and \( rank_r(d) \) is the rank of document \( d \) in retriever \( r \).

- **Weighted Sum:** Assign a weight to each score (e.g., 0.7 for vector, 0.3 for keyword) and sum them. This requires normalizing scores to the same range.

- **Boosting:** Apply a boost factor to one of the scores based on business logic.

## Implementing Hybrid Search with Java and Elasticsearch

Elasticsearch is a powerful search engine that natively supports hybrid search. It allows you to define a query that includes both a dense vector search and a sparse (keyword) search, and then combines them using RRF or weighted scoring.

### Prerequisites

Before we dive into the code, ensure you have:
1. An Elasticsearch cluster with the `ml` (machine learning) plugin enabled for vector search.
2. A Java project with the Elasticsearch Java Client dependency.
3. An embedding model deployed in your Elasticsearch cluster or accessible via an API.

### Step 1: Define the Index Mapping

First, we need to define an index that supports both text and dense vector fields. Here is a sample mapping:

```json
PUT /my-rag-index
{
  "mappings": {
    "properties": {
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      "doc_id": {
        "type": "keyword"
      }
    }
  }
}
```

### Step 2: Ingest Data with Embeddings

When ingesting documents, you need to generate embeddings for the `content` field and store them in the `embedding` field. You can use a library like `sentence-transformers` in Python to generate embeddings and then index them via the Java client.

```java
// Pseudo-code for indexing a document
Document doc = Document.of(d -> d
    .field("content", "The quick brown fox jumps over the lazy dog.")
    .field("embedding", Arrays.asList(0.1, 0.2, ...)) // 1536 dimensions
    .field("doc_id", "doc-1")
);

IndexResponse response = client.index(i -> i
    .index("my-rag-index")
    .id("doc-1")
    .document(doc)
);
```

### Step 3: Execute Hybrid Search

Now, let’s write the Java code to perform a hybrid search. We will use the Elasticsearch Java High-Level REST Client (or the new client library) to construct a query that combines vector and keyword search.

```java
import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.query_dsl.*;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.json.JsonData;

import java.util.List;

public class HybridSearchExample {

    public static void main(String[] args) throws Exception {
        ElasticsearchClient client = getClient();

        // 1. Prepare the query
        String queryText = "What is the return policy for SKU-9928-X?";
        List<Float> queryEmbedding = generateEmbedding(queryText); // Your embedding logic

        // 2. Build the hybrid query
        Query hybridQuery = Query.of(q -> q
            .hybrid(h -> h
                .queries(
                    // Vector query
                    Query.of(inner -> inner
                        .knn(k -> k
                            .field("embedding")
                            .queryVector(queryEmbedding)
                            .k(10)
                        )
                    ),
                    // Keyword query
                    Query.of(inner -> inner
                        .multiMatch(m -> m
                            .query(queryText)
                            .fields("content", "doc_id")
                        )
                    )
                )
                // Use Reciprocal Rank Fusion
                .rankingSignal(r -> r
                    .reciprocalRankFusion(rf -> rf
                        .constant(60)
                    )
                )
            )
        );

        // 3. Execute the search
        SearchRequest request = SearchRequest.of(s -> s
            .index("my-rag-index")
            .query(hybridQuery)
            .size(5)
        );

        SearchResponse response = client.search(request, MyDocument.class);

        // 4. Process results
        response.hits().hits().forEach(hit -> {
            System.out.println("Score: " + hit.score());
            System.out.println("Content: " + hit.source().getContent());
        });
    }

    private static List<Float> generateEmbedding(String text) {
        // Call your embedding API or model here
        return List.of(0.1f, 0.2f, ...); 
    }

    private static ElasticsearchClient getClient() {
        // Initialize your Elasticsearch client
        return null;
    }
}
```

### Step 4: Using Reciprocal Rank Fusion (RRF)

In the example above, we used the `hybrid` query with `reciprocalRankFusion`. This is the recommended approach because it is robust and does not require score normalization. The `constant` parameter (usually 60) controls the weight of high-ranked documents. A higher constant means less penalty for lower ranks.

## Best Practices for Hybrid Search in RAG

Implementing hybrid search is straightforward, but optimizing it for production RAG systems requires attention to detail. Here are some best practices:

### 1. Tune the Embedding Model
The quality of your vector search depends heavily on the embedding model. For technical documents, consider using models fine-tuned on code or scientific papers (e.g., E5-large, CodeBERT). For general knowledge, models like text-embedding-ada-002 or OpenAI’s newer models are excellent choices.

### 2. Preprocess Your Data
Clean your text before embedding. Remove HTML tags, normalize whitespace, and handle special characters. For keyword search, ensure your analyzer is appropriate. Use custom analyzers for domain-specific terms.

### 3. Balance the Weights
While RRF is a great default, you may need to adjust the weights. If your use case is heavily dependent on exact matches (e.g., searching for product IDs), you might boost the keyword query. If semantic understanding is more important (e.g., chatbots), you might boost the vector query.

### 4. Handle Chunking Strategically
Hybrid search works best when your documents are chunked appropriately. Too large chunks dilute the signal; too small chunks lose context. Aim for chunks that are semantically coherent and between 200-500 tokens.

### 5. Monitor and Evaluate
Use metrics like Recall@K, MRR (Mean Reciprocal Rank), and NDCG to evaluate your hybrid search. Compare it against pure vector and pure keyword search to ensure the combination adds value.

## Common Pitfalls to Avoid

### Over-Reliance on Vectors
Do not assume that vector search will solve all retrieval problems. Always include a keyword component for exact matches.

### Ignoring Language Specifics
Embedding models are often biased towards English. If your content is in other languages, use multilingual models (e.g., multilingual-e5-large).

### Not Updating Embeddings
When documents change, you must update their embeddings. Incremental updates can be complex, so consider re-indexing periodically.

## Conclusion

Hybrid search is not just a nice-to-have; it is a critical component for building reliable RAG systems. By combining the semantic understanding of vector search with the precision of keyword search, you can significantly improve the accuracy and robustness of your applications. 

In this post, we explored the limitations of pure vector search, the mechanics of hybrid search, and how to implement it using Java and Elasticsearch. We also discussed best practices and common pitfalls. As you move forward, remember that the key to success is experimentation. Test different models, weights, and chunking strategies to find the optimal configuration for your specific use case.

## Key Takeaways

- **Hybrid search combines vector and keyword retrieval** to leverage the strengths of both approaches, improving accuracy and robustness in RAG systems.
- **Vector search excels at semantic similarity** but struggles with exact matches, numbers, and domain-specific jargon.
- **Keyword search (BM25) provides precision** for exact terms and numerical values but lacks semantic understanding.
- **Reciprocal Rank Fusion (RRF) is the preferred method** for combining scores, as it is robust and does not require score normalization.
- **Implementation with Elasticsearch** is straightforward using the `hybrid` query type, allowing you to define both KNN and multi-match queries in a single request.
- **Best practices include** tuning embedding models, preprocessing data, balancing weights, strategic chunking, and continuous monitoring and evaluation.
- **Avoid over-reliance on vectors** and always include a keyword component for exact matches, especially in technical domains.