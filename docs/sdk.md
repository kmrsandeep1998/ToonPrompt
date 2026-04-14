# SDK

ToonPrompt exposes a Python SDK:

```python
from toonprompt import ToonPrompt

client = ToonPrompt(profile="default")
result = client.transform('{"id":1,"name":"node"}')
print(result.output)
print(result.delta_tokens)
```

Async transform:

```python
result = await client.transform_async(prompt)
```

Streaming output chunks:

```python
for chunk in client.stream(prompt):
    print(chunk, end="")
```
