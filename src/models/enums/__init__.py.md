# __init__.py

## What is this?

Marks `models/enums/` as a Python **package**.

The file is **empty** — that is normal.

## Why does it exist?

Python needs this file (or a namespace package) so you can write:

```python
from models.enums.ProcessingEnum import ProcessingEnum
```

## Where is it used?

- Imported indirectly when any code uses files inside `models/enums/`

## .NET comparison

Like an empty folder with a namespace — no code, just structure.
