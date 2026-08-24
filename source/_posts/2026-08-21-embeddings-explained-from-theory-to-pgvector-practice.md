---
title: "Embeddings Explained: From Theory to pgvector Practice"
date: 2026-08-21
tags: [embeddings, pgvector, vector search, PostgreSQL, machine learning]
categories: [Java, Database]
cover: "https://images.unsplash.com/photo-1770654324754-1eb9854008aa?w=1200&q=80&fit=crop&fm=webp"
description: Learn how embeddings work, from vector math to semantic search, and implement them with pgvector in PostgreSQL for scalable AI applications.
---

## Introduction

Imagine you have a million documents and you need to find the ones most similar to a query like "How to reset my password?" Traditional keyword search might miss documents that use different wording, like "changing your login credentials." This is where embeddings come in—they convert text, images, and other data into numerical vectors that capture semantic meaning, enabling search by concept rather than exact words.

In this post, we'll demystify embeddings: what they are, how they're created, and how to use them in practice with pgvector, a PostgreSQL extension that brings vector similarity search to your database. By the end, you'll be able to implement semantic search in your own applications.

## What Are Embeddings?

At their core, embeddings are dense numerical representations of data. For text, an embedding model transforms a sentence (or token) into an array of floating-point numbers, typically hundreds to thousands of dimensions. For example, the phrase "cat" might become `[0.2, -0.1, 0.7, ...]`. The magic is that these numbers are learned so that semantically similar items have vectors that are close together in the vector space.

### Why Dense Vectors?

Traditional methods like one-hot encoding create sparse, high-dimensional vectors where each word is a separate dimension, and similarity is based on exact matches. Embeddings, on the other hand, are dense—every dimension is meaningful, and similarity is measured by distance or angle between vectors. This allows for nuanced relationships: the vector for "king" minus "man" plus "woman" approximates the vector for "queen."

### How Embeddings Are Generated

Modern embeddings come from neural networks, often transformer models like BERT or GPT. These models are trained on massive text corpora to predict words in context, learning to map words and phrases to vectors that encode semantic and syntactic information. For images, convolutional neural networks (CNNs) produce embeddings that capture visual features. The key is that the model outputs a fixed-size vector for any input, regardless of input length.

## Vector Similarity: The Math Behind It

Once you have vectors, you need a way to measure similarity. The most common metrics are:

- **Cosine Similarity**: Measures the cosine of the angle between two vectors. It ranges from -1 (opposite) to 1 (identical), with 0 meaning orthogonal. It's popular for text embeddings because it's invariant to vector magnitude, which often carries little semantic meaning.

  Formula: `cosine_similarity(A, B) = (A · B) / (||A|| * ||B||)`

- **Euclidean Distance**: The straight-line distance between vectors. It's sensitive to magnitude, so it's used when magnitude matters (e.g., in some image embeddings). Lower distance means higher similarity.

- **Dot Product**: The raw dot product, which is fast but not normalized. It's used when you care about both direction and magnitude, and it's the default in some libraries.

In practice, for text embeddings, cosine similarity is the go-to choice. With pgvector, you can store vectors and compute these distances efficiently using indexes.

## Introduction to pgvector

[pgvector](https://github.com/pgvector/pgvector) is an open-source PostgreSQL extension that adds a `vector` data type and supports exact and approximate nearest neighbor search. It's a game-changer because it lets you keep your embeddings in the same database as your application data, avoiding the need for a separate vector database and the associated data synchronization overhead.

### Key Features

- **Vector Data Type**: Store arrays of floats (up to 2000 dimensions by default).
- **Distance Operators**: `<->` for Euclidean distance, `<#>` for negative inner product, `<=>` for cosine distance.
- **Indexing**: Supports IVFFlat and HNSW indexes for fast approximate search.
- **Integration**: Works with standard PostgreSQL features like transactions, backups, and SQL.

### Installation

Installing pgvector is straightforward. On Ubuntu, you can use the package manager:

```bash
sudo apt-get install postgresql-16-pgvector
```

Or compile from source:

```bash
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Then enable the extension in your database:

```sql
CREATE EXTENSION vector;
```

## Storing Embeddings with pgvector

Let's create a table to store movie descriptions and their embeddings. We'll use a dimension of 384, which is common for models like `all-MiniLM-L6-v2`.

```sql
CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    title TEXT,
    description TEXT,
    embedding vector(384)
);
```

To insert a row, you provide the vector as a string like `'[0.1, 0.2, ...]'`:

```sql
INSERT INTO movies (title, description, embedding)
VALUES ('Inception', 'A thief who steals corporate secrets through dream-sharing technology.', '[0.123, 0.456, ...]');
```

In practice, you'll generate embeddings using a library like Hugging Face's `sentence-transformers` in Python, or via an API like OpenAI's. Here's a Python snippet to generate an embedding:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode('A thief who steals corporate secrets through dream-sharing technology.')
# Convert to list and insert into PostgreSQL
```

## Querying for Similarity

To find movies similar to a query, compute the query's embedding and find the closest vectors in the database. Here's a SQL query using cosine distance:

```sql
SELECT title, description, 1 - (embedding <=> '[0.123, 0.456, ...]') AS similarity
FROM movies
ORDER BY embedding <=> '[0.123, 0.456, ...]'
LIMIT 5;
```

The `<=>` operator returns cosine distance (0 for identical, 2 for opposite). Subtracting from 1 gives cosine similarity. The lower the distance, the more similar.

## Indexing for Performance

Without an index, a query scans all rows, which is fine for small datasets but becomes a bottleneck with millions of rows. pgvector offers two index types:

