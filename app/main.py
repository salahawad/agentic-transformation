import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

DB_PATH = Path(os.environ.get('DATABASE_PATH', 'data/atlas.sqlite3'))
PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
if len(PASSWORD) < 16:
    raise RuntimeError('ADMIN_PASSWORD must contain at least 16 characters. Run scripts/setup.py.')
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
STATIC = Path(__file__).parent / 'static'
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
DraftText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


DEFAULT_TOOLS = [
    (name, category)
    for category, names in {
        'Communication': ['Microsoft Teams', 'Slack', 'Outlook', 'Gmail', 'Zoom'],
        'Documents & knowledge': ['Microsoft Excel', 'Google Sheets', 'Microsoft Word', 'Google Docs', 'Notion', 'Confluence', 'SharePoint', 'Google Drive'],
        'Projects & operations': ['Jira', 'Asana', 'Trello', 'Monday.com', 'ServiceNow'],
        'Business systems': ['Salesforce', 'HubSpot', 'SAP', 'Odoo', 'QuickBooks', 'Workday', 'Power BI', 'Tableau'],
        'Design & development': ['Figma', 'Canva', 'GitHub', 'GitLab', 'VS Code'],
        'AI assistants': ['ChatGPT', 'Claude', 'Gemini', 'Microsoft Copilot'],
    }.items() for name in names
]


