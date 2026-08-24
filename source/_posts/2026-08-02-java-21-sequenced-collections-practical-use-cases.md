---
title: "Java 21 Sequenced Collections: Practical Use Cases"
date: 2026-08-02
tags: [Java 21, Sequenced Collections, Java Collections, Programming]
categories: [Java]
cover: "https://images.unsplash.com/photo-1718780276037-e87403539eb6?w=1200&q=80&fit=crop&fm=webp"
description: Explore Java 21's Sequenced Collections with practical examples. Learn how to simplify code with first/last access, reverse iteration, and more.
---

## Introduction

Java 21 has finally arrived, and with it comes a host of new features that promise to make our lives as developers easier. Among these, Sequenced Collections stand out as a long-awaited addition to the Java Collections Framework. If you've ever struggled with the awkwardness of accessing the first or last element of a `List` or `LinkedHashSet`, or needed to iterate in reverse order without creating a new collection, then this feature is for you.

In this article, we'll dive deep into what Sequenced Collections are, how they work, and most importantly, we'll explore practical use cases that demonstrate how they can simplify your code and improve readability. Whether you're working on a legacy codebase or starting a new project, understanding Sequenced Collections will give you another tool in your Java toolbox.

## What Are Sequenced Collections?

Before we dive into use cases, let's clarify what Sequenced Collections actually are. In simple terms, a Sequenced Collection is a collection that has a defined encounter order. This means you can access elements by their position, get the first and last elements, and iterate in reverse order.

The Java Collections Framework has long had interfaces like `List` and `Deque` that support ordered access, but there was no unified way to handle this across all collection types. For example, `Set` implementations like `HashSet` don't guarantee order, but `LinkedHashSet` does. However, there was no common interface to represent this concept.

Java 21 introduces three new interfaces:

- `SequencedCollection` – for collections that have an encounter order
- `SequencedSet` – for sets that have an encounter order
- `SequencedMap` – for maps that have an encounter order

These interfaces extend the existing collection interfaces and add methods like `getFirst()`, `getLast()`, `addFirst()`, `addLast()`, and `reversed()`.

## The New Methods Explained

Let's take a closer look at the methods introduced by these interfaces.

### SequencedCollection

`SequencedCollection` extends `Collection` and adds the following methods:

- `getFirst()` – returns the first element
- `getLast()` – returns the last element
- `addFirst(E e)` – adds an element at the beginning
- `addLast(E e)` – adds an element at the end
- `reversed()` – returns a reverse-ordered view of the collection

### SequencedSet

`SequencedSet` extends `Set` and `SequencedCollection`, but it overrides `reversed()` to return a `SequencedSet`.

### SequencedMap

`SequencedMap` extends `Map` and adds:

- `firstEntry()` – returns the first key-value pair
- `lastEntry()` – returns the last key-value pair
- `pollFirstEntry()` – removes and returns the first entry
- `pollLastEntry()` – removes and returns the last entry
- `putFirst(K k, V v)` – inserts a key-value pair at the beginning
- `putLast(K k, V v)` – inserts a key-value pair at the end
- `reversed()` – returns a reverse-ordered view of the map

Now, let's see these in action with practical scenarios.

## Practical Use Case 1: Accessing First and Last Elements

One of the most common needs in programming is to access the first and last elements of a collection. Before Java 21, this was often done with awkward code.

Consider a simple task: given a list of strings, print the first and last elements.

### Before Java 21

```java
List<String> fruits = new ArrayList<>(List.of("apple", "banana", "cherry"));

// First element
String first = fruits.get(0);

// Last element
String last = fruits.get(fruits.size() - 1);

System.out.println("First: " + first);
System.out.println("Last: " + last);
```

This works, but it's error-prone. What if the list is empty? You'd get an `IndexOutOfBoundsException`. Also, for `LinkedList`, accessing the last element with `get(size - 1)` is O(n) because it has to traverse the list.

### With Java 21

```java
List<String> fruits = new ArrayList<>(List.of("apple", "banana", "cherry"));

System.out.println("First: " + fruits.getFirst());
System.out.println("Last: " + fruits.getLast());
```

Much cleaner! And if the collection is empty, `getFirst()` and `getLast()` throw a `NoSuchElementException`, which is more meaningful than an index-based error.

