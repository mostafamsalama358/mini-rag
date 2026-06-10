# ProcessingEnum.py

## What is this?

Enum for **supported file extensions** during document processing.

## Why does it exist?

The app only processes certain file types.

This enum stores the allowed extensions as constants.

## Values

| Name | Value | Meaning |
|------|-------|---------|
| `TXT` | `".txt"` | Plain text files |
| `PDF` | `".pdf"` | PDF files |

## Where is it used?

| File | How |
|------|-----|
| `src/models/__init__.py` | Re-exported |
| `src/controllers/ProcessController.py` | Chooses loader by extension |
| `src/helpers/config.py` | MIME types in `FILE_ALLOWED_TYPES` (separate check) |

## .NET comparison

```csharp
public enum ProcessingType { Txt = 1, Pdf = 2 }
```