- **IVFFlat**: Inverted File with Flat Compression. It partitions the dataset into lists (like clusters). During search, it only looks in the most promising lists. It requires a training phase with representative data.
- **HNSW**: Hierarchical Navigable Small World. It builds a multi-layer graph that allows fast approximate search without a training phase. It's generally faster but uses more memory.

### Creating an Index

For IVFFlat, you need to specify the number of lists (use `rows / 1000` as a heuristic, up to 1000). Here's an example:

```sql
CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

For HNSW, it's simpler:

```sql
CREATE INDEX ON movies USING hnsw (embedding vector_cosine_ops);
```

Note: For HNSW, you can also specify `m` (max connections per node) and `ef_construction` (build time vs. accuracy trade-off).

## Practical Example: Semantic Search in a Java Application

Let's see how to integrate pgvector into a Java Spring Boot application. We'll use Spring Data JPA and a custom repository method.

### Maven Dependencies

Add the PostgreSQL JDBC driver and Spring Data JPA:

```xml
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.7.3</version>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
```

### Entity Mapping

Define an entity for the `movies` table. Since `vector` is not a standard type, we'll use a custom Hibernate type. You can use [hibernate-types](https://github.com/vladmihalcea/hibernate-types) or implement a simple `UserType`. For brevity, here's a simple approach using a `String` column and casting in SQL.

```java
@Entity
@Table(name = "movies")
public class Movie {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;
    private String description;

    @Column(columnDefinition = "vector(384)")
    private String embedding; // store as string for simplicity

    // getters and setters
}
```n```java
@Repository
public interface MovieRepository extends JpaRepository<Movie, Long> {
    @Query(value = "SELECT * FROM movies ORDER BY embedding <=> :embedding LIMIT :limit", nativeQuery = true)
    List<Movie> findSimilar(@Param("embedding") String embedding, @Param("limit") int limit);
}
```

### Generating Embeddings in Java

You can use a library like [DJL](https://djl.ai) (Deep Java Library) to generate embeddings. Here's an example using a pre-trained BERT model:

```java
import ai.djl.Application;
import ai.djl.ModelException;
import ai.djl.inference.Predictor;
import ai.djl.modality.nlp.embedding.TextEmbedding;
import ai.djl.repository.zoo.Criteria;
import ai.djl.repository.zoo.ModelZoo;
import ai.djl.repository.zoo.ZooModel;

Criteria<TextEmbedding, float[]> criteria = Criteria.builder()
        .optApplication(Application.NLP.TEXT_EMBEDDING)
        .setTypes(TextEmbedding.class, float[].class)
        .build();

ZooModel<TextEmbedding, float[]> model = ModelZoo.loadModel(criteria);
Predictor<TextEmbedding, float[]> predictor = model.newPredictor();

float[] embedding = predictor.predict(new TextEmbedding("Your query text"));
```

Then convert the float array to a string for SQL.

### Putting It Together

In your service, generate the query embedding, call the repository, and return the results:

```java
@Service
public class SearchService {
    @Autowired
    private MovieRepository movieRepository;

    public List<Movie> search(String query) {
        float[] embedding = generateEmbedding(query);
        String vectorString = Arrays.toString(embedding);
        return movieRepository.findSimilar(vectorString, 5);
    }
}
```

## Best Practices and Pitfalls

### Choose the Right Embedding Model

The quality of your embeddings directly impacts search relevance. Models like `all-MiniLM-L6-v2` are fast and good for general text, but for domain-specific data (e.g., legal or medical), consider fine-tuned models. Always test on your data.

### Normalize Vectors for Cosine Similarity

If you use cosine distance, you can pre-normalize vectors to unit length, which makes cosine distance equivalent to Euclidean distance. This can improve index performance. In SQL, you can normalize on insert:

```sql
INSERT INTO movies (title, description, embedding)
VALUES ('...', '...', normalize_embedding('[0.1, 0.2, ...]'));
```

But pgvector doesn't have a built-in normalize function, so you'd do it in your application code.

### Index Tuning

IVFFlat requires training after data insertion. If you add a lot of data after creating the index, you may need to rebuild it:

```sql
CREATE INDEX ... ; 
-- after inserting data
REINDEX INDEX movies_embedding_idx;
```

HNSW doesn't need training but consumes more memory. Start with HNSW for simplicity, then tune.

### Handle High-Dimensional Vectors

While pgvector supports up to 2000 dimensions, high-dimensional vectors suffer from the "curse of dimensionality"—distances become less meaningful, and indexes perform worse. If your embeddings have 1000+ dimensions, consider dimensionality reduction (e.g., PCA) or use a model that outputs lower dimensions.

## Real-World Use Cases

- **Semantic Search**: Find documents, products, or articles by meaning.
- **Recommendation Systems**: Compare user preferences with item embeddings.
- **Anomaly Detection**: Identify data points far from the norm in embedding space.
- **Chatbots**: Retrieve relevant context for responses.

## Conclusion

Embeddings are a powerful way to represent data for semantic understanding, and pgvector makes it easy to integrate vector search into your PostgreSQL stack. We've covered the theory, the math, and practical implementation steps. Now you're ready to build your own semantic search features.

## Key Takeaways

- Embeddings are dense vector representations that capture semantic meaning, enabling similarity search by concept.
- Cosine similarity is the most common metric for text embeddings; pgvector provides operators for distance calculations.
- pgvector adds a `vector` data type and supports IVFFlat and HNSW indexes for scalable approximate search.
- Always choose an embedding model suited to your domain and test on your data.
- Normalize vectors and tune indexes for optimal performance.
- You can integrate pgvector into Java applications using Spring Data JPA and libraries like DJL for embedding generation.
- Start with a small dataset, experiment, and iterate—semantic search is a journey, not a one-time setup.