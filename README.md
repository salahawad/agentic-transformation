# Agent Atlas

A self-hosted workspace for preparing a company for agentic transformation. Administrators organize entities and teams, invite employees to describe their digital tools and standard operating procedures, and use a dashboard to identify useful agents to build.

## Run with Docker Compose

Requires Docker with the Compose plugin and Python 3 for the one-time configuration helper.

```bash
python3 scripts/setup.py
docker compose up --build -d --wait
```

Open **http://localhost:8180**. Sign in with `ADMIN_PASSWORD` from the generated `.env` file. The helper creates a random password and preserves an existing `.env`. You can also copy `.env.example` to `.env` and set your own password of at least 16 characters.

The default port binds to the local machine. To share the workspace with employees, use the HTTPS configuration below. Create invitations from the company-facing URL so the copied links contain the correct hostname.

## How to use it

1. **Organization:** add entities (departments, business units, or companies), then teams within them. Rename an entity, or rename a team and move it to another entity. An entity or team can only be deleted once it is empty.
2. **People & assessments:** add an employee’s name, work email, role, entity, and team. Each employee must have a team; the team determines their entity. Deleting an employee from their edit dialog also deletes their saved assessment.
3. Copy the employee’s private assessment link and share it directly. The app does not send emails. Links last 30 days; creating a new link invalidates the previous one. You can revoke access without deleting answers.
4. The employee selects digital tools, adds any custom tools, and describes one or more workflows. Each workflow has a frequency (times per workday, week, month, or year), trigger, outcome, pain points, and ordered steps. Each step records the action, tool, minutes per run, desired agent support, and any required human review. Switch between Text and Diagram to edit the same ordered steps; in Diagram, select a node to edit its details beside the compact flow. Unfinished steps are marked “Needs description,” and you can use arrow keys, Home, and End to navigate the flow.
5. Employees can save drafts, return later, reorder steps, and update a submitted assessment while their link is valid. Each workflow has its own **Save workflow** button that saves only that workflow, and a badge showing whether it is saved, has unsaved changes, or has not been saved yet. The footer lists anything not yet saved. Removing a saved workflow deletes it immediately. Saving any change returns a submitted assessment to draft until it is shared again.
6. **Overview** tracks completion and opportunities. **Digital tools** shows reported usage and edits the list employees choose from: add, rename, recategorize, or remove a tool, or add a custom tool employees reported. Renaming a tool updates saved answers; a removed tool stays in existing answers as a custom tool. **Agent opportunities** shows the supporting workflows, proposed tasks, tools, team, and estimated impact. Filter by entity/team or export opportunities as CSV.

The dashboard updates when you navigate between workspace pages, use the refresh button in the top bar, or reload the page. Editing an employee’s team also moves their workflow evidence and opportunities to the new team.

## Optional sample workspace

Start with fictional data to explore all dashboard views:

```bash
docker compose exec app python -m app.seed_demo
```

This adds 3 entities, 6 teams, and 8 fictional employees. It refuses to run if any entity already exists and never overwrites an existing workspace. Sample employees have no active invitation until you create one in People. For an independent demo instance, use a separate Compose project name so it gets a separate database volume.

## Share with your company over HTTPS

Set `ATLAS_DOMAIN=atlas.your-company.com` in `.env`, point that hostname to this server, and allow inbound ports 80 and 443. Caddy obtains and renews its certificate. Use a hostname eligible for your certificate setup; private-only DNS may require your organization’s existing TLS reverse proxy instead.

```bash
docker compose -f compose.yaml -f compose.https.yaml up --build -d --wait
```

Open `https://atlas.your-company.com`. This configuration removes the direct app port, enables secure session cookies, and puts Caddy in front of the app. It requires Compose 2.24.4 or newer for the `!reset` port override. If your company already has an HTTPS reverse proxy, proxy to `127.0.0.1:8180`, preserve the original `Host` header, and set `COOKIE_SECURE=true` in `.env` instead.

For a trusted development LAN you can set `BIND_ADDRESS` to the server’s LAN IP, then recreate the app. HTTPS is the intended configuration when collecting employee answers across a network. Changing the bind address does not add TLS.

## How suggestions work

Suggestions are deterministic and require no external model, API key, or SaaS account. Only **submitted** assessments contribute agent proposals. Drafts still appear in progress and tool-usage counts.

