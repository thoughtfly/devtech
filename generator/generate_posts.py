#!/usr/bin/env python3
"""
AI-Powered Blog Post Generator for DevTech Insights
Generates high-quality English tech blog posts using DeepSeek API.
Designed to run as a GitHub Actions scheduled job.

Usage:
    python generate_posts.py                    # Generate 1 post (default)
    python generate_posts.py --count 3          # Generate 3 posts
    python generate_posts --dry-run             # Print without saving
"""

import os
import re
import sys
import json
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import requests

# ============================================================
# Configuration
# ============================================================

# API config - read from environment variables (GitHub Secrets)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Blog config
BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "source" / "_posts"

# Post history tracker - avoids duplicate topics
HISTORY_FILE = BLOG_ROOT / "generator" / ".topic_history.json"

# ============================================================
# SEO-Optimized Topic Bank
# ============================================================

TOPICS = [
    # === Java & Spring Boot ===
    "How to Build a REST API with Spring Boot 3 and Java 21",
    "Spring Boot 3 Virtual Threads: A Practical Performance Guide",
    "Record Patterns in Java 21: Write Cleaner Data-Centric Code",
    "Building Reactive Microservices with Spring WebFlux",
    "Spring Boot 3 Observability with Micrometer and OpenTelemetry",
    "Spring Security 6: JWT Authentication from Scratch",
    "Spring Boot Testing: Unit Tests, Integration Tests, and Testcontainers",
    "Java 21 Pattern Matching for Switch: Real-World Examples",
    "Building a CRUD Application with Spring Boot and JPA",
    "Spring Boot Graceful Shutdown: Why and How",
    "Java Functional Programming: Streams, Optional, and Collectors",
    "Spring Boot Actuator: Production-Ready Monitoring",
    "Handling Transactions in Spring: @Transactional Deep Dive",
    "Java Multithreading Best Practices in 2026",
    "Building REST Clients with Spring 6 RestClient",

    # === AI & LLM Integration ===
    "Building an AI-Powered Chatbot with Spring Boot and LangChain4j",
    "Practical Guide to RAG: Enhancing LLM Responses with Your Own Data",
    "How to Build a Multi-Model AI Gateway with Spring Cloud Gateway",
    "Semantic Search with Vector Databases: A Developer's Guide",
    "Fine-Tuning vs RAG: Choosing the Right Approach for Your AI App",
    "Building AI Agents with Spring AI Framework",
    "Deploying LLMs in Production: A Backend Engineer's Guide",
    "Integrating OpenAI API with Spring Boot: Complete Tutorial",
    "Prompt Engineering for Developers: Patterns and Anti-Patterns",
    "Building a Code Review Assistant with LLMs and Java",
    "Vector Database Comparison: Pinecone vs Weaviate vs Qdrant",
    "Cost Optimization Strategies for LLM API Usage",
    "Building Intelligent Document Processing Pipelines with AI",

    # === System Design & Architecture ===
    "Microservices vs Modular Monolith: Making the Right Choice in 2026",
    "Event-Driven Architecture with Kafka and Spring Boot",
    "Designing Resilient Systems: Circuit Breaker and Retry Patterns",
    "API Gateway Patterns: Rate Limiting, Caching, and Authentication",
    "Database Sharding 101: When and How to Scale Horizontally",
    "CQRS and Event Sourcing: A Practical Introduction",
    "Designing RESTful APIs: Best Practices and Common Pitfalls",
    "CAP Theorem Explained: Consistency, Availability, Partition Tolerance",
    "Building Scalable Notification Systems: Architecture Deep Dive",
    "Backend System Design Interview: Design a URL Shortener",
    "Designing Idempotent APIs for Reliable Distributed Systems",
    "Distributed Caching with Redis: Patterns and Anti-Patterns",

    # === DevOps & Cloud ===
    "GitHub Actions CI/CD Pipeline for Spring Boot Microservices",
    "Containerizing Spring Boot Applications: From Docker to Kubernetes",
    "Monitoring Java Applications with Prometheus and Grafana",
    "Terraform vs Pulumi: Infrastructure as Code for Java Teams",
    "Zero-Downtime Deployments for Spring Boot Applications",
    "Kubernetes for Java Developers: A Practical Guide",
    "Docker Compose for Local Spring Boot Development",
    "Helm Charts for Spring Boot: Package and Deploy to Kubernetes",
    "Git Workflows for Teams: GitFlow vs Trunk-Based Development",
    "Cloud Cost Optimization for Java Microservices",
    "Building a Multi-Environment CI/CD Pipeline with GitHub Actions",
    "Service Mesh with Istio: When Do You Need It?",

    # === Performance & Optimization ===
    "JVM Performance Tuning: Garbage Collection Strategies in 2026",
    "Optimizing Database Queries in Spring Boot with Hibernate 6",
    "Caching Strategies for High-Performance Java Applications",
    "Profiling Spring Boot Applications with Async Profiler",
    "Reducing Docker Image Size for Spring Boot: From 500MB to 100MB",
    "Connection Pool Tuning: HikariCP Best Practices",
    "Optimizing JPA Performance: N+1 Queries, Fetch Strategies, and Batching",
    "Java Memory Leaks: Detection and Prevention",
    "Spring Boot Performance Benchmark: WebFlux vs MVC vs Virtual Threads",
    "Indexing Strategies for MySQL and PostgreSQL",
    "Load Testing Spring Boot Applications with k6 and Gatling",

    # === Databases & Data ===
    "MySQL vs PostgreSQL for Java Applications in 2026",
    "Spring Data JPA vs MyBatis: Which One Should You Choose?",
    "Database Migration with Flyway: Version Control for Your Schema",
    "Redis for Caching in Spring Boot: A Complete Guide",
    "Working with MongoDB in Spring Boot: A Developer's Guide",
    "Elasticsearch for Full-Text Search in Java Applications",
    "Database Replication: Master-Slave vs Multi-Master",
    "Introduction to Apache Kafka for Java Developers",

    # === Career & Best Practices ===
    "Clean Code in Java: Principles Every Developer Should Know",
    "Effective Code Review: A Guide for Backend Engineers",
    "Logging Best Practices for Spring Boot Applications",
    "Exception Handling Patterns in Java: Checked vs Unchecked",
    "API Versioning Strategies for RESTful Services",
    "Secrets Management for Java Applications: Vault, AWS Secrets Manager",
    "Building Developer Documentation with AsciiDoc and Spring REST Docs",
    "Contract Testing with Spring Cloud Contract: A Practical Guide",
    "Why Your Spring Boot Application Is Slow: A Debugging Checklist",
]

