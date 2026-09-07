---
title: "Prompt Versioning and A/B Testing for LLM Features: A Production-Ready Guide"
date: 2026-09-07
tags: [LLM, Prompt Engineering, A/B Testing, MLOps, Java, Software Engineering]
categories: [Java, AI/ML]
cover: "https://images.unsplash.com/photo-1777894162454-35cff9998a25?w=1200&q=80&fit=crop&fm=webp"
description: Master prompt versioning and A/B testing for LLMs. Learn practical strategies to track prompt evolution, measure performance, and ship confident AI features.
---

## Introduction: The Hidden Complexity of Prompt Engineering

When you first start building with Large Language Models (LLMs), it’s easy to fall into the trap of thinking that prompt engineering is just about writing good text. You craft a prompt, test it in the playground, and if it works, you ship it. It feels like frontend development: write some code, see the result, iterate.

But as your application grows from a prototype to a production service, this mindset becomes a liability. In production, prompts are not static strings; they are dynamic, versioned code that directly impacts your business metrics. A slight tweak to a system message can change your conversion rate by 15%. A regression in a few-shot example can silently degrade your model’s accuracy. Without rigorous management, you are flying blind.

This post explores the two critical pillars of production-grade LLM engineering: **Prompt Versioning** and **A/B Testing**. We will move beyond theory and look at concrete implementation strategies, including how to integrate these practices into a Java-based backend using modern tools like LangChain4j and OpenTelemetry. By the end, you will have a blueprint for treating prompts with the same seriousness as your application code.

## Why Prompts Need Versioning

In traditional software development, we version our code using Git. Every change is tracked, attributed, and reversible. Prompts, however, often live in string literals or configuration files that are rarely tracked with the same rigor. This leads to several problems:

1.  **Reproducibility**: If a prompt performs well today, can you reproduce that result next month? Without versioning, you might not know which exact version of the prompt generated a specific output.
2.  **Debugging**: When a user complains about a bad response, you need to know which prompt version they encountered. Was it the latest version? An old one? Did a recent deployment change the system prompt?
3.  **Rollbacks**: If a new prompt version causes a spike in hallucinations or a drop in user satisfaction, you need to roll back immediately. Without versioning, this is a manual, error-prone process.

### The Versioning Model

A robust prompt versioning system should include:

-   **Unique Identifier**: Each prompt version should have a unique ID (e.g., `prompt-v1.2.3`).
-   **Content Hash**: A hash of the prompt content to detect changes.
-   **Metadata**: Author, date, description, and associated experiment.
-   **Status**: Draft, Active, Deprecated.

## Implementing Prompt Versioning in Java

Let’s look at how to implement prompt versioning in a Java application. We’ll use **LangChain4j**, a popular Java framework for building LLM applications, and a simple database-backed storage system.

### Step 1: Define the Prompt Version Entity

First, we need a data model to represent a prompt version. This entity will store the prompt content, metadata, and version information.

```java
import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "prompt_versions")
public class PromptVersion {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    private String name; // e.g., "customer-support-system-prompt"
    private Integer majorVersion;
    private Integer minorVersion;
    private String content; // The actual prompt text
    private String description; // Why this version was created
    private String author; // Who created it
    private Instant createdAt;
    private Instant updatedAt;
    private String status; // DRAFT, ACTIVE, DEPRECATED

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Integer getMajorVersion() { return majorVersion; }
    public void setMajorVersion(Integer majorVersion) { this.majorVersion = majorVersion; }

    public Integer getMinorVersion() { return minorVersion; }
    public void setMinorVersion(Integer minorVersion) { this.minorVersion = minorVersion; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
```

### Step 2: Create a Prompt Version Service

Next, we need a service to manage prompt versions. This service will handle creating, updating, and retrieving prompt versions. It will also ensure that only one prompt version is active at a time for a given prompt name.

