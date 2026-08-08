# Site deploy (canonical production)

The landing site at `https://screenscribe.vetcoders.io` is the **canonical**
production surface. It is served by Caddy from a release directory on a
maintainer-operated VM. GitHub Pages is a **non-canonical mirror** and is never
the source of truth.

## What deploys, and when

Workflow: [`.github/workflows/deploy-site-production.yml`](../../.github/workflows/deploy-site-production.yml)

It runs on:

- a push to `main` touching `site/**` or the workflow file itself, and
- `workflow_dispatch` (manual re-deploy of the current `main`).

Deploys are serialized (`concurrency: site-production-deploy`, never cancelled
in flight).

## How it reaches the server

The deploy talks to the server over **Tailscale**, not the public internet:

1. The job joins the tailnet via `tailscale/github-action` using an OAuth
   client, tagged `tag:ci`. The node is **ephemeral** — the action logs out in
   its post step and the coordination server reaps the node when the job ends.
2. All SSH and rsync traffic then targets the server's **tailnet address**,
   which is stored in the `PROD_SSH_HOST` secret. Nothing about the host is
   hardcoded in the workflow.

This means the server's public SSH port can stay closed. If the tailnet step
fails, the deploy fails before any SSH is attempted — there is no public
fallback path, by design.

## Deploy shape

Every run is atomic and reversible:

1. `rsync` `site/` into a fresh, per-run `releases/<sha>-<run>-<attempt>.tmp/`
   directory (`--delete` only ever acts inside that fresh directory).
2. Validate the release **before** activation: required files present, `assets/`
   present, zero symlinks in content, plus a sha256 manifest in the log.
3. Activate by `mv` + atomic symlink switch of `current`.
4. Smoke-check the live canonical URL, including a byte-exact sha256 comparison
   of the served `index.html` against the deployed commit.
5. On smoke failure, **roll back** to the previous release, re-smoke, and fail
   the workflow.
6. On success, prune old releases (keep the 4 newest; never the live or previous
   target) and reap stale `*.tmp` scratch dirs.

## Required configuration

Repository secrets (GitHub environment `screenscribe-production`):

| Secret | Purpose |
| --- | --- |
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID (needs writable `auth_keys` scope) |
| `TS_OAUTH_SECRET` | Tailscale OAuth client secret |
| `PROD_SSH_HOST` | Server's tailnet address |
| `PROD_SSH_USER` | Deploy user on the server |
| `PROD_SSH_KEY` | Deploy private key (ed25519) |
| `PROD_SSH_KNOWN_HOSTS` | `known_hosts` line for `PROD_SSH_HOST` (`StrictHostKeyChecking=yes` is enforced) |

Tailnet side, owned by the tailnet admin:

- an OAuth client with the writable `auth_keys` scope and `tag:ci` among its
  tags,
- `tagOwners` in the tailnet policy granting that client `tag:ci`,
- an ACL rule allowing `tag:ci` to reach the server's SSH port.

Changing the server's address means updating **both** `PROD_SSH_HOST` and
`PROD_SSH_KNOWN_HOSTS`; a stale `known_hosts` line fails the deploy closed,
which is the intended behaviour.
