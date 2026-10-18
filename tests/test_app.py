import os
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ['ADMIN_PASSWORD'] = 'test-workspace-password-123'
os.environ['DATABASE_PATH'] = str(Path(_tmp.name) / 'bootstrap.sqlite3')
from fastapi.testclient import TestClient
from app import main


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        main.DB_PATH = Path(self.directory.name) / 'atlas.sqlite3'
        main.initialize()
        self.client = TestClient(main.app)
        self.client.post('/api/login', json={'password': main.PASSWORD})

    def tearDown(self):
        self.client.close()
        self.directory.cleanup()

    def person(self, name='Alex Morgan', email='alex@example.com'):
        workspace = self.client.get('/api/admin/workspace').json()
        if not workspace['entities']:
            entity = self.client.post('/api/admin/entities', json={'name': 'Operations'}).json()['id']
            self.client.post('/api/admin/teams', json={'name': 'Planning', 'entity_id': entity})
        team = self.client.get('/api/admin/workspace').json()['teams'][0]['id']
        response = self.client.post('/api/admin/employees', json={'name': name, 'email': email, 'role': 'Analyst', 'team_id': team})
        self.assertEqual(response.status_code, 201, response.text)
        person = response.json()
        return person, {'Authorization': 'Bearer ' + person['token']}

    @staticmethod
    def assessment():
        return {'tools': ['chatgpt', 'ChatGPT', ' Microsoft Excel '], 'workflows': [{
            'name': 'Weekly reporting', 'runs_per_week': 5, 'trigger': 'Monday',
            'outcome': 'A shared report', 'steps': [
                {'action': 'Draft summary', 'tool': 'chatgpt', 'minutes': 10, 'support': 'assist'},
                {'action': 'Update spreadsheet', 'tool': 'Microsoft Excel', 'minutes': 20, 'support': 'automate'},
                {'action': 'Approve report', 'minutes': 30, 'support': 'manual'},
            ]}], 'status': 'submitted', 'revision': 0}

    def test_admin_access_and_session_revocation(self):
        anon = TestClient(main.app)
        self.assertEqual(anon.get('/api/admin/workspace').status_code, 401)
        response = anon.post('/api/login', json={'password': main.PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        old_cookie = anon.cookies.get('atlas_session')
        self.assertEqual(anon.get('/api/admin/workspace').status_code, 200)
        anon.post('/api/logout')
        anon.cookies.set('atlas_session', old_cookie)
        self.assertEqual(anon.get('/api/admin/workspace').status_code, 401)
        anon.close()

    def test_failed_logins_are_persisted_and_rate_limited(self):
        anon = TestClient(main.app)
        for _ in range(10):
            self.assertEqual(anon.post('/api/login', json={'password': 'wrong'}).status_code, 401)
        self.assertEqual(anon.post('/api/login', json={'password': main.PASSWORD}).status_code, 429)
        anon.close()

    def test_hierarchy_email_uniqueness_and_missing_parents(self):
        self.person()
        self.assertEqual(self.client.post('/api/admin/entities', json={'name': 'operations'}).status_code, 409)
        self.assertEqual(self.client.post('/api/admin/teams', json={'name': 'Lost', 'entity_id': 999}).status_code, 409)
        response = self.client.post('/api/admin/employees', json={'name': 'Other', 'email': 'ALEX@example.com', 'role': 'Analyst', 'team_id': 1})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.post('/api/admin/employees', json={'name': 'Other', 'email': 'other@example.com', 'role': 'Analyst', 'team_id': 999}).status_code, 409)

    def test_intake_submission_dashboard_and_persistence(self):
        person, auth = self.person()
        self.assertEqual(self.client.get('/api/intake', headers=auth).json()['assessment']['revision'], 0)
        response = self.client.put('/api/intake', headers=auth, json=self.assessment())
        self.assertEqual(response.status_code, 200, response.text)
        intake = self.client.get('/api/intake', headers=auth).json()['assessment']
        self.assertEqual(intake['tools'], ['ChatGPT', 'Microsoft Excel'])
        self.assertEqual(intake['workflows'][0]['steps'][0]['tool'], 'ChatGPT')
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(workspace['employees'][0]['status'], 'submitted')
        self.assertNotIn('invite_hash', workspace['employees'][0])
        self.assertNotIn('token', workspace['employees'][0])
        opportunity = workspace['opportunities'][0]
        self.assertEqual(opportunity['estimated_hours'], 1.58)
        self.assertEqual(opportunity['weekly_hours'], 5)
        self.assertTrue(opportunity['human_review'])
        self.assertEqual(opportunity['priority'], 'Medium')
        with TestClient(main.app) as other:
            self.assertEqual(other.get('/api/intake', headers=auth).json()['assessment']['revision'], 1)
        read = self.client.get(f"/api/admin/employees/{person['id']}/assessment").json()
        self.assertEqual(read['workflows'][0]['steps'][0]['action'], 'Draft summary')

    def test_partial_drafts_and_incomplete_submission(self):
        _, auth = self.person()
        draft = {'tools': [], 'workflows': [{'name': '', 'steps': [{'action': ''}]}], 'status': 'draft'}
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=draft).status_code, 200)
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(workspace['employees'][0]['status'], 'draft')
        self.assertEqual(workspace['opportunities'], [])
        draft.update(revision=1, status='submitted', tools=['Slack'])
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=draft).status_code, 422)

    def test_optimistic_lock_prevents_lost_updates(self):
        _, auth = self.person()
        payload = self.assessment()
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 200)
        payload['notes'] = 'Stale overwritten copy'
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 409)
        self.assertEqual(self.client.get('/api/intake', headers=auth).json()['assessment']['notes'], '')

    def test_invitation_isolation_rotation_revocation_and_expiry(self):
        first, auth = self.person()
        second, second_auth = self.person('Jamie Smith', 'jamie@example.com')
        anon = TestClient(main.app)
        self.assertEqual(anon.get('/api/admin/workspace', headers=auth).status_code, 401)
        self.assertEqual(anon.get('/api/intake', headers=auth).json()['employee']['id'], first['id'])
        self.assertEqual(anon.get('/api/intake', headers=second_auth).json()['employee']['id'], second['id'])
        payload = self.assessment()
        payload['employee_id'] = second['id']
        self.assertEqual(anon.put('/api/intake', headers=auth, json=payload).status_code, 422)
        fresh = self.client.post(f"/api/admin/employees/{first['id']}/invite").json()
        self.assertEqual(anon.get('/api/intake', headers=auth).status_code, 401)
        fresh_auth = {'Authorization': 'Bearer ' + fresh['token']}
        self.assertEqual(anon.get('/api/intake', headers=fresh_auth).status_code, 200)
        self.client.delete(f"/api/admin/employees/{first['id']}/invite")
        self.assertEqual(anon.get('/api/intake', headers=fresh_auth).status_code, 401)
        with main.database() as db:
            db.execute('UPDATE employees SET invite_expires=0 WHERE id=?', (second['id'],))
        self.assertEqual(anon.get('/api/intake', headers=second_auth).status_code, 401)
        anon.close()

    def test_matching_workflows_group_only_within_team(self):
        first, auth = self.person()
        _, other_auth = self.person('Jamie Smith', 'jamie@example.com')
        payload = self.assessment()
        self.client.put('/api/intake', headers=auth, json=payload)
        payload['workflows'][0]['name'] = ' WEEKLY   REPORTING '
        self.client.put('/api/intake', headers=other_auth, json=payload)
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(len(workspace['opportunities']), 1)
        self.assertEqual(len(workspace['opportunities'][0]['people']), 2)
        self.assertEqual(workspace['opportunities'][0]['estimated_hours'], 3.17)
        entity = self.client.post('/api/admin/entities', json={'name': 'Finance'}).json()['id']
        team = self.client.post('/api/admin/teams', json={'name': 'Accounts', 'entity_id': entity}).json()['id']
        self.client.put(f"/api/admin/employees/{first['id']}", json={'name': 'Alex Morgan', 'email': 'alex@example.com', 'role': 'Analyst', 'team_id': team})
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(len(workspace['opportunities']), 2)
        self.assertEqual(next(p for p in workspace['employees'] if p['id']==first['id'])['entity_name'], 'Finance')

    def test_manual_steps_and_human_review_estimates(self):
        _, auth = self.person()
        payload = self.assessment()
        payload['workflows'][0]['steps'][1]['human_review'] = True
        self.client.put('/api/intake', headers=auth, json=payload)
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(workspace['opportunities'][0]['estimated_hours'], 1.25)
        for step in payload['workflows'][0]['steps']:
            step['support'] = 'manual'
        payload['revision'] = 1
        self.client.put('/api/intake', headers=auth, json=payload)
        self.assertEqual(self.client.get('/api/admin/workspace').json()['opportunities'], [])

    def test_rename_move_and_delete_organization(self):
        person, auth = self.person()
        self.client.put('/api/intake', headers=auth, json=self.assessment())
        workspace = self.client.get('/api/admin/workspace').json()
        entity, team = workspace['entities'][0]['id'], workspace['teams'][0]['id']
        other = self.client.post('/api/admin/entities', json={'name': 'Finance'}).json()['id']
        self.assertEqual(self.client.put(f'/api/admin/entities/{entity}', json={'name': 'finance'}).status_code, 409)
        self.assertEqual(self.client.put(f'/api/admin/entities/{entity}', json={'name': 'Ops'}).status_code, 200)
        self.assertEqual(self.client.put(f'/api/admin/teams/{team}', json={'name': 'X', 'entity_id': 999}).status_code, 409)
        self.assertEqual(self.client.put(f'/api/admin/teams/{team}', json={'name': 'Plans', 'entity_id': other}).status_code, 200)
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual({e['name'] for e in workspace['entities']}, {'Ops', 'Finance'})
        self.assertEqual((workspace['opportunities'][0]['entity_name'], workspace['opportunities'][0]['team_name']), ('Finance', 'Plans'))
        self.assertEqual(self.client.delete(f'/api/admin/entities/{other}').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/admin/teams/{team}').status_code, 409)
        self.assertEqual(self.client.delete(f"/api/admin/employees/{person['id']}").status_code, 200)
        self.assertEqual(self.client.get('/api/intake', headers=auth).status_code, 401)
        with main.database() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM assessments').fetchone())
        for path in (f'employees/{person["id"]}', f'teams/{team}', f'entities/{other}', f'entities/{entity}'):
            self.client.delete(f'/api/admin/{path}')
            self.assertEqual(self.client.delete(f'/api/admin/{path}').status_code, 404)
        self.assertEqual(self.client.put(f'/api/admin/teams/{team}', json={'name': 'Gone', 'entity_id': other}).status_code, 404)
        self.assertEqual(self.client.get('/api/admin/workspace').json()['entities'], [])

    def test_admin_edits_tool_catalog(self):
        _, auth = self.person()
        payload = self.assessment()
        payload['tools'].append('internal portal')
        self.client.put('/api/intake', headers=auth, json=payload)
        ids = {t['name']: t['id'] for t in self.client.get('/api/admin/workspace').json()['catalog']}
        self.assertEqual(self.client.post('/api/admin/tools', json={'name': 'Internal Portal', 'category': 'Internal'}).status_code, 201)
        self.assertEqual(self.client.post('/api/admin/tools', json={'name': 'slack', 'category': 'Chat'}).status_code, 409)
        self.assertEqual(self.client.put(f"/api/admin/tools/{ids['ChatGPT']}", json={'name': 'ChatGPT Enterprise', 'category': 'AI assistants'}).status_code, 200)
        intake = self.client.get('/api/intake', headers=auth).json()
        self.assertEqual(intake['assessment']['tools'], ['ChatGPT Enterprise', 'Microsoft Excel', 'Internal Portal'])
        self.assertEqual(intake['assessment']['workflows'][0]['steps'][0]['tool'], 'ChatGPT Enterprise')
        self.assertIn({'id': ids['ChatGPT'], 'name': 'ChatGPT Enterprise', 'category': 'AI assistants'}, intake['catalog'])
        self.assertIn('ChatGPT Enterprise', self.client.get('/api/admin/workspace').json()['opportunities'][0]['tools'])
        self.assertEqual(self.client.delete(f"/api/admin/tools/{ids['Microsoft Excel']}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/tools/{ids['Microsoft Excel']}").status_code, 404)
        self.assertEqual(self.client.put(f"/api/admin/tools/{ids['Microsoft Excel']}", json={'name': 'X', 'category': 'Y'}).status_code, 404)
        main.initialize()
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertNotIn('Microsoft Excel', [t['name'] for t in workspace['catalog']])
        self.assertIn('Microsoft Excel', workspace['employees'][0]['tools'])
        payload.update(revision=1, tools=['chatgpt enterprise', 'Microsoft Excel'])
        payload['workflows'][0]['steps'][0]['tool'] = 'CHATGPT ENTERPRISE'
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 200)
        saved = self.client.get('/api/intake', headers=auth).json()['assessment']
        self.assertEqual((saved['tools'], saved['workflows'][0]['steps'][0]['tool']), (['ChatGPT Enterprise', 'Microsoft Excel'], 'ChatGPT Enterprise'))

    def test_collaborator_access_is_limited_to_granted_entities(self):
        mine, mine_auth = self.person()
        self.client.put('/api/intake', headers=mine_auth, json=self.assessment())
        ops = self.client.get('/api/admin/workspace').json()['entities'][0]['id']
        planning = self.client.get('/api/admin/workspace').json()['teams'][0]['id']
        finance = self.client.post('/api/admin/entities', json={'name': 'Finance'}).json()['id']
        accounts = self.client.post('/api/admin/teams', json={'name': 'Accounts', 'entity_id': finance}).json()['id']
        other = self.client.post('/api/admin/employees', json={'name': 'Sam Lee', 'email': 'sam@example.com', 'role': 'Analyst', 'team_id': accounts}).json()
        self.client.put('/api/intake', headers={'Authorization': 'Bearer ' + other['token']}, json=self.assessment())
        invite = self.client.post('/api/admin/collaborators', json={'name': 'Kim Park', 'email': 'kim@example.com', 'entity_ids': [ops, ops]})
        self.assertEqual(invite.status_code, 201, invite.text)
        self.assertEqual(self.client.post('/api/admin/collaborators', json={'name': 'X', 'email': 'x@example.com', 'entity_ids': [999]}).status_code, 409)
        guest = TestClient(main.app)
        self.assertEqual(guest.post('/api/join', json={'token': 'wrong'}).status_code, 401)
        self.assertEqual(guest.post('/api/join', json={'token': invite.json()['token']}).status_code, 200)
        workspace = guest.get('/api/admin/workspace').json()
        self.assertEqual(workspace['viewer'], {'name': 'Kim Park', 'entity_ids': [ops]})
        self.assertEqual(([e['id'] for e in workspace['entities']], [t['id'] for t in workspace['teams']]), ([ops], [planning]))
        self.assertEqual([p['id'] for p in workspace['employees']], [mine['id']])
        self.assertEqual({o['entity_id'] for o in workspace['opportunities']}, {ops})
        self.assertEqual(workspace['collaborators'], [])
        for method, path, body in [('post', '/api/admin/entities', {'name': 'New'}), ('put', f'/api/admin/entities/{ops}', {'name': 'Mine'}),
                                   ('delete', f'/api/admin/entities/{ops}', None), ('post', '/api/admin/tools', {'name': 'T', 'category': 'C'}),
                                   ('post', '/api/admin/collaborators', {'name': 'Y', 'email': 'y@example.com', 'entity_ids': [ops]})]:
            self.assertEqual(guest.request(method, path, json=body).status_code, 403, path)
        for method, path, body in [('post', '/api/admin/teams', {'name': 'Audit', 'entity_id': finance}),
                                   ('put', f'/api/admin/teams/{accounts}', {'name': 'A', 'entity_id': finance}),
                                   ('put', f'/api/admin/teams/{planning}', {'name': 'Planning', 'entity_id': finance}),
                                   ('delete', f'/api/admin/teams/{accounts}', None),
                                   ('post', '/api/admin/employees', {'name': 'Z', 'email': 'z@example.com', 'role': 'R', 'team_id': accounts}),
                                   ('put', f"/api/admin/employees/{mine['id']}", {'name': 'Alex Morgan', 'email': 'alex@example.com', 'role': 'R', 'team_id': accounts}),
                                   ('put', f"/api/admin/employees/{other['id']}", {'name': 'Sam Lee', 'email': 'sam@example.com', 'role': 'R', 'team_id': planning}),
                                   ('delete', f"/api/admin/employees/{other['id']}", None), ('post', f"/api/admin/employees/{other['id']}/invite", None),
                                   ('delete', f"/api/admin/employees/{other['id']}/invite", None), ('get', f"/api/admin/employees/{other['id']}/assessment", None)]:
            self.assertEqual(guest.request(method, path, json=body).status_code, 404, (method, path))
        self.assertEqual(guest.get(f"/api/admin/employees/{mine['id']}/assessment").status_code, 200)
        self.assertEqual(guest.post('/api/admin/teams', json={'name': 'Field', 'entity_id': ops}).status_code, 201)
        self.assertEqual(guest.post(f"/api/admin/employees/{mine['id']}/invite").status_code, 200)
        collaborator = self.client.get('/api/admin/workspace').json()['collaborators'][0]
        self.assertEqual(collaborator['entity_ids'], [ops])
        self.client.put(f"/api/admin/collaborators/{collaborator['id']}", json={'name': 'Kim Park', 'email': 'kim@example.com', 'entity_ids': [finance]})
        self.assertEqual([e['id'] for e in guest.get('/api/admin/workspace').json()['entities']], [finance])
        self.client.post(f"/api/admin/collaborators/{collaborator['id']}/invite")
        self.assertEqual(guest.post('/api/join', json={'token': invite.json()['token']}).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/admin/collaborators/{collaborator['id']}").status_code, 200)
        self.assertEqual(guest.get('/api/admin/workspace').status_code, 401)
        guest.close()

    def test_sessions_from_before_collaborators_keep_working(self):
        main.DB_PATH = Path(self.directory.name) / 'old.sqlite3'
        with main.database() as db:
            db.execute('CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)')
            db.execute('INSERT INTO sessions VALUES (?,?)', (main.digest('old-token'), 2**40))
        main.initialize()
        old = TestClient(main.app, cookies={'atlas_session': 'old-token'})
        self.assertEqual(old.get('/api/admin/workspace').json()['viewer'], None)
        old.close()

    def test_trust_boundary_validation(self):
        _, auth = self.person()
        payload = self.assessment()
        payload['workflows'][0]['steps'][0]['tool'] = 'Unselected system'
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 422)
        payload = self.assessment()
        payload['workflows'][0]['steps'][0]['minutes'] = -1
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 422)
        self.assertEqual(self.client.post('/api/admin/entities', json={'name': ' '}).status_code, 422)
        self.assertEqual(self.client.post('/api/admin/entities', json={'name':'Evil'}, headers={'Origin':'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/admin/entities', content=b'x'*1_000_001).status_code, 413)

    def test_optional_sample_workspace_is_atomic_and_repeat_safe(self):
        from app.seed_demo import seed
        seed()
        workspace = self.client.get('/api/admin/workspace').json()
        self.assertEqual(len(workspace['entities']), 3)
        self.assertEqual(len(workspace['teams']), 6)
        self.assertEqual(len(workspace['employees']), 8)
        self.assertEqual(len(workspace['opportunities']), 5)
        with self.assertRaises(SystemExit):
            seed()
        self.assertEqual(len(self.client.get('/api/admin/workspace').json()['employees']), 8)

    def test_frequency_units_round_trip_and_legacy_values(self):
        _, auth = self.person()
        for revision, (unit, count, weekly) in enumerate([
            ('day', 1, 5), ('week', 2, 2), ('month', 1, 12 / 52), ('year', 1, 1 / 52),
        ]):
            payload = self.assessment()
            payload['revision'] = revision
            payload['workflows'][0].update(frequency_count=count, frequency_unit=unit)
            response = self.client.put('/api/intake', headers=auth, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            workflow = self.client.get('/api/intake', headers=auth).json()['assessment']['workflows'][0]
            self.assertEqual(workflow['frequency_count'], count)
            self.assertEqual(workflow['frequency_unit'], unit)
            self.assertAlmostEqual(workflow['runs_per_week'], weekly)
        payload = self.assessment()
        payload['revision'] = 4
        payload['workflows'][0]['runs_per_week'] = 0.25
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 200)
        workflow = self.client.get('/api/intake', headers=auth).json()['assessment']['workflows'][0]
        self.assertEqual(workflow['runs_per_week'], 0.25)
        self.assertIsNone(workflow['frequency_count'])
        self.assertIsNone(workflow['frequency_unit'])

    def test_frequency_pair_and_normalized_limits(self):
        _, auth = self.person()
        for fields in [
            {'frequency_count': 1}, {'frequency_unit': 'month'},
            {'frequency_count': 0, 'frequency_unit': 'week'},
            {'frequency_count': 201, 'frequency_unit': 'day'},
            {'frequency_count': 1, 'frequency_unit': 'invalid'},
        ]:
            payload = self.assessment()
            payload['workflows'][0].update(fields)
            self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 422)
        payload = self.assessment()
        payload['workflows'][0].update(frequency_count=2, frequency_unit='week', runs_per_week=999)
        self.assertEqual(self.client.put('/api/intake', headers=auth, json=payload).status_code, 200)
        workflow = self.client.get('/api/intake', headers=auth).json()['assessment']['workflows'][0]
        self.assertEqual(workflow['runs_per_week'], 2)

    def test_static_health_and_security_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Agent Atlas', response.text)
        self.assertIn("script-src 'self'", response.headers['content-security-policy'])
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertEqual(self.client.get('/intake').status_code, 200)
        self.assertEqual(self.client.get('/api/health').json(), {'status':'ok'})


if __name__ == '__main__':
    unittest.main()
