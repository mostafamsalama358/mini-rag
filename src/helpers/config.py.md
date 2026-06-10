# config.py

## What is this?

Reads all **app settings** from the `.env` file.

Uses Pydantic `BaseSettings` — like **Options pattern** in .NET (`IOptions<Settings>`).

## Why does it exist?

One place for every config value:

- Database connection
- File upload limits
- LLM provider and model names
- Vector database choice
- Celery URLs

## Main class

```python
class Settings(BaseSettings):
    APP_NAME: str
    POSTGRES_HOST: str
    OPENAI_API_KEY: str
    # ... many more
```

## Function

```python
get_settings()  # returns Settings()
```

FastAPI can inject this with `Depends(get_settings)`.

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | Startup reads settings |
| `src/celery_app.py` | Celery config |
| `src/controllers/BaseController.py` | File paths and limits |
| `src/models/BaseDataModel.py` | DB settings |
| `src/routes/base.py` | Welcome endpoint shows app name |
| `src/.env.example` | Lists all variable names |
| `docker/env/.env.example.app` | Same names for Docker |

## .NET comparison

```csharp
public class Settings {
    public string PostgresHost { get; set; }
}
// builder.Services.Configure<Settings>(configuration);
```