```java
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import jakarta.transaction.Transactional;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class PromptVersionService {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional
    public PromptVersion createPromptVersion(PromptVersion promptVersion) {
        promptVersion.setCreatedAt(Instant.now());
        promptVersion.setUpdatedAt(Instant.now());
        if (promptVersion.getStatus() == null) {
            promptVersion.setStatus("DRAFT");
        }
        entityManager.persist(promptVersion);
        return promptVersion;
    }

    @Transactional
    public PromptVersion updatePromptVersion(PromptVersion promptVersion) {
        PromptVersion existing = entityManager.find(PromptVersion.class, promptVersion.getId());
        if (existing == null) {
            throw new IllegalArgumentException("Prompt version not found: " + promptVersion.getId());
        }
        existing.setContent(promptVersion.getContent());
        existing.setDescription(promptVersion.getDescription());
        existing.setUpdatedAt(Instant.now());
        existing.setStatus(promptVersion.getStatus());
        return existing;
    }

    public Optional<PromptVersion> getActivePromptVersion(String name) {
        TypedQuery<PromptVersion> query = entityManager.createQuery(
            "SELECT p FROM PromptVersion p WHERE p.name = :name AND p.status = 'ACTIVE' ORDER BY p.majorVersion DESC, p.minorVersion DESC", 
            PromptVersion.class
        );
        query.setParameter("name", name);
        List<PromptVersion> results = query.getResultList();
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    public List<PromptVersion> getPromptVersions(String name) {
        TypedQuery<PromptVersion> query = entityManager.createQuery(
            "SELECT p FROM PromptVersion p WHERE p.name = :name ORDER BY p.majorVersion DESC, p.minorVersion DESC", 
            PromptVersion.class
        );
        query.setParameter("name", name);
        return query.getResultList();
    }

    @Transactional
    public void activatePromptVersion(String id) {
        // Deactivate all other versions of the same prompt
        TypedQuery<PromptVersion> query = entityManager.createQuery(
            "SELECT p FROM PromptVersion p WHERE p.name = (SELECT p2.name FROM PromptVersion p2 WHERE p2.id = :id) AND p.status = 'ACTIVE'", 
            PromptVersion.class
        );
        query.setParameter("id", id);
        List<PromptVersion> activeVersions = query.getResultList();
        for (PromptVersion v : activeVersions) {
            v.setStatus("DEPRECATED");
            v.setUpdatedAt(Instant.now());
        }

        // Activate the new version
        PromptVersion newVersion = entityManager.find(PromptVersion.class, id);
        if (newVersion != null) {
            newVersion.setStatus("ACTIVE");
            newVersion.setUpdatedAt(Instant.now());
        }
    }
}
```

### Step 3: Integrate with LangChain4j

Now, let’s integrate this with LangChain4j. We’ll create a custom `ChatLanguageModel` that fetches the active prompt version before sending the request to the LLM.

```java
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.input.Prompt;
import dev.langchain4j.model.input.PromptTemplate;
import dev.langchain4j.model.output.Response;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.List;
import java.util.Map;

@ApplicationScoped
public class VersionedPromptChatModel implements ChatLanguageModel {

    @Inject
    private PromptVersionService promptVersionService;

    @Inject
    private ChatLanguageModel delegate; // e.g., OpenAiChatModel

    @Override
    public Response<String> generate(List<dev.langchain4j.data.message.Message> messages) {
        // Assume the first message is a SystemMessage with the prompt name
        if (messages.isEmpty() || !(messages.get(0) instanceof SystemMessage)) {
            return delegate.generate(messages);
        }

        SystemMessage systemMessage = (SystemMessage) messages.get(0);
        String promptName = systemMessage.text(); // The prompt name is stored in the text

        // Fetch the active prompt version
        var activePrompt = promptVersionService.getActivePromptVersion(promptName);
        if (activePrompt.isEmpty()) {
            throw new IllegalStateException("No active prompt version found for: " + promptName);
        }

        // Replace the system message with the prompt content
        String promptContent = activePrompt.get().getContent();
        List<dev.langchain4j.data.message.Message> updatedMessages = List.of(
            new SystemMessage(promptContent),
            messages.subList(1, messages.size()).toArray(new dev.langchain4j.data.message.Message[0])
        );

        return delegate.generate(updatedMessages);
    }
}
```