## Practical Use Case 2: Reverse Iteration

Another common scenario is iterating over a collection in reverse order. Before, you had to either use a `ListIterator` or create a reversed copy.

### Before Java 21

```java
List<String> fruits = new ArrayList<>(List.of("apple", "banana", "cherry"));

// Using ListIterator
ListIterator<String> it = fruits.listIterator(fruits.size());
while (it.hasPrevious()) {
    System.out.println(it.previous());
}

// Or using Collections.reverse
Collections.reverse(fruits);
for (String fruit : fruits) {
    System.out.println(fruit);
}
// But this modifies the original list!
```

### With Java 21

```java
List<String> fruits = new ArrayList<>(List.of("apple", "banana", "cherry"));

for (String fruit : fruits.reversed()) {
    System.out.println(fruit);
}
```

The `reversed()` method returns a reverse-ordered *view* of the collection, not a new collection. This means it's efficient and doesn't modify the original.

## Practical Use Case 3: Adding Elements at Both Ends

Sometimes you need to add elements to both the beginning and end of a collection. This is common in scenarios like maintaining a history or a queue with priorities.

### Before Java 21

For a `List`, adding at the beginning was expensive for `ArrayList` (O(n)) and cumbersome for `LinkedList` (you'd use `addFirst()` but only if you declared it as a `LinkedList`).

```java
LinkedList<String> history = new LinkedList<>();
history.add("Page 1");
history.add("Page 2");

// Add to front
history.addFirst("Home");

// Add to end
history.addLast("Page 3");
```

This works, but it ties you to a specific implementation. If you later want to change to an `ArrayList`, you'd have to rewrite the logic.

### With Java 21

```java
List<String> history = new LinkedList<>();
history.add("Page 1");
history.add("Page 2");

// Add to front
history.addFirst("Home");

// Add to end
history.addLast("Page 3");
```

Now you can use the `List` interface and still get `addFirst()` and `addLast()` methods. This is a huge win for code flexibility.

## Practical Use Case 4: Working with LinkedHashSet

`LinkedHashSet` maintains insertion order, but before Java 21, there was no easy way to get the first or last element or to iterate in reverse.

### Before Java 21

```java
LinkedHashSet<String> visited = new LinkedHashSet<>();
visited.add("/home");
visited.add("/about");
visited.add("/contact");

// Get first element
String first = visited.iterator().next();

// Get last element - requires iteration
String last = null;
for (String s : visited) {
    last = s;
}
```

This is clunky and inefficient for large sets.

### With Java 21

```java
SequencedSet<String> visited = new LinkedHashSet<>();
visited.add("/home");
visited.add("/about");
visited.add("/contact");

System.out.println("First: " + visited.getFirst());
System.out.println("Last: " + visited.getLast());

// Reverse iteration
for (String s : visited.reversed()) {
    System.out.println(s);
}
```

Notice that we declared the variable as `SequencedSet`. This is the new interface, and it's implemented by `LinkedHashSet`. This gives us all the benefits of a set (no duplicates) with ordered access.

## Practical Use Case 5: SequencedMap for Configuration Management

Maps also benefit from sequenced access. Consider a configuration system where you want to maintain the order of keys as they were inserted, and you often need to access the first or last entry.

### Before Java 21

```java
LinkedHashMap<String, String> config = new LinkedHashMap<>();
config.put("host", "localhost");
config.put("port", "8080");
config.put("debug", "true");

// Get first entry
String firstKey = config.keySet().iterator().next();
String firstValue = config.get(firstKey);

// Get last entry - again, iterate
Map.Entry<String, String> lastEntry = null;
for (Map.Entry<String, String> e : config.entrySet()) {
    lastEntry = e;
}
```

### With Java 21

```java
SequencedMap<String, String> config = new LinkedHashMap<>();
config.put("host", "localhost");
config.put("port", "8080");
config.put("debug", "true");

System.out.println("First: " + config.firstEntry());
System.out.println("Last: " + config.lastEntry());

// Remove and return the first entry
Map.Entry<String, String> first = config.pollFirstEntry();
System.out.println("Removed: " + first);
```

This is especially useful for LRU caches or for implementing priority-based features where you need to quickly access and remove the oldest or newest entry.

## Practical Use Case 6: Implementing a Simple LRU Cache

Let's put it all together with a real-world example: an LRU (Least Recently Used) cache. An LRU cache evicts the least recently used item when the cache is full. With sequenced collections, this becomes trivial.

### Implementation with SequencedMap

```java
import java.util.*;

public class LRUCache<K, V> {
    private final int capacity;
    private final SequencedMap<K, V> cache;

    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.cache = new LinkedHashMap<>() {
            @Override
            protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                return size() > LRUCache.this.capacity;
            }
        };
    }

    public V get(K key) {
        if (!cache.containsKey(key)) {
            return null;
        }
        V value = cache.remove(key);
        cache.putLast(key, value); // Move to end to mark as recently used
        return value;
    }

    public void put(K key, V value) {
        cache.remove(key);
        cache.putLast(key, value);
    }

    public V getFirst() {
        return cache.firstEntry().getValue();
    }

    public V getLast() {
        return cache.lastEntry().getValue();
    }

    @Override
    public String toString() {
        return cache.toString();
    }
}
```

In this implementation, we use `putLast()` to add or update entries, ensuring that the most recently used items are at the end. When the cache exceeds its capacity, the `removeEldestEntry` method (which is called automatically by `LinkedHashMap`) removes the first entry, which is the least recently used.

This is much cleaner than previous implementations that required manual tracking of access order.

## Practical Use Case 7: Batch Processing with Reverse Order

Imagine you have a list of tasks that need to be processed in reverse order because the last added task has the highest priority. With sequenced collections, this is straightforward.

```java
public void processTasksInReverse(List<Task> tasks) {
    for (Task task : tasks.reversed()) {
        task.execute();
    }
}
```

This is especially useful for undo operations, where you want to undo the most recent action first.

## Performance Considerations

One of the great things about the new methods is that they are designed to be efficient. For example, `getFirst()` and `getLast()` on an `ArrayList` are O(1), while on a `LinkedList` they are also O(1) because the implementation now uses the new interface methods to optimize these operations.

The `reversed()` method returns a view, so it doesn't copy the collection. This is O(1) in time and space. However, note that the view is not modifiable; if you try to call `add()` on a reversed view, you'll get an `UnsupportedOperationException`. This is a deliberate design choice to keep the view simple.

## Migration Tips

If you're working with existing code, you might be wondering how to migrate to the new interfaces. The good news is that the existing implementations already implement the new interfaces. Here's a quick mapping:

- `ArrayList`, `LinkedList`, `Vector` now implement `SequencedCollection`
- `LinkedHashSet` now implements `SequencedSet`
- `LinkedHashMap` now implements `SequencedMap`

So you can simply change your variable types to the new interfaces if you need the extra methods. However, be cautious: if you have code that depends on the specific implementation (e.g., `LinkedList` for its `addFirst()` method), you can now use the interface type instead, which is more flexible.

## Conclusion

Sequenced Collections in Java 21 are a welcome addition that simplifies many everyday programming tasks. Whether you need to access the first and last elements, iterate in reverse, or add elements at both ends, these new interfaces provide a unified and efficient way to do so. By adopting them, you can make your code more readable, maintainable, and less error-prone.

## Key Takeaways

- **Unified API**: Sequenced Collections provide a common set of methods (`getFirst()`, `getLast()`, `addFirst()`, `addLast()`, `reversed()`) across `List`, `Set`, and `Map` implementations that have an encounter order.
- **Efficiency**: The new methods are optimized for the underlying data structures, making operations like accessing the last element of a `LinkedList` O(1) instead of O(n).
- **Reverse Views**: The `reversed()` method returns a view, avoiding expensive copies and allowing efficient reverse iteration.
- **Better Code Quality**: Using sequenced collections eliminates boilerplate and reduces the risk of off-by-one errors and `IndexOutOfBoundsException`.
- **Easy Migration**: Existing implementations like `ArrayList`, `LinkedHashSet`, and `LinkedHashMap` already implement the new interfaces, so you can adopt them incrementally.

Start using Sequenced Collections in your Java 21 projects today, and enjoy cleaner, more expressive code!