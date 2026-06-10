# BaseDataModel.py

## What is this?

**Base class** for all database model classes.

In .NET this is like a base repository class.

## Why does it exist?

`ProjectModel`, `AssetModel`, and `ChunkModel` all need:

- A database session (`db_client`)
- App settings from config

They inherit this instead of repeating code.

## Constructor

```python
def __init__(self, db_client: object):
    self.db_client = db_client
    self.app_settings = get_settings()
```

## Where is it used?

| File | Extends BaseDataModel |
|------|----------------------|
| `src/models/ProjectModel.py` | Yes |
| `src/models/AssetModel.py` | Yes |
| `src/models/ChunkModel.py` | Yes |
| `src/helpers/config.py` | Provides settings |
| `src/main.py` | Creates `db_client` passed to models |

## .NET comparison

```csharp
public abstract class BaseRepository {
    protected DbContext _db;
    protected Settings _settings;
}
```
