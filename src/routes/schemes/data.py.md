# data.py (schemes)

## What is this?

**Pydantic models** for data/upload API request bodies.

Pydantic is like **DTOs** or **request models** in .NET.

## Why does it exist?

FastAPI validates JSON input against these classes.

Wrong data = automatic 422 error response.

## Classes

### ProcessRequest

Used when processing an uploaded file into chunks.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `file_id` | str | — | Which file to process |
| `chunk_size` | int | 100 | Chunk text size |
| `overlap_size` | int | 20 | Overlap between chunks |
| `do_reset` | int | 0 | Reset existing chunks? |

## Where is it used?

| File | How |
|------|-----|
| `src/routes/data.py` | Endpoint parameter type |
| `src/controllers/ProcessController.py` | Business logic uses same values |
| `src/assets/mini-rag-app.postman_collection.json` | Example API calls |

## Note

This is in `routes/schemes/` — **not** the route file itself.

The actual routes live in `src/routes/data.py`.

## .NET comparison

```csharp
public record ProcessRequest(string FileId, int ChunkSize = 100);
```

---

## Code review: upload flow (`src/routes/data.py`)

These blocks sit inside `POST /api/v1/data/upload/{project_id}`. They run after the project is resolved and before the success response.

---

### Block 1 — Validate uploaded file (lines 39–43)

#### 1. What this block does

Hands the uploaded file to a controller for business validation (allowed MIME type, max size) before any disk or DB work.

#### 2. How it works

`DataController()` is constructed inline — no DI here. `validate_uploaded_file` returns a **tuple**: `(bool, signal string)`. The route checks the bool and returns `400 Bad Request` with the signal if validation fails.

In Python, returning multiple values as a tuple is normal; you unpack them into named variables.

#### 3. Equivalent in ASP.NET Core

```csharp
// Option A: inject a service
public async Task<IActionResult> Upload(
    int projectId,
    IFormFile file,
    IDataService dataService)
{
    var (isValid, signal) = dataService.ValidateUploadedFile(file);
    if (!isValid)
        return BadRequest(new { signal });
}

// Option B: FluentValidation / custom IActionFilter on IFormFile
```

`UploadFile` ≈ `IFormFile`. `ResponseSignal` ≈ an enum or string constant you put in the JSON body.

#### 4. Important notes

- Validation is **sync** and cheap — fine to run on the request thread.
- Controller is `new`’d per request instead of injected. In ASP.NET you’d normally use `IDataController` from DI for testability.
- Fail-fast here avoids writing a bad file to disk — same pattern as validating `IFormFile` before `CopyToAsync`.

---

### Block 2 — Resolve path and unique filename (lines 52–56)

#### 1. What this block does

Decides **where** on disk the file will live and generates a collision-safe stored name (random prefix + sanitized original name).

#### 2. How it works

`ProjectController().get_project_path` returns the folder for that project (like a tenant/upload root). `generate_unique_filepath` builds `{project_path}/{random}_{cleaned_filename}` and loops until the path does not already exist. It returns both the full path (for writing) and `file_id` (the stored basename, used later as the asset name).

Note: `project_dir_path` is assigned but unused — the path logic is fully inside `generate_unique_filepath`.

#### 3. Equivalent in ASP.NET Core

```csharp
var projectDir = _projectService.GetProjectPath(projectId);
var (filePath, fileId) = _dataService.GenerateUniqueFilePath(file.FileName, projectId);

// Internally: Path.Combine(projectDir, $"{Guid:N}_{Sanitize(fileName)}")
// while (File.Exists(filePath)) retry
```

Same idea as generating a blob key or `uploads/{projectId}/{guid}_{filename}` before save.

#### 4. Important notes

- **Architecture**: filesystem layout + naming rules belong in a service, not the route — this code follows that split.
- Stored name ≠ original upload name — good for security (no path traversal, no weird characters).
- Sync filesystem checks (`os.path.exists`) are OK for single-server; with multiple app instances you’d want shared storage or DB-level uniqueness.

---

### Block 3 — Stream file to disk (lines 58–62)

#### 1. What this block does

Writes the upload to disk in **chunks** instead of loading the whole file into memory.

#### 2. How it works

`async with aiofiles.open(..., "wb")` opens the file asynchronously. The `while chunk := await file.read(chunk_size)` loop reads from FastAPI’s `UploadFile` stream and writes each chunk until EOF. The walrus operator (`:=`) assigns and tests in one expression — common Python idiom.

On failure, the `except` block logs and returns `400` (lines 62–71, not shown in selection).

#### 3. Equivalent in ASP.NET Core

```csharp
await using var stream = new FileStream(filePath, FileMode.Create);
await file.CopyToAsync(stream); // Kestrel already streams

// Or explicit buffering:
var buffer = new byte[appSettings.FileDefaultChunkSize];
int read;
while ((read = await file.OpenReadStream().ReadAsync(buffer)) > 0)
    await stream.WriteAsync(buffer.AsMemory(0, read));
```

`aiofiles` ≈ async `FileStream` I/O. `UploadFile.read()` ≈ reading from `IFormFile.OpenReadStream()`.

#### 4. Important notes

- **Performance**: chunked async I/O is the right pattern for large uploads — same reason you don’t call `.ReadToEnd()` on big files in .NET.
- Chunk size comes from `app_settings.FILE_DEFAULT_CHUNK_SIZE` (injected via `Depends(get_settings)`) — like `IOptions<FileUploadSettings>`.
- If DB insert fails later, the file may be orphaned on disk — something to handle with a transaction/outbox or cleanup job (same concern in ASP.NET).

---

### Block 4 — Persist asset metadata (lines 85–86)

#### 1. What this block does

After a successful disk write, saves a row/document describing the file (project, type, stored name, size) and gets back the persisted record (including DB-generated `asset_id`).

#### 2. How it works

`Asset` above (lines 78–83) is a **SQLAlchemy model** — think EF entity, not a DTO. `AssetModel.create_instance` is a factory that holds the DB session factory from `request.app.db_client`. `create_asset` opens a session, adds the entity, commits, refreshes (to load server-generated IDs), and returns the entity.

#### 3. Equivalent in ASP.NET Core

```csharp
var asset = new Asset
{
    AssetProjectId = project.ProjectId,
    AssetType = AssetType.File,
    AssetName = fileId,
    AssetSize = new FileInfo(filePath).Length
};

var assetRecord = await _assetRepository.CreateAsync(asset);
// or _dbContext.Assets.Add(asset); await _dbContext.SaveChangesAsync();
```

`AssetModel` ≈ repository or `DbContext` wrapper. `create_instance(db_client)` ≈ resolving a scoped `DbContext` from `HttpContext.RequestServices`.

#### 4. Important notes

- **Order matters**: disk first, then DB — if you reversed it, you’d have DB rows pointing at missing files.
- Model is created via factory + `request.app.db_client`, not FastAPI `Depends()` — works, but less idiomatic than injecting a repository.
- `asset_record.asset_id` becomes the API’s `file_id` in the response — the DB primary key is the client-facing identifier.

---

### Upload pipeline (mental model)

```
UploadFile → validate → generate path → stream to disk → insert Asset → JSON response
```

Same shape as a typical ASP.NET Core upload endpoint: validate → store blob → save metadata → return ID.
