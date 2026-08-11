---
title: "Spring Boot + Elasticsearch: Full-Text Search Integration"
date: 2026-08-11
tags: [Spring Boot, Elasticsearch, Full-Text Search, Java, REST API]
categories: [Java, Spring Boot, Elasticsearch]
cover: "https://picsum.photos/seed/spring-boot-elasticsearch-full-text-search-integration/1200/630.webp"
description: Learn to integrate Elasticsearch with Spring Boot for powerful full-text search. Step-by-step guide with code examples, best practices, and optimization tips.
---

## Introduction

In today's data-driven world, users expect instant, relevant search results—whether they're searching for products, documents, or log entries. Traditional relational databases fall short when it comes to full-text search: they struggle with fuzzy matching, stemming, synonyms, and ranking by relevance. This is where **Elasticsearch** shines.

Elasticsearch is a distributed, RESTful search engine built on Apache Lucene. It provides near real-time search, powerful aggregations, and scalability out of the box. When combined with **Spring Boot**, you get a robust foundation for building modern applications with seamless search capabilities.

In this guide, I'll walk you through integrating Elasticsearch into a Spring Boot application, from setup to advanced query building. We'll cover:

- Setting up Elasticsearch locally or via Docker
- Adding the necessary dependencies
- Creating an index and mapping
- Performing CRUD operations
- Implementing full-text search queries
- Handling pagination, sorting, and highlighting
- Best practices for performance and maintainability

By the end, you'll have a solid understanding of how to leverage Elasticsearch in your Spring Boot projects.

## Prerequisites

Before diving in, ensure you have:

- Java 11 or later
- Maven or Gradle
- Docker (optional but recommended for running Elasticsearch)
- Basic knowledge of Spring Boot and REST APIs

## Setting Up Elasticsearch

### Option 1: Using Docker (Recommended)

Docker is the easiest way to get Elasticsearch running locally. Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data

volumes:
  esdata:
```

Then run:

```bash
docker-compose up -d
```

### Option 2: Local Installation

Download and extract Elasticsearch from [elastic.co/downloads/elasticsearch](https://www.elastic.co/downloads/elasticsearch). Then run:

```bash
./bin/elasticsearch
```

Once running, verify it's up by hitting `http://localhost:9200`. You should see a JSON response with the version info.

## Creating a Spring Boot Project

