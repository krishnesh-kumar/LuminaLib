# Deploying LuminaLib

## Pipeline overview

```
push/PR ──► CI (.github/workflows/ci.yml)
              ├─ lint
              ├─ unit tests (Postgres service container)
              └─ e2e (full docker-compose stack, Ollama replaced by a fast CI stub)
                     │
                     ▼ (only after CI succeeds on main)
            CD (.github/workflows/cd.yml)
              ├─ build image, push to GHCR (ghcr.io/krishnesh-kumar/luminalib)
              ├─ SSH to the VPS, `docker compose pull && up -d`, run `alembic upgrade head`
              └─ smoke test the live deployment (real Ollama/mistral this time)
```

CI never touches the server, and CD never runs unless CI was green on `main`. If CI is red, CD's `workflow_run` trigger fires but the `if: github.event.workflow_run.conclusion == 'success'` guard on `build-and-push` skips it — nothing gets built or deployed.

## Why this cloud target

The stack is API + worker + beat + Postgres + Redis + MinIO + **Ollama running mistral**. Ollama is the constraint: it needs the full 7B model resident in RAM (~4-5GB) plus room for everything else, so anything free-tier-sized (512MB-1GB) won't run it. The cheapest way to get enough RAM in one place, with everything reachable over a private docker network exactly like local dev, is a single VPS running your existing `docker-compose.yml` as-is.

**Recommended: Hetzner Cloud CPX31** — 4 vCPU, 8GB RAM, 160GB disk, ~€13.10/mo (~$14). Comfortable headroom for Postgres + Redis + MinIO + api/worker/beat + mistral running concurrently.
- Cheaper but tighter: **CX22** (2 vCPU, 4GB RAM, ~€4.59/mo) — works, but mistral inference will compete with everything else for memory; fine for light/demo traffic, watch `docker stats` under load.
- Any equivalent works too (DigitalOcean 8GB Droplet ~$48/mo is pricier for the same RAM; Hetzner and Vultr's high-memory plans are the best $/GB right now).

## One-time server setup

1. **Create the server** (Hetzner Cloud console or CLI), Ubuntu 22.04/24.04, add your SSH public key at creation time.
2. **Install Docker** (as root or a sudo user):
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
   This installs the `docker compose` plugin too.
3. **Create a deploy user** (don't deploy as root):
   ```bash
   adduser deploy
   usermod -aG docker deploy
   mkdir -p /home/deploy/.ssh
   # add the CI's public key (see below) to /home/deploy/.ssh/authorized_keys
   ```
4. **Firewall** — only SSH, HTTP, HTTPS need to be open:
   ```bash
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```
5. **App directory**:
   ```bash
   sudo -u deploy mkdir -p /home/deploy/luminalib
   ```
6. **Create the production `.env`** on the server (never committed to git — copy `.env.example` from this repo as a starting point, fill in real secrets):
   ```bash
   sudo -u deploy nano /home/deploy/luminalib/.env
   ```
   Generate a strong `JWT_SECRET_KEY` with `openssl rand -hex 32`, and strong, unique `POSTGRES_PASSWORD` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`. Keep the password in `POSTGRES_PASSWORD` and inside `DATABASE_URL` identical (see the comment in `.env.example` — compose can't cross-reference the two automatically).
7. **DNS (optional but recommended)** — point an A record (e.g. `api.yourdomain.com`) at the server's IP. Caddy (already wired up in `docker-compose.prod.yml`) will automatically get you a free Let's Encrypt HTTPS cert for that domain. If you skip this, set `DEPLOY_DOMAIN` to empty/unset and Caddy serves plain HTTP on port 80 instead — fine for a quick demo, not for real user data.

## GitHub Actions secrets

Add these under **Settings → Secrets and variables → Actions** (or under a `production` Environment for an extra manual-approval gate — the `deploy` job already targets `environment: production`):

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | Private key matching the public key in `deploy`'s `authorized_keys` (generate a dedicated CI keypair, don't reuse your personal one) |
| `DEPLOY_SSH_PORT` | `22` |
| `DEPLOY_APP_DIR` | `/home/deploy/luminalib` |
| `DEPLOY_DOMAIN` | `api.yourdomain.com` (or leave empty for HTTP-only) |
| `DEPLOY_BASE_URL` | `https://api.yourdomain.com` (or `http://<server-ip>` if no domain) — used by the post-deploy smoke test |
| `GHCR_PULL_TOKEN` | A GitHub PAT with `read:packages` scope, so the server can `docker login ghcr.io` and pull the (private, by default) image. Not needed if you make the GHCR package public. |

`GITHUB_TOKEN` (already provided automatically) is used to *push* the image to GHCR from the Actions runner — no secret to add for that part.

## What happens on deploy

`cd.yml`'s `deploy` job copies `docker-compose.yml`, `docker-compose.prod.yml`, and `Caddyfile` to the server, then over SSH:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head
```

The prod overlay (`docker-compose.prod.yml`):
- Runs api/worker/beat from the GHCR image (`${IMAGE_NAME}:${IMAGE_TAG}`, e.g. `ghcr.io/krishnesh-kumar/luminalib:<git-sha>` — `IMAGE_NAME`/`IMAGE_TAG` are exported by the deploy step, computed with the repo name lowercased since GHCR requires lowercase image refs), not a local build, and drops the dev bind-mount and `--reload`.
- Stops publishing db/redis/minio/ollama ports to the public interface — they're only reachable over the internal compose network, exactly as before but now not exposed to the internet.
- Adds Caddy in front of the API for TLS.

## Rolling back

Every image is tagged with its git short-SHA (visible as the `build-and-push` job's output / in GHCR). To roll back manually:
```bash
ssh deploy@<host>
cd /home/deploy/luminalib
export IMAGE_NAME=ghcr.io/krishnesh-kumar/luminalib
IMAGE_TAG=<previous-sha> docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Manual trigger

`cd.yml` also has a `workflow_dispatch` trigger, so you can re-run build+deploy from the Actions tab without needing a new push (useful for re-deploying the same commit, or the very first deploy).