def initialize():
    with database() as db:
        db.execute('PRAGMA journal_mode=WAL')
        # Seed defaults only when the table is first created, so tools an administrator removed stay removed.
        new_catalog = not db.execute("SELECT 1 FROM sqlite_master WHERE name='tools'").fetchone()
        db.executescript('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE);
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY, entity_id INTEGER NOT NULL REFERENCES entities(id),
            name TEXT NOT NULL COLLATE NOCASE, UNIQUE(entity_id, name));
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            role TEXT NOT NULL, team_id INTEGER NOT NULL REFERENCES teams(id),
            invite_hash TEXT UNIQUE, invite_expires INTEGER, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS assessments (
            employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
            payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
            revision INTEGER NOT NULL DEFAULT 1, updated_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL,
            collaborator_id INTEGER REFERENCES collaborators(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS login_attempts (client TEXT PRIMARY KEY, attempts INTEGER NOT NULL, until_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS tools (id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, category TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS collaborators (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            invite_hash TEXT UNIQUE, invite_expires INTEGER, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS collaborator_entities (
            collaborator_id INTEGER NOT NULL REFERENCES collaborators(id) ON DELETE CASCADE,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            PRIMARY KEY (collaborator_id, entity_id));
        ''')
        if new_catalog:
            db.executemany('INSERT INTO tools(name,category) VALUES (?,?)', DEFAULT_TOOLS)
        # Sessions created before collaborators existed all belong to the workspace administrator.
        if 'collaborator_id' not in {r['name'] for r in db.execute('PRAGMA table_info(sessions)')}:
            db.execute('ALTER TABLE sessions ADD COLUMN collaborator_id INTEGER REFERENCES collaborators(id) ON DELETE CASCADE')


initialize()
app = FastAPI(title='Agent Atlas', docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'DELETE', 'PATCH'}:
        origin = request.headers.get('origin')
        parsed = urlsplit(origin) if origin else None
        if request.headers.get('sec-fetch-site') == 'cross-site' or (parsed and parsed.netloc != request.headers.get('host')):
            return Response('Cross-origin writes are not allowed', status_code=403)
        # Bound JSON parsing and validation work for public intake endpoints.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1_000_000:
                return Response('Request too large', status_code=413)
        request._body = bytes(body)
    try:
        response = await call_next(request)
    except sqlite3.IntegrityError:
        response = Response('A record with these details already exists or its parent is missing.', status_code=409)
    response.headers.update({
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'X-Frame-Options': 'DENY',
        'Cache-Control': 'no-store',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    })
    return response


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require_access(request: Request):
    """None for the workspace administrator; for a collaborator, their name and the entity ids they manage."""
    token = request.cookies.get('atlas_session', '')
    with database() as db:
        session = db.execute('''SELECT s.collaborator_id,c.name FROM sessions s LEFT JOIN collaborators c ON c.id=s.collaborator_id
            WHERE s.token_hash=? AND s.expires_at>?''', (digest(token), time.time())).fetchone()
        if not session:
            raise HTTPException(401, 'Please sign in to your workspace.')
        if session['collaborator_id'] is None:
            return None
        entity_ids = [r[0] for r in db.execute('SELECT entity_id FROM collaborator_entities WHERE collaborator_id=?', (session['collaborator_id'],))]
    return {'name': session['name'], 'entity_ids': entity_ids}


def require_admin(viewer=Depends(require_access)):
    if viewer is not None:
        raise HTTPException(403, 'Only the workspace administrator can do this.')


# Routes stay administrator-only unless they take `viewer=Access` and check every record with check_scope.
Admin = Depends(require_admin)
Access = Depends(require_access)
SCOPE_QUERIES = {
    'Entity': 'SELECT id FROM entities WHERE id=?',
    'Team': 'SELECT entity_id FROM teams WHERE id=?',
    'Employee': 'SELECT t.entity_id FROM employees e JOIN teams t ON t.id=e.team_id WHERE e.id=?',
}


def check_scope(db, viewer, kind, identifier):
    """Collaborators get 404 for records outside their entities, so other entities stay invisible."""
    if viewer is None:
        return
    row = db.execute(SCOPE_QUERIES[kind], (identifier,)).fetchone()
    if not row or row[0] not in viewer['entity_ids']:
        raise HTTPException(404, f'{kind} not found.')


def require_employee(authorization: str = Header(default='')):
    token = authorization.removeprefix('Bearer ')
    with database() as db:
        person = db.execute('''SELECT e.id,e.name,e.email,e.role,e.team_id,t.name AS team_name,
            t.entity_id,n.name AS entity_name FROM employees e JOIN teams t ON t.id=e.team_id
            JOIN entities n ON n.id=t.entity_id WHERE e.invite_hash=? AND e.invite_expires>?''',
            (digest(token), time.time())).fetchone()
    if not person:
        raise HTTPException(401, 'This invitation has expired or is invalid. Please ask your administrator for a new link.')
    return dict(person)


Employee = Depends(require_employee)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(StrictModel):
    password: str = Field(max_length=512)


@app.post('/api/login')
def login(body: Login, request: Request, response: Response):
    client = request.client.host if request.client else 'unknown'
    now = int(time.time())
    with database() as db:
        db.execute('DELETE FROM login_attempts WHERE until_at<?', (now,))
        attempt = db.execute('SELECT * FROM login_attempts WHERE client=?', (client,)).fetchone()
        if attempt and attempt['attempts'] >= 10:
            raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
        if not hmac.compare_digest(body.password.encode(), PASSWORD.encode()):
            db.execute('''INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(client)
                DO UPDATE SET attempts=attempts+1''', (client, now + 900))
            # Commit the failed attempt before returning an authentication error.
            response.status_code = 401
            return {'detail': 'Incorrect workspace password.'}
        db.execute('DELETE FROM login_attempts WHERE client=?', (client,))
        start_session(db, response)
    return {'ok': True}


def start_session(db, response, collaborator_id=None):
    now = int(time.time())
    db.execute('DELETE FROM sessions WHERE expires_at<?', (now,))
    token = secrets.token_urlsafe(32)
    db.execute('INSERT INTO sessions(token_hash,expires_at,collaborator_id) VALUES (?,?,?)', (digest(token), now + 43200, collaborator_id))
    response.set_cookie('atlas_session', token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=43200)


class Join(StrictModel):
    token: str = Field(max_length=200)


@app.post('/api/join')
def join(body: Join, response: Response):
    """Exchange a collaborator's private link for a session limited to their entities."""
    with database() as db:
        collaborator = db.execute('SELECT id FROM collaborators WHERE invite_hash=? AND invite_expires>?',
            (digest(body.token), time.time())).fetchone()
        if not collaborator:
            raise HTTPException(401, 'This link has expired or is invalid. Ask the workspace administrator for a new link.')
        start_session(db, response, collaborator['id'])
    return {'ok': True}


@app.post('/api/logout')
def logout(request: Request, response: Response):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(request.cookies.get('atlas_session', '')),))
    response.delete_cookie('atlas_session')
    return {'ok': True}


@app.get('/api/health')
def health():
    with database() as db:
        db.execute('SELECT 1')
    return {'status': 'ok'}


class ToolInput(StrictModel):
    name: Text
    category: Text


def retag_tool(db, old, new):
    """Point saved answers naming `old`, or a case variant of `new`, at `new` so usage counts stay together."""
    # ponytail: a tab opened before the rename still holds the old name and saves it back as a custom tool.
    names = {old.casefold(), new.casefold()}

    def rename(tool):
        return new if tool.casefold() in names else tool

    for row in db.execute('SELECT employee_id,payload FROM assessments').fetchall():
        payload = json.loads(row['payload'])
        payload['tools'] = list(dict.fromkeys(map(rename, payload['tools'])))
        for workflow in payload['workflows']:
            for step in workflow['steps']:
                step['tool'] = rename(step['tool'])
        db.execute('UPDATE assessments SET payload=? WHERE employee_id=?', (json.dumps(payload), row['employee_id']))


@app.post('/api/admin/tools', dependencies=[Admin], status_code=201)
def create_tool(body: ToolInput):
    with database() as db:
        identifier = db.execute('INSERT INTO tools(name,category) VALUES (?,?)', (body.name, body.category)).lastrowid
        retag_tool(db, body.name, body.name)
    return {'id': identifier, **body.model_dump()}


@app.put('/api/admin/tools/{tool_id}', dependencies=[Admin])
def edit_tool(tool_id: int, body: ToolInput):
    with database() as db:
        old = db.execute('SELECT name FROM tools WHERE id=?', (tool_id,)).fetchone()
        if not old:
            raise HTTPException(404, 'Tool not found.')
        db.execute('UPDATE tools SET name=?,category=? WHERE id=?', (body.name, body.category, tool_id))
        retag_tool(db, old['name'], body.name)
    return {'ok': True}


# Saved answers keep a removed tool; reports then list it as a custom tool.
@app.delete('/api/admin/tools/{tool_id}', dependencies=[Admin])
def delete_tool(tool_id: int):
    with database() as db:
        if not db.execute('DELETE FROM tools WHERE id=?', (tool_id,)).rowcount:
            raise HTTPException(404, 'Tool not found.')
    return {'ok': True}


class EntityInput(StrictModel):
    name: Text


class TeamInput(EntityInput):
    entity_id: int = Field(gt=0)


Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')]


class PersonInput(StrictModel):
    name: Text
    email: Email
    role: Text
    team_id: int = Field(gt=0)


class CollaboratorInput(StrictModel):
    name: Text
    email: Email
    entity_ids: list[int] = Field(min_length=1, max_length=500)


@app.post('/api/admin/entities', dependencies=[Admin], status_code=201)
def create_entity(body: EntityInput):
    with database() as db:
        identifier = db.execute('INSERT INTO entities(name) VALUES (?)', (body.name,)).lastrowid
    return {'id': identifier, **body.model_dump()}


@app.post('/api/admin/teams', status_code=201)
def create_team(body: TeamInput, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Entity', body.entity_id)
        identifier = db.execute('INSERT INTO teams(entity_id,name) VALUES (?,?)', (body.entity_id, body.name)).lastrowid
    return {'id': identifier, **body.model_dump()}


@app.put('/api/admin/entities/{entity_id}', dependencies=[Admin])
def rename_entity(entity_id: int, body: EntityInput):
    with database() as db:
        if not db.execute('UPDATE entities SET name=? WHERE id=?', (body.name, entity_id)).rowcount:
            raise HTTPException(404, 'Entity not found.')
    return {'ok': True}


@app.put('/api/admin/teams/{team_id}')
def edit_team(team_id: int, body: TeamInput, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Team', team_id)
        check_scope(db, viewer, 'Entity', body.entity_id)
        if not db.execute('UPDATE teams SET name=?,entity_id=? WHERE id=?', (body.name, body.entity_id, team_id)).rowcount:
            raise HTTPException(404, 'Team not found.')
    return {'ok': True}


# Deleting a parent never cascades, so employee answers are only removed by deleting that employee.
@app.delete('/api/admin/entities/{entity_id}', dependencies=[Admin])
def delete_entity(entity_id: int):
    with database() as db:
        if db.execute('SELECT 1 FROM teams WHERE entity_id=?', (entity_id,)).fetchone():
            raise HTTPException(409, 'Delete or move this entity’s teams first.')
        if not db.execute('DELETE FROM entities WHERE id=?', (entity_id,)).rowcount:
            raise HTTPException(404, 'Entity not found.')
    return {'ok': True}


@app.delete('/api/admin/teams/{team_id}')
def delete_team(team_id: int, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Team', team_id)
        if db.execute('SELECT 1 FROM employees WHERE team_id=?', (team_id,)).fetchone():
            raise HTTPException(409, 'Move or delete this team’s employees first.')
        if not db.execute('DELETE FROM teams WHERE id=?', (team_id,)).rowcount:
            raise HTTPException(404, 'Team not found.')
    return {'ok': True}


def new_invitation(db, identifier, table='employees'):
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + 30 * 86400
    db.execute(f'UPDATE {table} SET invite_hash=?,invite_expires=? WHERE id=?', (digest(token), expires, identifier))
    return {'token': token, 'expires_at': expires}


@app.post('/api/admin/employees', status_code=201)
def create_employee(body: PersonInput, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Team', body.team_id)
        identifier = db.execute('INSERT INTO employees(name,email,role,team_id,created_at) VALUES (?,?,?,?,?)',
            (body.name, body.email.lower(), body.role, body.team_id, int(time.time()))).lastrowid
        invitation = new_invitation(db, identifier)
    return {'id': identifier, **invitation}


@app.put('/api/admin/employees/{employee_id}')
def edit_employee(employee_id: int, body: PersonInput, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Employee', employee_id)
        check_scope(db, viewer, 'Team', body.team_id)
        result = db.execute('UPDATE employees SET name=?,email=?,role=?,team_id=? WHERE id=?',
            (body.name, body.email.lower(), body.role, body.team_id, employee_id))
        if not result.rowcount:
            raise HTTPException(404, 'Employee not found.')
    return {'ok': True}


@app.delete('/api/admin/employees/{employee_id}')
def delete_employee(employee_id: int, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Employee', employee_id)
        # The assessment is removed by ON DELETE CASCADE.
        if not db.execute('DELETE FROM employees WHERE id=?', (employee_id,)).rowcount:
            raise HTTPException(404, 'Employee not found.')
    return {'ok': True}


@app.post('/api/admin/employees/{employee_id}/invite')
def issue_invite(employee_id: int, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Employee', employee_id)
        if not db.execute('SELECT 1 FROM employees WHERE id=?', (employee_id,)).fetchone():
            raise HTTPException(404, 'Employee not found.')
        invitation = new_invitation(db, employee_id)
    return invitation


@app.delete('/api/admin/employees/{employee_id}/invite')
def revoke_invite(employee_id: int, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Employee', employee_id)
        result = db.execute('UPDATE employees SET invite_hash=NULL,invite_expires=NULL WHERE id=?', (employee_id,))
        if not result.rowcount:
            raise HTTPException(404, 'Employee not found.')
    return {'ok': True}


def grant_entities(db, collaborator_id, entity_ids):
    db.execute('DELETE FROM collaborator_entities WHERE collaborator_id=?', (collaborator_id,))
    db.executemany('INSERT INTO collaborator_entities VALUES (?,?)', [(collaborator_id, e) for e in set(entity_ids)])


@app.post('/api/admin/collaborators', dependencies=[Admin], status_code=201)
def create_collaborator(body: CollaboratorInput):
    with database() as db:
        identifier = db.execute('INSERT INTO collaborators(name,email,created_at) VALUES (?,?,?)',
            (body.name, body.email.lower(), int(time.time()))).lastrowid
        grant_entities(db, identifier, body.entity_ids)
        invitation = new_invitation(db, identifier, 'collaborators')
    return {'id': identifier, **invitation}


@app.put('/api/admin/collaborators/{collaborator_id}', dependencies=[Admin])
def edit_collaborator(collaborator_id: int, body: CollaboratorInput):
    with database() as db:
        if not db.execute('UPDATE collaborators SET name=?,email=? WHERE id=?', (body.name, body.email.lower(), collaborator_id)).rowcount:
            raise HTTPException(404, 'Collaborator not found.')
        grant_entities(db, collaborator_id, body.entity_ids)
    return {'ok': True}


@app.delete('/api/admin/collaborators/{collaborator_id}', dependencies=[Admin])
def delete_collaborator(collaborator_id: int):
    with database() as db:
        # Their entity grants and signed-in sessions are removed by ON DELETE CASCADE.
        if not db.execute('DELETE FROM collaborators WHERE id=?', (collaborator_id,)).rowcount:
            raise HTTPException(404, 'Collaborator not found.')
    return {'ok': True}


@app.post('/api/admin/collaborators/{collaborator_id}/invite', dependencies=[Admin])
def issue_collaborator_link(collaborator_id: int):
    with database() as db:
        if not db.execute('SELECT 1 FROM collaborators WHERE id=?', (collaborator_id,)).fetchone():
            raise HTTPException(404, 'Collaborator not found.')
        invitation = new_invitation(db, collaborator_id, 'collaborators')
    return invitation


class Step(StrictModel):
    action: DraftText
    details: LongText = ''
    tool: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] = ''
    minutes: float = Field(default=5, ge=0, le=10080)
    support: Literal['manual', 'assist', 'automate'] = 'assist'
    human_review: bool = False


FREQUENCY_FACTORS = {'day': 5, 'week': 1, 'month': 12 / 52, 'year': 1 / 52}


class Workflow(StrictModel):
    name: DraftText
    trigger: LongText = ''
    outcome: LongText = ''
    runs_per_week: float = Field(default=1, gt=0, le=1000)
    frequency_count: float | None = Field(default=None, gt=0, le=52000)
    frequency_unit: Literal['day', 'week', 'month', 'year'] | None = None
    pain_points: LongText = ''
    steps: list[Step] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def normalize_frequency(self):
        if (self.frequency_count is None) != (self.frequency_unit is None):
            raise ValueError('Provide both the frequency count and period.')
        if self.frequency_unit is not None:
            weekly = self.frequency_count * FREQUENCY_FACTORS[self.frequency_unit]
            if not 0 < weekly <= 1000:
                raise ValueError('Frequency must be at most 1,000 runs per week.')
            self.runs_per_week = weekly
        return self


class Assessment(StrictModel):
    tools: list[Text] = Field(default_factory=list, max_length=100)
    workflows: list[Workflow] = Field(default_factory=list, max_length=30)
    notes: LongText = ''
    status: Literal['draft', 'submitted'] = 'draft'
    revision: int = Field(default=0, ge=0)

    @field_validator('tools')
    @classmethod
    def normalize_tools(cls, tools):
        return list({t.casefold(): t for t in tools}.values())


@app.get('/api/intake')
def get_intake(person=Employee):
    with database() as db:
        row = db.execute('SELECT * FROM assessments WHERE employee_id=?', (person['id'],)).fetchone()
        catalog = [dict(r) for r in db.execute('SELECT * FROM tools ORDER BY id')]
    assessment = {'tools': [], 'workflows': [], 'notes': '', 'status': 'draft', 'revision': 0}
    if row:
        assessment = {**json.loads(row['payload']), 'status': row['status'], 'revision': row['revision']}
    return {'employee': person, 'assessment': assessment, 'catalog': catalog}


@app.put('/api/intake')
def save_intake(body: Assessment, person=Employee):
    if body.status == 'submitted' and (not body.tools or not body.workflows):
        raise HTTPException(422, 'Select at least one tool and describe at least one workflow before submitting.')
    with database() as db:
        canonical = {r['name'].casefold(): r['name'] for r in db.execute('SELECT name FROM tools')}
    body.tools = [canonical.get(t.casefold(), t) for t in body.tools]
    selected = {t.casefold(): t for t in body.tools}
    for workflow in body.workflows:
        if body.status == 'submitted' and (not workflow.name or not workflow.steps or any(not s.action for s in workflow.steps)):
            raise HTTPException(422, 'Every submitted workflow needs a name and at least one named step.')
        for step in workflow.steps:
            if step.tool and step.tool.casefold() not in selected:
                raise HTTPException(422, f'Add {step.tool} to your tools before using it in a workflow.')
            if step.tool:
                step.tool = selected[step.tool.casefold()]
    payload = json.dumps(body.model_dump(exclude={'revision', 'status'}))
    now = int(time.time())
    with database() as db:
        # A write lock makes revision checking and the update atomic across tabs.
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT revision FROM assessments WHERE employee_id=?', (person['id'],)).fetchone()
        revision = row['revision'] if row else 0
        if revision != body.revision:
            raise HTTPException(409, 'This form changed in another tab. Reload the page before saving again.')
        db.execute('''INSERT INTO assessments VALUES (?,?,?,?,?) ON CONFLICT(employee_id)
            DO UPDATE SET payload=excluded.payload,status=excluded.status,revision=excluded.revision,updated_at=excluded.updated_at''',
            (person['id'], payload, body.status, revision + 1, now))
    return {'revision': revision + 1, 'status': body.status, 'updated_at': now}


def build_workspace(viewer=None):
    with database() as db:
        entities = [dict(r) for r in db.execute('SELECT * FROM entities ORDER BY name')]
        teams = [dict(r) for r in db.execute('SELECT * FROM teams ORDER BY name')]
        catalog = [dict(r) for r in db.execute('SELECT * FROM tools ORDER BY id')]
        people = [dict(r) for r in db.execute('''SELECT e.id,e.name,e.email,e.role,e.team_id,e.invite_expires,
            t.name AS team_name,t.entity_id,n.name AS entity_name,
            COALESCE(a.status,'invited') AS status,a.updated_at,a.payload
            FROM employees e JOIN teams t ON t.id=e.team_id JOIN entities n ON n.id=t.entity_id
            LEFT JOIN assessments a ON a.employee_id=e.id ORDER BY e.name''')]
        collaborators = [dict(r) for r in db.execute('SELECT id,name,email,invite_expires FROM collaborators ORDER BY name')]
        grants = db.execute('SELECT collaborator_id,entity_id FROM collaborator_entities').fetchall()
    for collaborator in collaborators:
        collaborator['entity_ids'] = [entity for owner, entity in grants if owner == collaborator['id']]
    if viewer is not None:
        # Filter before building opportunities so nothing from other entities reaches a collaborator.
        entities = [e for e in entities if e['id'] in viewer['entity_ids']]
        teams = [t for t in teams if t['entity_id'] in viewer['entity_ids']]
        people = [p for p in people if p['entity_id'] in viewer['entity_ids']]
        collaborators = []
    candidates = {}
    for person in people:
        assessment = json.loads(person.pop('payload') or '{}')
        person['tools'] = assessment.get('tools', [])
        person['workflow_count'] = len(assessment.get('workflows', []))
        if person['status'] != 'submitted':
            continue
        for workflow in assessment.get('workflows', []):
            eligible = [s for s in workflow['steps'] if s['support'] != 'manual' and s['minutes'] > 0]
            if not eligible:
                continue
            key = (person['team_id'], ' '.join(workflow['name'].casefold().split()))
            if key not in candidates:
                candidates[key] = {
                    'name': workflow['name'] + ' assistant',
                    'entity_id': person['entity_id'], 'entity_name': person['entity_name'],
                    'team_id': person['team_id'], 'team_name': person['team_name'],
                    'people': {}, 'tools': set(), 'weekly_minutes': 0, 'estimated_minutes': 0,
                    'actions': set(), 'human_review': False, 'workflow_name': workflow['name'],
                    'evidence': [],
                }
            candidate = candidates[key]
            candidate['people'][person['id']] = person['name']
            candidate['tools'].update(s['tool'] for s in eligible if s['tool'])
            weekly = sum(s['minutes'] for s in workflow['steps']) * workflow['runs_per_week']
            estimate = sum(s['minutes'] * (0.5 if s['support'] == 'assist' or s['human_review'] else 0.7) for s in eligible) * workflow['runs_per_week']
            candidate['weekly_minutes'] += weekly
            candidate['estimated_minutes'] += estimate
            candidate['human_review'] |= any(s['human_review'] or s['support'] == 'manual' for s in workflow['steps'])
            candidate['actions'].update(s['action'] for s in eligible)
            candidate['evidence'].append({'employee': person['name'], **workflow})
    opportunities = []
    for index, candidate in enumerate(candidates.values()):
        hours = candidate.pop('estimated_minutes') / 60
        candidate.update({
            'id': index + 1, 'estimated_hours': round(hours, 2),
            'weekly_hours': round(candidate.pop('weekly_minutes') / 60, 2),
            'priority': 'High' if hours >= 3 else 'Medium' if hours >= 1 else 'Explore',
            'people': list(candidate['people'].values()), 'tools': sorted(candidate['tools']),
            'actions': sorted(candidate['actions']),
            'rationale': 'Suggested from employee-marked assistance and automation steps. Validate integrations and access before a pilot.',
        })
        opportunities.append(candidate)
    opportunities.sort(key=lambda c: c['estimated_hours'], reverse=True)
    return {'entities': entities, 'teams': teams, 'employees': people, 'opportunities': opportunities, 'catalog': catalog,
            'collaborators': collaborators, 'viewer': viewer}


@app.get('/api/admin/workspace')
def workspace(viewer=Access):
    return build_workspace(viewer)


@app.get('/api/admin/employees/{employee_id}/assessment')
def view_assessment(employee_id: int, viewer=Access):
    with database() as db:
        check_scope(db, viewer, 'Employee', employee_id)
        row = db.execute('SELECT payload,status,revision,updated_at FROM assessments WHERE employee_id=?', (employee_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'This employee has not saved an assessment yet.')
    return {**json.loads(row['payload']), 'status': row['status'], 'revision': row['revision'], 'updated_at': row['updated_at']}


@app.get('/')
@app.get('/intake')
@app.get('/join')
def index():
    return FileResponse(STATIC / 'index.html')


app.mount('/static', StaticFiles(directory=STATIC), name='static')
