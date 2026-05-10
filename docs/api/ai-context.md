# AIContext

`AIContext` is the object passed as the `ai` parameter to every `@step` method. It manages the explore/replay lifecycle and exposes action methods.

## Key Methods

### Navigation

```python
await ai.navigate("https://example.com")
```

### Interactions

```python
await ai.click("#button")
await ai.fill("#input", "text")
await ai.type_text("#input", "hello")
await ai.focus("#element")
await ai.hover("#element")
await ai.scroll(0, 500)
await ai.select_option("#dropdown", "value")
await ai.eval_js("document.title")
```

### Reading

```python
text = await ai.get_text(".result")
info = await ai.get_page_info()
await ai.screenshot()
```

### Perception

```python
elements = await ai.page_perceive()        # Structured DOM analysis
element = await ai.find_element("login")    # Natural language element search
```

### Waiting

```python
await ai.wait_for(3000)                    # ms
await ai.wait_for("#loaded-element")
```

## Execution Modes

Set with `@step_mode` on your step, or the `run_mode` property:

```python
ai.run_mode  # "auto", "explore", or "replay"
```
