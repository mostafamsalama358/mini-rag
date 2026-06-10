# minirag.service

## What is this?

A **systemd service file** for Linux servers.

It starts and stops the whole Docker stack automatically.

## Why does it exist?

On a production Linux machine (for example after GitHub Actions deploy), you want:

- App starts when the server boots
- App restarts if it fails
- One command to stop everything

## What it does

| Command | Action |
|---------|--------|
| `ExecStart` | `docker compose up --build -d` in the `docker/` folder |
| `ExecStop` | `docker compose down` |
| `ExecReload` | `docker compose restart` |

## Where is it used?

- Installed on the server as a systemd unit (see `.github/workflows/deploy-develop.yml`)
- Points to `docker/docker-compose.yml` via `WorkingDirectory`

## Note

Change `User=github_user` and `WorkingDirectory` to match your server paths.