# ============================================================
# Helper Functions
# ============================================================

def slugify(title):
    """Convert a title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug


def load_topic_history():
    """Load previously used topics to avoid duplicates."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"used_topics": [], "post_dates": []}


def save_topic_history(history):
    """Save updated topic history."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def get_next_topic(history):
    """Pick a topic that hasn't been used recently."""
    used_set = set(history["used_topics"])
    available = [t for t in TOPICS if t not in used_set]

    if not available:
        # All topics used - reset
        history["used_topics"] = []
        available = TOPICS[:]

    topic = available[0]
    history["used_topics"].append(topic)
    return topic, history


def call_deepseek(topic, api_key, max_retries=3):
    """Generate a blog post using DeepSeek API with retry logic."""
    system_prompt = """You are an expert technical writer for a software engineering blog. 
Write high-quality, SEO-optimized blog posts in English.

Requirements:
- Write a complete, in-depth blog post (1500-2500 words)
- Use markdown formatting with proper headings (##, ###)
- Include code examples where relevant (use ```java, ```bash, ```yaml blocks)
- Start with a compelling introduction that hooks the reader
- Include a "Key Takeaways" section at the end
- Use natural language that ranks well for technical SEO
- Write as a seasoned engineer sharing practical experience
- DO NOT include disclaimer or "AI-generated" notes
- DO NOT include a conclusion section - end with Key Takeaways
- Frontmatter must include: title, date, tags, categories

Return ONLY valid JSON with this structure:
{
  "title": "Post title",
  "tags": ["tag1", "tag2", "tag3"],
  "categories": ["Java"],
  "content": "Full markdown content including frontmatter"
}"""

    user_prompt = f"Write a detailed technical blog post about: {topic}"

    session = requests.Session()

    for attempt in range(1, max_retries + 1):
        try:
            resp = session.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=300
            )

            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"[WARN] Rate limited (attempt {attempt}/{max_retries}), waiting {wait}s...")
                import time
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"]

            # Extract JSON from response (handle markdown code block wrapping)
            result = extract_json(raw)
            if result:
                return result

            print(f"[WARN] Failed to parse JSON on attempt {attempt}/{max_retries}")

        except requests.exceptions.Timeout:
            print(f"[WARN] Timeout on attempt {attempt}/{max_retries}")
        except requests.exceptions.RequestException as e:
            print(f"[WARN] API request failed on attempt {attempt}/{max_retries}: {e}")

        if attempt < max_retries:
            wait = 2 ** attempt
            print(f"  Retrying in {wait}s...")
            import time
            time.sleep(wait)

    print(f"[ERROR] All {max_retries} attempts failed for topic: {topic}")
    return None


