---
title: "Semantic Search with Vector Databases: A Developer's Guide"
date: 2026-07-08
tags: [semantic search, vector databases, embeddings, machine learning, information retrieval]
categories: [Java]
cover:
description: Learn to build semantic search using vector databases like Pinecone and Weaviate. Covers embeddings, indexing, and querying with code examples in Python and...
---

# Semantic Search with Vector Databases: A Developer's Guide

Imagine searching for "warm, cozy places to read" and getting results for a fireplace cafe—not because the words match, but because the meaning aligns. That's the power of semantic search. Unlike traditional keyword-based search, semantic search understands intent and context. In this guide, I'll walk you through building a semantic search system using vector databases, from embeddings to production deployment.

## Why Semantic Search Matters

Traditional search relies on exact keyword matches. If a user types "affordable laptops," a keyword search might miss results that say "budget-friendly notebooks" or "cheap computers." Semantic search solves this by representing text as dense vectors (embeddings) that capture meaning. When you query, the system finds vectors closest in semantic space, not just lexical matches.

**Real-world use cases:**
- E-commerce product discovery
- Enterprise document retrieval
- Customer support ticket routing
- Recommendation systems

## The Vector Database Landscape

Vector databases are purpose-built for storing and querying high-dimensional vectors. Here are the top contenders:

| Database | Type | Strengths |
|----------|------|-----------|
| Pinecone | Managed | Zero ops, serverless, low latency |
| Weaviate | Open-source | Hybrid search, GraphQL, modular |
| Qdrant | Open-source | Rust-based, fast, disk-based |
| Milvus | Open-source | Distributed, GPU acceleration |

For this guide, I'll use Weaviate because it's developer-friendly and supports hybrid search out of the box.

## Step 1: Generating Embeddings

Embeddings are the heart of semantic search. You can choose from several models:

- **OpenAI embeddings** (`text-embedding-ada-002`): 1536 dimensions, good for general use
- **Sentence Transformers** (e.g., `all-MiniLM-L6-v2`): 384 dimensions, lightweight
- **Cohere embeddings**: 1024 dimensions, domain-specific options

Let's generate embeddings using Python and Hugging Face's Sentence Transformers:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

texts = [
    "A warm cafe with comfortable armchairs by the fireplace",
    "Budget-friendly laptops for students under $500",
    "High-performance gaming desktop with RTX 4080"
]

embeddings = model.encode(texts)
print(f"Embedding shape: {embeddings.shape}")  # (3, 384)
```

**Pro tip:** Normalize embeddings to unit length for better cosine similarity accuracy.

```python
embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
```

## Step 2: Setting Up Weaviate

Spin up Weaviate using Docker Compose:

```yaml
# docker-compose.yml
version: '3.4'
services:
  weaviate:
    image: semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
    environment:
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
```

Start the service:

```bash
docker-compose up -d
```

## Step 3: Creating a Schema and Inserting Data

Define a schema for your data. Here's how to create a class for products:

```python
import weaviate

client = weaviate.Client("http://localhost:8080")

schema = {
    "class": "Product",
    "description": "A product with a description and embedding",
    "properties": [
        {
            "name": "title",
            "dataType": ["string"],
            "description": "Product title"
        },
        {
            "name": "description",
            "dataType": ["text"],
            "description": "Product description"
        },
        {
            "name": "price",
            "dataType": ["number"],
            "description": "Price in USD"
        }
    ],
    "vectorizer": "none"  # We'll provide our own vectors
}

client.schema.create_class(schema)
```

Now insert data with precomputed embeddings:

```python
products = [
    {
        "title": "Cozy Fireplace Cafe",
        "description": "A warm cafe with comfortable armchairs by the fireplace",
        "price": 5.50,
        "embedding": embeddings[0].tolist()
    },
    {
        "title": "Student Laptop Pro",
        "description": "Budget-friendly laptops for students under $500",
        "price": 499.99,
        "embedding": embeddings[1].tolist()
    },
    {
        "title": "Ultra Gaming Rig",
        "description": "High-performance gaming desktop with RTX 4080",
        "price": 2499.99,
        "embedding": embeddings[2].tolist()
    }
]

for product in products:
    client.data_object.create(
        data_object={
            "title": product["title"],
            "description": product["description"],
            "price": product["price"]
        },
        class_name="Product",
        vector=product["embedding"]
    )
```

## Step 4: Performing Semantic Search

Query with a natural language phrase:

```python
def semantic_search(query_text, top_k=5):
    # Generate query embedding
    query_embedding = model.encode([query_text])[0]
    query_embedding = query_embedding / np.linalg.norm(query_embedding)
    
    # Search in Weaviate
    result = client.query.get(
        "Product", ["title", "description", "price"]
    ).with_near_vector({
        "vector": query_embedding.tolist()
    }).with_limit(top_k).do()
    
    return result["data"]["Get"]["Product"]

# Example query
results = semantic_search("places to relax and read a book")
for r in results:
    print(f"{r['title']} - ${r['price']}: {r['description']}")
```

Output:
```
Cozy Fireplace Cafe - $5.5: A warm cafe with comfortable armchairs by the fireplace
```

Notice it didn't match "relax" or "book" literally—it understood the semantics.

## Step 5: Hybrid Search (Vector + Keyword)

Pure semantic search can miss exact matches. Hybrid search combines vector and keyword scoring for the best of both worlds. In Weaviate, enable hybrid search:

```python
def hybrid_search(query_text, alpha=0.5, top_k=5):
    result = client.query.get(
        "Product", ["title", "description", "price"]
    ).with_hybrid({
        "query": query_text,
        "alpha": alpha  # 0 = pure keyword, 1 = pure vector
    }).with_limit(top_k).do()
    
    return result["data"]["Get"]["Product"]