Head to [Spring Initializr](https://start.spring.io/) and generate a project with the following dependencies:

- Spring Web
- Spring Data Elasticsearch
- Lombok (optional)

Alternatively, add these to your `pom.xml`:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-elasticsearch</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

## Configuration

In `application.yml`, configure the Elasticsearch connection:

```yaml
spring:
  elasticsearch:
    uris: http://localhost:9200
    connection-timeout: 10s
    socket-timeout: 30s
```

For more advanced settings (like authentication), you can use `RestClientBuilder` or `ElasticsearchClient` beans. Spring Boot auto-configures a `RestClient` and `ElasticsearchOperations` bean for you.

## Defining an Entity

We'll create a simple `Product` entity that we want to index and search.

```java
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(indexName = "products")
public class Product {

    @Id
    private String id;

    @Field(type = FieldType.Text)
    private String name;

    @Field(type = FieldType.Text)
    private String description;

    @Field(type = FieldType.Keyword)
    private String category;

    @Field(type = FieldType.Double)
    private Double price;

    @Field(type = FieldType.Date)
    private LocalDate releaseDate;
}
```

Key annotations:
- `@Document` marks the class as an Elasticsearch document and specifies the index name.
- `@Field` defines the field mapping. `Text` is analyzed for full-text search, while `Keyword` is exact-match only.

## Repository Layer

Spring Data Elasticsearch provides a repository abstraction similar to Spring Data JPA. Create an interface:

```java
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ProductRepository extends ElasticsearchRepository<Product, String> {

    List<Product> findByName(String name);

    List<Product> findByCategory(String category);
}
```

This gives you basic CRUD operations out of the box. But for full-text search, we'll need custom queries.

## Building a Search Service

Let's create a service that uses `ElasticsearchOperations` (or `ElasticsearchClient`) to build dynamic queries.

```java
import org.springframework.data.elasticsearch.client.elc.ElasticsearchTemplate;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.data.elasticsearch.core.query.Criteria;
import org.springframework.data.elasticsearch.core.query.CriteriaQuery;
import org.springframework.data.elasticsearch.core.query.Query;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class SearchService {

    private final ElasticsearchTemplate elasticsearchTemplate;

    public SearchService(ElasticsearchTemplate elasticsearchTemplate) {
        this.elasticsearchTemplate = elasticsearchTemplate;
    }

    public List<Product> searchByName(String name) {
        Criteria criteria = new Criteria("name").is(name);
        Query query = new CriteriaQuery(criteria);
        SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
        return hits.stream().map(hit -> hit.getContent()).collect(Collectors.toList());
    }
}
```

But this is still basic. For true full-text search, we need to use **match queries** and other full-text query types.

## Implementing Full-Text Search

Full-text search in Elasticsearch uses analyzers to tokenize and normalize text. The `match` query is the standard for full-text search.

### Using `MatchQuery`

```java
import org.springframework.data.elasticsearch.core.query.Criteria;
import org.springframework.data.elasticsearch.core.query.CriteriaQuery;
import org.springframework.data.elasticsearch.core.query.Query;
import org.springframework.data.elasticsearch.core.query.MatchQueryBuilder;

public List<Product> fullTextSearch(String text) {
    Query query = new MatchQueryBuilder("name", text)
            .withOperator(Operator.And)
            .build();
    SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
    return hits.stream().map(hit -> hit.getContent()).collect(Collectors.toList());
}
```

### Multi-Field Search

Often, you want to search across multiple fields with different weights. Use `MultiMatchQueryBuilder`:

```java
import org.springframework.data.elasticsearch.core.query.MultiMatchQueryBuilder;

public List<Product> multiFieldSearch(String text) {
    MultiMatchQueryBuilder builder = new MultiMatchQueryBuilder(text)
            .field("name", 2.0f)   // boost name field
            .field("description")
            .type(MultiMatchQueryBuilder.Type.BEST_FIELDS);
    Query query = new NativeQuery(builder);
    SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
    return hits.stream().map(hit -> hit.getContent()).collect(Collectors.toList());
}
```

### Using `NativeQuery` for Advanced Queries

For complex queries, you can use `NativeQuery` with the Elasticsearch query DSL:

```java
import co.elastic.clients.elasticsearch._types.query_dsl.Query as EsQuery;

public List<Product> advancedSearch(String text, String category, Double minPrice) {
    NativeQuery query = NativeQuery.builder()
        .withQuery(q -> q
            .bool(b -> b
                .must(m -> m
                    .match(t -> t
                        .field("name")
                        .query(text)
                    )
                )
                .filter(f -> f
                    .term(t -> t
                        .field("category")
                        .value(category)
                    )
                )
                .filter(f -> f
                    .range(r -> r
                        .double_(d -> d
                            .field("price")
                            .gte(minPrice)
                        )
                    )
                )
            )
        )
        .build();
    SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
    return hits.stream().map(hit -> hit.getContent()).collect(Collectors.toList());
}
```

## Pagination and Sorting

For real-world applications, you need to paginate results. Spring Data Elasticsearch integrates with Spring Data's `Pageable`:

```java
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;

public Page<Product> searchWithPagination(String text, int page, int size) {
    Pageable pageable = PageRequest.of(page, size);
    NativeQuery query = NativeQuery.builder()
        .withQuery(q -> q
            .match(t -> t
                .field("name")
                .query(text)
            )
        )
        .withPageable(pageable)
        .build();
    SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
    return new PageImpl<>(hits.stream().map(hit -> hit.getContent()).collect(Collectors.toList()), pageable, hits.getTotalHits());
}
```

For sorting, add a `Sort` to the query:

```java
import org.springframework.data.domain.Sort;

Sort sort = Sort.by(Sort.Direction.DESC, "price");
query.withSort(sort);
```

## Highlighting Search Terms

Highlighting shows the matched terms in the results, which improves user experience. Here's how to add highlighting:

```java
public List<Map<String, Object>> searchWithHighlights(String text) {
    NativeQuery query = NativeQuery.builder()
        .withQuery(q -> q
            .match(t -> t
                .field("name")
                .query(text)
            )
        )
        .withHighlight(h -> h
            .fields("name", f -> f)
            .fields("description", f -> f)
        )
        .build();
    SearchHits<Product> hits = elasticsearchTemplate.search(query, Product.class);
    return hits.stream().map(hit -> {
        Map<String, Object> map = new HashMap<>();
        map.put("product", hit.getContent());
        map.put("highlights", hit.getHighlightFields());
        return map;
    }).collect(Collectors.toList());
}
```

## Advanced Query Types

### Fuzzy Search

To handle typos, use fuzzy matching:

```java
query.withQuery(q -> q
    .fuzzy(f -> f
        .field("name")
        .value(text)
        .fuzziness("AUTO")
    )
);
```

### Phrase Search

To match exact phrases:

```java
query.withQuery(q -> q
    .matchPhrase(mp -> mp
        .field("description")
        .query(text)
    )
);
```

### Boolean Queries

Combine multiple conditions with boolean logic:

```java
query.withQuery(q -> q
    .bool(b -> b
        .must(m -> m
            .match(t -> t.field("name").query(text))
        )
        .should(s -> s
            .match(t -> t.field("description").query(text))
        )
        .mustNot(mn -> mn
            .term(t -> t.field("category").value("obsolete"))
        )
    )
);
```

## Best Practices

1. **Design your index mapping carefully** – Decide which fields are `text` (analyzed) and which are `keyword` (exact). Over-analyzing keywords can lead to performance issues.
2. **Use custom analyzers** for language-specific stemming and stop words.
3. **Leverage Spring Data's repository** for simple queries, but use `ElasticsearchOperations` for complex ones.
4. **Handle connection retries** – Elasticsearch might temporarily be unavailable. Configure `RestClient` with retry logic.
5. **Monitor performance** – Use Elasticsearch's `_search` profiling and slow logs.
6. **Avoid N+1 queries** – When fetching related documents, use bulk operations or `mget`.
7. **Keep entities lightweight** – Don't map all fields if you don't need them in search.

## Testing the Integration

Write a simple REST controller to test:

```java
@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductRepository repository;
    private final SearchService searchService;

    public ProductController(ProductRepository repository, SearchService searchService) {
        this.repository = repository;
        this.searchService = searchService;
    }

    @PostMapping
    public Product create(@RequestBody Product product) {
        return repository.save(product);
    }

    @GetMapping("/search")
    public List<Product> search(@RequestParam String q) {
        return searchService.fullTextSearch(q);
    }

    @GetMapping("/search/fuzzy")
    public List<Product> fuzzySearch(@RequestParam String q) {
        return searchService.fuzzySearch(q);
    }
}
```

You can test with curl:

```bash
curl -X POST http://localhost:8080/api/products -H "Content-Type: application/json" -d '{"name":"Wireless Mouse","description":"Ergonomic wireless mouse with USB receiver","category":"Electronics","price":29.99}'

curl "http://localhost:8080/api/products/search?q=wireless"
```

## Conclusion

Integrating Elasticsearch with Spring Boot opens up a world of possibilities for building high-performance search features. We've covered the essentials: setting up Elasticsearch, creating entities, building repositories, and implementing various search queries. Remember to design your index mapping thoughtfully and leverage the full power of Elasticsearch's query DSL for complex requirements.

With the foundation you've gained here, you can now explore more advanced topics like aggregations, geospatial search, and suggesters. Happy searching!

## Key Takeaways

- **Spring Boot + Elasticsearch** provides a seamless way to add full-text search to your applications.
- Use **`@Document`** and **`@Field`** annotations to define your index mapping.
- **`ElasticsearchRepository`** offers basic CRUD, while **`ElasticsearchOperations`** gives you fine-grained control over queries.
- **Match queries** are the go-to for full-text search; use **multi-match** for searching across fields.
- Leverage **`NativeQuery`** for complex boolean and advanced queries.
- **Pagination** and **sorting** are easily integrated with Spring Data's `Pageable` and `Sort`.
- **Highlighting** improves user experience by showing matched terms.
- Always design your index mapping with performance and relevance in mind.