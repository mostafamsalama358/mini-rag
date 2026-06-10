# mini-rag-app.postman_collection.json

## What is this?

**Postman collection** — ready-made API requests to test the app.

Postman is like **Swagger UI** or **REST Client** in VS Code.

## Why does it exist?

You can test all endpoints without writing code:

- Upload file
- Process file
- Push to vector DB
- Search
- Ask RAG question

## How to use

1. Install [Postman](https://www.postman.com/)
2. Import this JSON file
3. Start the app (`uvicorn` or Docker)
4. Run requests in order

## Where is it used?

| File | How |
|------|-----|
| Root `README.md` | Link to download this file |
| `src/routes/base.py` | Welcome endpoint |
| `src/routes/data.py` | Upload/process routes* |
| `src/routes/nlp.py` | Search/answer routes* |
| `src/routes/schemes/data.py` | Request body shapes |
| `src/routes/schemes/nlp.py` | Search/push body shapes |

## .NET comparison

Like a `.http` file or Swagger "Try it out" saved as a shareable collection.
