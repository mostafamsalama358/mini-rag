# AssetTypeEnum.py

## What is this?

Enum for **asset types** stored in the database.

## Why does it exist?

The `assets` table has an `asset_type` column.

Right now only **files** are supported.

## Values

| Name | Value |
|------|-------|
| `FILE` | `"file"` |

## Where is it used?

| File | How |
|------|-----|
| `src/models/AssetModel.py` | `get_all_project_assets(..., asset_type=...)` |
| `src/routes/data.py` | When saving upload metadata* |

## Future use

You could add more types later (for example `"url"` or `"image"`).

## .NET comparison

```csharp
public enum AssetType { File }
```