# Search for "laptop" with hybrid
results = hybrid_search("laptop", alpha=0.7)
for r in results:
    print(f"{r['title']} - ${r['price']}")
```

## Step 6: Filtering and Metadata

Vector databases support metadata filtering. Let's add a category and filter by price:

```python
# Add category to schema
client.schema.property.create(
    "Product",
    {
        "name": "category",
        "dataType": ["string"]
    }
)

# Insert with category
product = {
    "title": "Ergonomic Office Chair",
    "description": "Comfortable chair with lumbar support for long work hours",
    "price": 299.99,
    "category": "furniture",
    "embedding": model.encode(["Comfortable chair with lumbar support"])[0].tolist()
}
client.data_object.create(
    data_object={
        "title": product["title"],
        "description": product["description"],
        "price": product["price"],
        "category": product["category"]
    },
    class_name="Product",
    vector=product["embedding"]
)

# Search with filter
result = client.query.get(
    "Product", ["title", "price", "category"]
).with_near_vector({
    "vector": query_embedding.tolist()
}).with_where({
    "path": ["price"],
    "operator": "LessThan",
    "valueNumber": 500
}).with_limit(5).do()
```

## Step 7: Production Considerations

### Scaling Vector Databases

- **Indexing**: Use HNSW (Hierarchical Navigable Small World) for high recall. In Weaviate, configure index parameters:

```python
class_config = {
    "vectorIndexConfig": {
        "distance": "cosine",
        "efConstruction": 128,
        "ef": -1,
        "maxConnections": 64
    }
}
client.schema.create_class({
    "class": "Product",
    "vectorIndexConfig": class_config["vectorIndexConfig"]
})
```

- **Batching**: Insert data in batches of 100-1000 for performance.
- **Caching**: Cache frequent queries using Redis or in-memory cache.
- **Monitoring**: Track latency, recall, and indexing speed with Prometheus.

### Embedding Model Selection

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good | General purpose, low latency |
| `text-embedding-ada-002` | 1536 | Slow | Excellent | High accuracy, budget for API costs |
| `BAAI/bge-large-en-v1.5` | 1024 | Medium | Very good | Open-source, competitive with OpenAI |

**Rule of thumb:** Start with `all-MiniLM-L6-v2` for prototyping, then benchmark with larger models.

## Step 8: Building a REST API (Java Example)

Let's expose our search as a REST API using Spring Boot:

```java
// SearchController.java
@RestController
@RequestMapping("/api/search")
public class SearchController {

    @Autowired
    private WeaviateClient weaviateClient;
    
    @Autowired
    private EmbeddingService embeddingService;
    
    @PostMapping("/semantic")
    public ResponseEntity<List<Product>> semanticSearch(
            @RequestBody SearchRequest request) {
        
        // Generate embedding
        float[] queryVector = embeddingService.getEmbedding(request.getQuery());
        
        // Build Weaviate query
        GraphQLQuery query = GraphQLQuery.builder()
            .withClassName("Product")
            .withFields("title description price")
            .withNearVector(NearVector.builder()
                .vector(queryVector)
                .build())
            .withLimit(request.getTopK())
            .build();
        
        List<Product> results = weaviateClient.query(query);
        return ResponseEntity.ok(results);
    }
}

// EmbeddingService.java
@Service
public class EmbeddingService {
    
    private final SentenceTransformer model;
    
    public EmbeddingService() {
        this.model = new SentenceTransformer("all-MiniLM-L6-v2");
    }
    
    public float[] getEmbedding(String text) {
        float[] embedding = model.encode(text);
        // Normalize
        float norm = 0;
        for (float v : embedding) norm += v * v;
        norm = (float) Math.sqrt(norm);
        for (int i = 0; i < embedding.length; i++) {
            embedding[i] /= norm;
        }
        return embedding;
    }
}
```

## Step 9: Evaluation and Tuning

Measure search quality using:

- **Recall@k**: Fraction of relevant results in top k
- **Mean Reciprocal Rank (MRR)**: Reciprocal rank of first relevant result
- **Normalized Discounted Cumulative Gain (NDCG)**: Accounts for graded relevance

Create a test set with labeled queries and expected results. Use Weaviate's built-in evaluation or custom scripts:

```python
from sklearn.metrics import ndcg_score

def evaluate(queries, relevant_docs, model, client, k=10):
    scores = []
    for query, relevant in zip(queries, relevant_docs):
        results = semantic_search(query, top_k=k)
        # Binary relevance: 1 if in relevant, else 0
        relevance = [1 if r['title'] in relevant else 0 for r in results]
        # Pad if fewer than k results
        relevance += [0] * (k - len(relevance))
        scores.append(relevance)
    
    return ndcg_score([[1]*k for _ in queries], scores, k=k)
```

## Key Takeaways

- **Semantic search** captures meaning, not just keywords, using dense vector embeddings.
- **Vector databases** like Weaviate, Pinecone, and Qdrant are optimized for similarity search at scale.
- **Hybrid search** (vector + keyword) often outperforms pure semantic search in production.
- **Embedding model choice** impacts quality and latency; benchmark multiple models.
- **Metadata filtering** is essential for practical applications (e.g., price ranges, categories).
- **Productionize** with proper indexing, batching, caching, and monitoring.
- **Evaluate** using metrics like Recall@k and NDCG to iterate on your system.

Semantic search isn't just a buzzword—it's a practical tool that dramatically improves user experience. Start small, iterate, and watch your search results become smarter.