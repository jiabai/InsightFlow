# Sample Markdown for Immersive Reader

# Understanding Async/Await in JavaScript

Async/await is **syntactic sugar** built on top of Promises.

## Why Async/Await?

Before async/await, developers used callbacks and `Promise` chains. These could lead to "callback hell".

## Basic Syntax

```js
async function fetchData() {
  const response = await fetch('/api/data');
  return response.json();
}
```

### Key Points

- The `async` keyword before a function means the function always returns a **Promise**
- The `await` keyword can only be used inside `async` functions
- Error handling uses standard `try/catch` blocks

## Benefits

1. Cleaner code structure
2. Easier error handling
3. Better stack traces
4. Works with existing Promise APIs

> Async/await has become the standard way to handle asynchronous operations.
