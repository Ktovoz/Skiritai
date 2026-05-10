# AIContext

`AIContext` 是每个 `@step` 方法中作为 `ai` 参数传入的对象。它管理探索/回放生命周期，并暴露操作 API。

## 主要方法

### 导航

```python
await ai.navigate("https://example.com")
```

### 交互

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

### 读取

```python
text = await ai.get_text(".result")
info = await ai.get_page_info()
await ai.screenshot()
```

### 感知

```python
elements = await ai.page_perceive()        # 结构化 DOM 分析
element = await ai.find_element("login")    # 自然语言元素搜索
```

### 等待

```python
await ai.wait_for(3000)                    # 毫秒
await ai.wait_for("#loaded-element")
```

## 执行模式

通过步骤上的 `@step_mode` 或 `run_mode` 属性设置：

```python
ai.run_mode  # "auto"、"explore" 或 "replay"
```
