# base.py

## What is this?

FastAPI **router** for basic API endpoints.

A router is like a **Controller** class in ASP.NET Core with route attributes.

## Why does it exist?

Every API needs a simple health/welcome endpoint.

This file defines routes under prefix `/api/v1`.

## Endpoints

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/` | App name and version from settings |

## Where is it used?

| File | How |
|------|-----|
| `src/main.py` | `app.include_router(base.base_router)` |
| `src/helpers/config.py` | `APP_NAME`, `APP_VERSION` |
| Postman collection | Can test welcome endpoint |

## Code pattern

```python
base_router = APIRouter(prefix="/api/v1", tags=["api_v1"])
```

## .NET comparison

```csharp
[ApiController]
[Route("api/v1")]
public class BaseController {
    [HttpGet]
    public IActionResult Welcome() => Ok(new { appName, appVersion });
}
```