This approach allows you to manage prompt versions centrally and swap them out without changing your application code. It also provides a clear audit trail of which prompt was used for each request.

## A/B Testing LLM Features

Versioning is only half the battle. Once you have multiple prompt versions, you need a way to determine which one performs best. This is where A/B testing comes in.

### What is A/B Testing for LLMs?

A/B testing for LLMs involves serving different prompt versions to different users or segments and measuring their impact on key metrics. Unlike traditional A/B testing, where the metric is often a click or a conversion, LLM A/B testing can involve more complex metrics such as:

-   **Token Usage**: Cost efficiency.
-   **Latency**: Response time.
-   **Quality Scores**: Human or automated ratings of response quality.
-   **User Satisfaction**: Upvotes, downvotes, or explicit feedback.
-   **Hallucination Rate**: The frequency of incorrect or fabricated information.

### Designing an A/B Test

Let’s say you want to test two versions of a customer support prompt: `v1` and `v2`. You want to see which one leads to higher user satisfaction.

1.  **Define the Hypothesis**: `v2` will lead to higher user satisfaction because it includes more detailed examples.
2.  **Select the Metric**: User satisfaction score (1-5 stars).
3.  **Randomize Users**: Assign each user to either `v1` or `v2` randomly.
4.  **Serve the Prompt**: Use the assigned prompt version for all interactions.
5.  **Collect Data**: Log the prompt version, user ID, and satisfaction score.
6.  **Analyze Results**: Compare the average satisfaction scores between the two groups.

### Implementing A/B Testing in Java

We can extend our `PromptVersionService` to support A/B testing. We’ll add a `Experiment` entity to track the test and a `ExperimentAssignment` table to record which users were assigned to which version.

```java
import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "experiments")
public class Experiment {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    private String name; // e.g., "customer-support-prompt-ab-test"
    private String description;
    private Instant startDate;
    private Instant endDate;
    private String status; // RUNNING, COMPLETED, CANCELLED

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public Instant getStartDate() { return startDate; }
    public void setStartDate(Instant startDate) { this.startDate = startDate; }

    public Instant getEndDate() { return endDate; }
    public void setEndDate(Instant endDate) { this.endDate = endDate; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
```

```java
import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "experiment_assignments")
public class ExperimentAssignment {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String id;

    @ManyToOne
    @JoinColumn(name = "experiment_id")
    private Experiment experiment;

    private String userId; // Could be anonymous if not logged in
    private String promptVersionId;
    private Instant assignedAt;

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public Experiment getExperiment() { return experiment; }
    public void setExperiment(Experiment experiment) { this.experiment = experiment; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getPromptVersionId() { return promptVersionId; }
    public void setPromptVersionId(String promptVersionId) { this.promptVersionId = promptVersionId; }

    public Instant getAssignedAt() { return assignedAt; }
    public void setAssignedAt(Instant assignedAt) { this.assignedAt = assignedAt; }
}
```

### The A/B Testing Service

Now, let’s create a service to manage A/B tests.