- Workflows with matching names (ignoring case and repeated spaces) are grouped **within the same team**. Other workflows produce separate assistant proposals.
- “Help me do it” contributes **50%** of the step’s reported time as potential savings.
- “Do it for me” contributes **70%**, reduced to **50%** when a person must review that step.
- “Human only” contributes **0%**. Workflows with no eligible steps produce no proposal.
- Frequency is normalized to a weekly average: 5 workdays per week, 52 weeks per year, and 12 months per year. Existing weekly frequencies retain their stored values until edited.
- Weekly potential = eligible step minutes × runs per week × assistance factor ÷ 60, summed across contributing employees.
- Priority is **High** at 3+ potential hours per week, **Medium** at 1+, and **Explore** below 1.

These are explicit planning assumptions, not measured savings, feasibility guarantees, or agents already built. Each proposal includes its source workflows for review. Validate integration access, business rules, and quality with the team before building a pilot. Similar workflows with different names are not semantically merged.

## Data and access

FastAPI serves the browser interface and API from one container. SQLite uses WAL mode and a named Docker volume (`atlas-data`). No browser build step or external CDN is required. The container runs as a non-root user with a read-only root filesystem.

Administrators use a shared workspace password and 12-hour server-side sessions. Session cookies are HTTP-only and SameSite Strict. Employee links are bearer credentials; only their SHA-256 hashes are stored in the database. The browser removes the token from the address bar and retains it in that tab’s session storage. Closing the tab requires reopening the original invitation link. Cross-origin writes are rejected, public request bodies are bounded, and intake updates use optimistic revisions to prevent overwrites from stale tabs.

Share invitations only with their intended recipients. The administrator can see all assessments. Employees can only access their own answers and cannot change identity or team assignments. Sign-in attempts are limited per client IP. The bundled Caddy configuration passes each visitor’s IP to the app; behind your own reverse proxy the limit is shared, because the app does not trust that proxy’s forwarded client-IP headers. This first version does not include SSO, mail delivery, multiple administrator roles, or automatic agent execution.

Changing `ADMIN_PASSWORD` does not end existing sessions. To sign out every administrator after changing it:

```bash
docker compose exec app python -c "import sqlite3; db=sqlite3.connect('/data/atlas.sqlite3'); db.execute('DELETE FROM sessions'); db.commit(); db.close()"
docker compose up -d --force-recreate app
```

## Operations

```bash
docker compose ps
docker compose logs --tail 100 app
docker compose restart app
docker compose down
```

`down` preserves the data volume. Do not use `down -v` unless you intend to erase all workspace data. Use the same `-f compose.yaml -f compose.https.yaml` arguments for lifecycle commands when using the HTTPS configuration.

Create a consistent SQLite backup using the online backup API:

```bash
mkdir -p backups
docker compose exec app python -c "import sqlite3; source=sqlite3.connect('/data/atlas.sqlite3'); target=sqlite3.connect('/data/atlas-backup.sqlite3'); source.backup(target); target.close(); source.close()"
docker compose cp app:/data/atlas-backup.sqlite3 backups/atlas-backup.sqlite3
docker compose exec app rm /data/atlas-backup.sqlite3
```

Treat backups as company data. To restore, stop the app, replace `/data/atlas.sqlite3` in the named volume with the backup, remove stale `-wal`/`-shm` files while the app is stopped, preserve ownership (UID 10001), and restart. This initial release creates its initial schema on startup; it does not provide a general schema-migration framework. Use one app instance with its local SQLite volume.

## Local development and checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
# Set ADMIN_PASSWORD and DATABASE_PATH in your shell before starting locally.
.venv/bin/uvicorn app.main:app --reload --port 8180
.venv/bin/python -m unittest discover -s tests -v
node --check app/static/app.js
docker compose config --quiet
```

The API tests use temporary databases. A separate browser smoke test exercises organization setup, invitations, tool selection, workflow ordering, draft reload, submission, dashboard suggestions, export, and mobile layouts:

```bash
# Requires Playwright and its Chromium browser in the invoking Python environment.
python3 tests/browser_smoke.py
```

Browser logs and screenshots go in the ignored `artifacts/` directory. The browser test starts and stops an isolated local server on port 18181 and does not modify the Docker workspace.

Implementation references: [FastAPI’s Docker guide](https://fastapi.tiangolo.com/deployment/docker/) and [Docker Compose services](https://docs.docker.com/reference/compose-file/services/), [Compose merge rules](https://docs.docker.com/reference/compose-file/merge/), and [Caddy HTTPS](https://caddyserver.com/docs/quick-starts/https).

UI references: [WCAG 2.2 focus visibility](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum) and [GOV.UK select guidance](https://design-system.service.gov.uk/components/select/).