def extract_json(text):
    """Robustly extract JSON from API response text."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Handle markdown code block wrapping
    # Remove ```json ... ``` or ``` ... ```
    lines = text.split('\n')
    if lines[0].strip().startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith('```'):
        lines = lines[:-1]
    cleaned = '\n'.join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: try to repair common issues (unescaped newlines in strings)
    import re
    try:
        # Escape unescaped newlines within string values
        repaired = re.sub(r'(?<=[^\\])"(?:[^"\\]|\\.)*"', 
                         lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r'), 
                         cleaned)
        return json.loads(repaired)
    except (json.JSONDecodeError, re.error):
        pass

    return None


def save_post(post_data, topic, dry_run=False):
    """Save the generated post as a markdown file."""
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")
    slug = slugify(topic)
    filename = f"{date_str}-{slug}.md"
    filepath = POSTS_DIR / filename

    # Build frontmatter
    tags_str = ", ".join(post_data.get("tags", ["tech"]))
    cats_str = ", ".join(post_data.get("categories", ["Uncategorized"]))

    frontmatter = f"""---
title: "{post_data['title']}"
date: {date_str}
tags: [{tags_str}]
categories: [{cats_str}]
cover:
description: {post_data['title']}
---
"""

    full_content = frontmatter + "\n" + post_data["content"]

    if dry_run:
        print(f"[DRY-RUN] Would write: {filepath.name}")
        print(f"[DRY-RUN] Title: {post_data['title']}")
        print(f"[DRY-RUN] Size: {len(full_content)} chars")
        return filename

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)

    print(f"[OK] Saved: {filepath.name} ({len(full_content)} chars)")
    return filename


def generate_sitemap_index():
    """Generate a sitemap index for Google Search Console."""
    # We'll use the hexo-generator-sitemap plugin instead
    pass


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Generate AI blog posts")
    parser.add_argument("--count", type=int, default=1, help="Number of posts to generate")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--topic", type=str, help="Specific topic to write about")
    args = parser.parse_args()

    if not DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY environment variable not set!")
        print("Set it locally or add it to GitHub Secrets as DEEPSEEK_API_KEY")
        sys.exit(1)

    print(f"=== DevTech Blog Post Generator ===")
    print(f"Posts to generate: {args.count}")
    print(f"Posts directory: {POSTS_DIR}")
    print()

    history = load_topic_history()
    generated = []

    for i in range(args.count):
        print(f"\n--- Post {i+1}/{args.count} ---")

        if args.topic:
            topic = args.topic
        else:
            topic, history = get_next_topic(history)

        print(f"Topic: {topic}")
        print("Calling DeepSeek API...")

        post_data = call_deepseek(topic, DEEPSEEK_API_KEY)
        if not post_data:
            print(f"[FAILED] Could not generate post for: {topic}")
            continue

        filename = save_post(post_data, topic, dry_run=args.dry_run)
        generated.append(filename)

    if not args.dry_run:
        save_topic_history(history)

    print(f"\n=== Done ===")
    print(f"Generated: {len(generated)} posts")
    for f in generated:
        print(f"  - {f}")
    print(f"\nNext step: Commit and push to trigger GitHub Pages deployment.")


if __name__ == "__main__":
    main()