```java
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.TypedQuery;
import jakarta.transaction.Transactional;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class ExperimentService {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional
    public Experiment createExperiment(Experiment experiment) {
        experiment.setStartDate(Instant.now());
        experiment.setStatus("RUNNING");
        entityManager.persist(experiment);
        return experiment;
    }

    @Transactional
    public ExperimentAssignment assignUserToExperiment(String experimentId, String userId, String promptVersionId) {
        ExperimentAssignment assignment = new ExperimentAssignment();
        assignment.setExperiment(entityManager.find(Experiment.class, experimentId));
        assignment.setUserId(userId);
        assignment.setPromptVersionId(promptVersionId);
        assignment.setAssignedAt(Instant.now());
        entityManager.persist(assignment);
        return assignment;
    }

    public Optional<ExperimentAssignment> getUserExperimentAssignment(String experimentId, String userId) {
        TypedQuery<ExperimentAssignment> query = entityManager.createQuery(
            "SELECT a FROM ExperimentAssignment a WHERE a.experiment.id = :experimentId AND a.userId = :userId", 
            ExperimentAssignment.class
        );
        query.setParameter("experimentId", experimentId);
        query.setParameter("userId", userId);
        List<ExperimentAssignment> results = query.getResultList();
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    @Transactional
    public void completeExperiment(String experimentId) {
        Experiment experiment = entityManager.find(Experiment.class, experimentId);
        if (experiment != null) {
            experiment.setStatus("COMPLETED");
            experiment.setEndDate(Instant.now());
        }
    }
}
```

### Integrating A/B Testing with Prompt Versioning

Finally, we need to integrate the A/B testing logic with our prompt versioning. We’ll modify the `VersionedPromptChatModel` to check if the user is part of an A/B test and serve the appropriate prompt version.

```java
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class VersionedPromptChatModel implements ChatLanguageModel {

    @Inject
    private PromptVersionService promptVersionService;

    @Inject
    private ExperimentService experimentService;

    @Inject
    private ChatLanguageModel delegate; // e.g., OpenAiChatModel

    @Override
    public Response<String> generate(List<dev.langchain4j.data.message.Message> messages) {
        if (messages.isEmpty() || !(messages.get(0) instanceof SystemMessage)) {
            return delegate.generate(messages);
        }

        SystemMessage systemMessage = (SystemMessage) messages.get(0);
        String promptName = systemMessage.text();

        // Check if this prompt is part of an A/B test
        // For simplicity, assume we have a way to map prompt names to experiment IDs
        String experimentId = getExperimentIdForPrompt(promptName);
        
        String userId = getCurrentUserId(); // Implement this based on your auth system
        String promptVersionId = null;

        if (experimentId != null && userId != null) {
            Optional<ExperimentAssignment> assignment = experimentService.getUserExperimentAssignment(experimentId, userId);
            if (assignment.isPresent()) {
                promptVersionId = assignment.get().getPromptVersionId();
            } else {
                // Assign user to a random version
                List<String> versions = getVersionsForExperiment(experimentId);
                if (!versions.isEmpty()) {
                    promptVersionId = versions.get((int) (Math.random() * versions.size()));
                    experimentService.assignUserToExperiment(experimentId, userId, promptVersionId);
                }
            }
        }

        // Fetch the prompt version
        PromptVersion promptVersion;
        if (promptVersionId != null) {
            promptVersion = promptVersionService.getPromptVersionById(promptVersionId);
        } else {
            // Fallback to active version
            var activePrompt = promptVersionService.getActivePromptVersion(promptName);
            if (activePrompt.isEmpty()) {
                throw new IllegalStateException("No active prompt version found for: " + promptName);
            }
            promptVersion = activePrompt.get();
        }

        // Replace the system message with the prompt content
        String promptContent = promptVersion.getContent();
        List<dev.langchain4j.data.message.Message> updatedMessages = List.of(
            new SystemMessage(promptContent),
            messages.subList(1, messages.size()).toArray(new dev.langchain4j.data.message.Message[0])
        );

        return delegate.generate(updatedMessages);
    }

    // Helper methods
    private String getExperimentIdForPrompt(String promptName) {
        // Implement logic to map prompt names to experiment IDs
        return null; 
    }

    private List<String> getVersionsForExperiment(String experimentId) {
        // Implement logic to get versions for an experiment
        return List.of();
    }

    private String getCurrentUserId() {
        // Implement logic to get the current user ID
        return null;
    }
}
```

