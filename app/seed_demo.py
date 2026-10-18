"""Optional fictional workspace. Refuses to modify an existing organization."""
import json
import time
from app.main import database


def seed():
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT COUNT(*) FROM entities').fetchone()[0]:
            raise SystemExit('Sample data requires an empty workspace. Existing data was preserved.')
        entities = {}
        teams = {}
        for entity, names in {'Operations': ['Business Operations', 'Customer Experience'], 'Commercial': ['Sales', 'Marketing'], 'People & Finance': ['People', 'Finance']}.items():
            entities[entity] = db.execute('INSERT INTO entities(name) VALUES (?)', (entity,)).lastrowid
            for name in names:
                teams[name] = db.execute('INSERT INTO teams(entity_id,name) VALUES (?,?)', (entities[entity], name)).lastrowid
        records = [
            ('Alex Morgan', 'Operations manager', 'Business Operations', ['Microsoft Excel','Outlook','SharePoint'], 'Weekly performance reporting', 5, [('Collect performance data','Microsoft Excel',25,'automate'),('Draft a weekly summary','Outlook',20,'assist'),('Review and share the report','SharePoint',10,'manual')]),
            ('Jamie Chen', 'Operations analyst', 'Business Operations', ['Microsoft Excel','Outlook','SharePoint'], 'Weekly performance reporting', 5, [('Combine team updates','Microsoft Excel',20,'automate'),('Draft a weekly summary','Outlook',25,'assist'),('Review findings','SharePoint',10,'manual')]),
            ('Sam Rivera', 'Customer success lead', 'Customer Experience', ['ServiceNow','Slack','Notion'], 'Customer request triage', 20, [('Classify incoming requests','ServiceNow',8,'automate'),('Find relevant knowledge','Notion',5,'assist'),('Draft a response','Slack',7,'assist')]),
            ('Taylor Brooks', 'Account executive', 'Sales', ['Salesforce','Outlook','Microsoft Teams'], 'Sales meeting follow-up', 12, [('Summarize meeting notes','Microsoft Teams',10,'assist'),('Update opportunity records','Salesforce',8,'automate'),('Draft a customer follow-up','Outlook',12,'assist')]),
            ('Jordan Ellis', 'People partner', 'People', ['Workday','Notion','Slack'], 'New employee onboarding', 2, [('Create an onboarding checklist','Notion',20,'automate'),('Prepare a welcome message','Slack',10,'assist'),('Review employee information','Workday',15,'manual')]),
            ('Casey Patel', 'Finance analyst', 'Finance', ['SAP','Microsoft Excel','Outlook'], 'Invoice reconciliation', 8, [('Match invoices to purchase orders','SAP',15,'assist'),('Flag discrepancies','Microsoft Excel',10,'automate'),('Approve payment','Outlook',10,'manual')]),
            ('Robin Kim', 'Marketing specialist', 'Marketing', ['HubSpot','Canva','Google Sheets'], None, 1, []),
            ('Drew Lewis', 'Support specialist', 'Customer Experience', [], None, 1, []),
        ]
        for index,(name,role,team,tools,workflow,frequency,steps) in enumerate(records):
            email = name.lower().replace(' ','.')+'@example.com'
            person = db.execute('INSERT INTO employees(name,email,role,team_id,created_at) VALUES (?,?,?,?,?)', (name,email,role,teams[team],int(time.time()))).lastrowid
            if not tools:
                continue
            workflows = [] if not workflow else [{
                'name':workflow,'trigger':'A regular team task begins','outcome':'Reviewed work shared with the team',
                'runs_per_week':frequency,'pain_points':'Repetitive manual work across multiple tools.',
                'steps':[{'action':a,'tool':t,'minutes':m,'support':s,'human_review':s=='manual','details':''} for a,t,m,s in steps],
            }]
            payload = {'tools':tools,'workflows':workflows,'notes':'Fictional sample assessment for exploring Agent Atlas.'}
            db.execute('INSERT INTO assessments VALUES (?,?,?,?,?)', (person,json.dumps(payload),'submitted' if workflow else 'draft',1,int(time.time())))
    print('Created 3 fictional entities, 6 teams, and 8 employees. No messages were sent. Create an invitation in People to try an assessment.')


if __name__ == '__main__':
    seed()