## Monitoring and Observability

A/B testing and prompt versioning generate a lot of data. It’s essential to have robust monitoring and observability to track the performance of different prompt versions and experiments.

### Key Metrics to Track

1.  **Token Usage**: Track the number of tokens consumed by each prompt version. This helps you understand the cost impact of different prompts.
2.  **Latency**: Measure the response time for each prompt version. Some prompts may be more complex and take longer to process.
3.  **Error Rate**: Track the rate of errors (e.g., timeouts, API failures) for each prompt version.
4.  **Quality Scores**: If you have a feedback mechanism, track the quality scores for each prompt version.
5.  **User Satisfaction**: Track user satisfaction scores for each prompt version.

### Using OpenTelemetry for Observability

OpenTelemetry is a powerful framework for collecting telemetry data (traces, metrics, logs) from your applications. You can use it to instrument your LLM requests and capture the key metrics mentioned above.

Here’s an example of how to use OpenTelemetry to trace an LLM request with LangChain4j:

```java
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.List;

@ApplicationScoped
public class TracedChatModel implements ChatLanguageModel {

    @Inject
    private OpenTelemetry openTelemetry;

    @Inject
    private ChatLanguageModel delegate;

    private static final Tracer tracer = OpenTelemetry.getGlobalTracerManagement().getTracer("chat-model");

    @Override
    public Response<String> generate(List<dev.langchain4j.data.message.Message> messages) {
        Span span = tracer.spanBuilder("llm.generate").startSpan();
        try (Scope scope = span.makeCurrent()) {
            // Add attributes to the span
            span.setAttribute("llm.model", "gpt-4");
            span.setAttribute("llm.prompt.length", messages.toString().length());

            Response<String> response = delegate.generate(messages);

            // Add response attributes
            span.setAttribute("llm.response.length", response != null && response.content() != null ? response.content().length() : 0);
            span.setStatus(StatusCode.OK);

            return response;
        } catch (Exception e) {
            span.recordException(e);
            span.setStatus(StatusCode.ERROR);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

This code creates a trace for each LLM request and records important attributes such as the model name, prompt length, and response length. You can then use a observability backend like Jaeger or Zipkin to visualize these traces and identify bottlenecks or issues.

## Best Practices for Prompt Versioning and A/B Testing

1.  **Treat Prompts as Code**: Use version control (Git) to track changes to your prompts. Include prompts in your CI/CD pipeline to ensure they are tested and reviewed before deployment.
2.  **Automate Testing**: Write automated tests for your prompts. Use tools like Promptfoo or LangSmith to evaluate prompt performance against a set of test cases.
3.  **Start with Small Experiments**: Begin with small A/B tests to validate your hypotheses before rolling out changes to all users.
4.  **Monitor Continuously**: Set up dashboards to monitor the performance of your prompts in real-time. Use alerts to notify you of any sudden changes in metrics.
5.  **Document Everything**: Keep detailed records of your prompt versions, experiments, and results. This will help you understand the history of your LLM features and make informed decisions in the future.

## Key Takeaways

-   **Prompt versioning is essential** for production LLM applications. It provides reproducibility, debugging capabilities, and the ability to roll back changes quickly.
-   **A/B testing allows you to make data-driven decisions** about which prompts perform best. It helps you optimize for key metrics such as user satisfaction, latency, and cost.
-   **Integrating versioning and A/B testing with Java** can be done using frameworks like LangChain4j and persistence APIs like JPA. Custom services can manage prompt versions and experiment assignments.
-   **Observability is critical** for monitoring the performance of your prompts. Use tools like OpenTelemetry to trace LLM requests and capture key metrics.
-   **Best practices include treating prompts as code, automating testing, starting with small experiments, monitoring continuously, and documenting everything.**

By adopting these practices, you can build more reliable, efficient, and user-friendly LLM features. Remember, prompt engineering is not just about writing good text; it’s about managing a complex system with rigor and discipline.