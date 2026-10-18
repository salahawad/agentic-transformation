"""Real-browser end-to-end checks against an isolated temporary workspace.
Run with a Python environment that has Playwright and Chromium installed.
"""
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
ARTIFACTS.mkdir(exist_ok=True)
PASSWORD = 'browser-test-password-12345'
BASE = 'http://127.0.0.1:18181'


def run():
    with tempfile.TemporaryDirectory() as directory:
        env = {**os.environ, 'ADMIN_PASSWORD': PASSWORD, 'DATABASE_PATH': str(Path(directory)/'test.sqlite3')}
        with (ARTIFACTS/'browser-server.log').open('w') as log:
            server = subprocess.Popen([str(ROOT/'.venv/bin/python'), '-m', 'uvicorn', 'app.main:app', '--port', '18181', '--no-access-log'], cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    try:
                        urllib.request.urlopen(BASE+'/api/health', timeout=1).close()
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Test server exited; see artifacts/browser-server.log')
                        time.sleep(.1)
                else:
                    raise RuntimeError('Test server did not become ready')
                browser_checks()
            finally:
                server.terminate()
                server.wait(timeout=10)


def browser_checks():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        admin = browser.new_context(viewport={'width':1440, 'height':1100})
        page = admin.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE)
        page.get_by_label('Workspace password').fill(PASSWORD)
        page.get_by_role('button', name='Open workspace').click()
        expect(page.get_by_role('heading', name='Transformation overview')).to_be_visible()
        page.screenshot(path=str(ARTIFACTS/'dashboard-empty.png'), full_page=True, animations='disabled')
        page.get_by_role('link', name='Organization', exact=True).click()
        page.get_by_role('button', name='Add entity', exact=True).click()
        page.get_by_label('Entity name', exact=True).fill('Operations')
        page.get_by_role('button', name='Create entity').click()
        page.get_by_role('button', name='Add team', exact=True).click()
        page.get_by_label('Team name', exact=True).fill('Business Operations')
        page.get_by_role('button', name='Create team').click()
        page.get_by_role('link', name='People & assessments').click()
        page.locator('.skip-link').focus()
        page.keyboard.press('Enter')
        assert page.evaluate('document.activeElement.id') == 'content'
        assert page.url.endswith('#people'), 'Skipping to content must preserve the current page'
        page.get_by_role('button', name='Invite employee', exact=True).first.click()
        page.get_by_label('Full name').fill('Alex Morgan')
        page.get_by_label('Work email').fill('alex@example.com')
        page.get_by_label('Role / job title').fill('Operations analyst')
        page.get_by_role('button', name='Create invitation').click()
        link = page.get_by_label('Employee assessment link').input_value()
        page.get_by_role('button', name='Done', exact=True).click()

        employee = browser.new_context(viewport={'width':1280,'height':1000})
        form = employee.new_page()
        form.on('pageerror', lambda e: errors.append(str(e)))
        form.goto(link)
        expect(form.get_by_role('heading', name='Help shape a better workday, Alex.')).to_be_visible()
        assert '#' not in form.url, 'Secret token must be removed from visible URL'
        form.get_by_label('ChatGPT', exact=True).check()
        form.get_by_label('Custom digital tool').fill('Internal portal')
        form.get_by_label('Custom digital tool').press('Enter')
        expect(form.get_by_label('Internal portal', exact=True)).to_be_checked()
        expect(form.get_by_role('heading', name='Which tools are part of your workday?')).to_be_visible()
        form.get_by_role('button', name='Save & continue').click()
        form.get_by_role('button', name='Describe your first workflow').click()
        form.get_by_label('Workflow name', exact=True).fill('Weekly reporting')
        form.get_by_label('Number of times', exact=True).fill('1')
        form.get_by_label('Frequency period', exact=True).select_option('month')
        assert abs(form.evaluate('state.intake.assessment.workflows[0].runs_per_week') - 12/52) < 1e-10
        form.get_by_label('Frequency period', exact=True).select_option('day')
        assert form.evaluate('state.intake.assessment.workflows[0].runs_per_week') == 5
        form.get_by_label('Frequency period', exact=True).select_option('week')
        form.get_by_label('Number of times', exact=True).fill('5')
        form.get_by_label('What starts this workflow?').fill('Every weekday at 9am')
        form.get_by_label('What is the end result?').fill('Reviewed report shared')
        form.get_by_label('What do you do?', exact=True).fill('Draft a summary')
        form.get_by_label('Tool used', exact=True).select_option(label='ChatGPT')
        form.get_by_label('Minutes / run', exact=True).fill('30')
        form.get_by_label('How could an agent help?', exact=True).select_option('assist')
        form.get_by_role('button', name='Add a step', exact=True).click()
        form.get_by_label('What do you do?', exact=True).nth(1).fill('Approve the report')
        form.get_by_label('Tool used', exact=True).nth(1).select_option('Internal portal')
        form.get_by_label('Minutes / run', exact=True).nth(1).fill('10')
        form.get_by_label('How could an agent help?', exact=True).nth(1).select_option('manual')
        form.get_by_label('A person must review or approve this step').nth(1).check()
        form.get_by_role('button', name='Move step 2 up', exact=True).click()
        expect(form.get_by_label('What do you do?', exact=True).first).to_have_value('Approve the report')
        form.get_by_role('button', name='Move step 1 down', exact=True).click()
        expect(form.get_by_label('What do you do?', exact=True).first).to_have_value('Draft a summary')
        form.get_by_label('Where does this workflow get frustrating? (optional)').fill('Copying data takes time.')

        # Both representations edit the same assessment without UI-only payload fields.
        workflow = form.locator('.workflow-editor').first
        expect(workflow.get_by_role('button', name='Text', exact=True)).to_have_attribute('aria-pressed', 'true')
        before_switch = form.evaluate('JSON.stringify(state.intake.assessment)')
        workflow.get_by_role('button', name='Diagram', exact=True).click()
        expect(workflow.locator('.diagram-node')).to_have_count(2)
        expect(form.get_by_label('What do you do?', exact=True)).to_have_count(1)
        assert form.evaluate('JSON.stringify(state.intake.assessment)') == before_switch
        workflow.locator('.diagram-node').first.click()
        form.get_by_label('What do you do?', exact=True).fill('Review <img src=x onerror="alert(1)">')
        expect(workflow.locator('[data-node-action]').first).to_have_text('Review <img src=x onerror="alert(1)">')
        expect(workflow.locator('.workflow-diagram img')).to_have_count(0)
        form.get_by_label('What do you do?', exact=True).fill('Draft a summary')
        form.get_by_label('Minutes / run', exact=True).fill('35')
        expect(workflow.locator('[data-node-minutes]').first).to_have_text('35 min')
        form.get_by_label('Minutes / run', exact=True).fill('30')
        form.get_by_label('How could an agent help?', exact=True).select_option('automate')
        expect(workflow.locator('[data-node-support]').first).to_have_text('Automated')
        form.get_by_label('A person must review or approve this step').check()
        expect(workflow.locator('[data-node-review]').first).to_be_visible()
        form.get_by_label('How could an agent help?', exact=True).select_option('assist')
        form.get_by_label('A person must review or approve this step').uncheck()
        workflow.locator('.diagram-node').nth(1).focus()
        workflow.locator('.diagram-node').nth(1).press('Enter')
        expect(form.get_by_label('What do you do?', exact=True)).to_have_value('Approve the report')
        form.get_by_label('What do you do?', exact=True).fill('Approve and publish the report')
        workflow.get_by_role('button', name='Text', exact=True).click()
        expect(form.get_by_label('What do you do?', exact=True).nth(1)).to_have_value('Approve and publish the report')
        expect(form.get_by_label('A person must review or approve this step').nth(1)).to_be_checked()
        form.get_by_label('What do you do?', exact=True).nth(1).fill('Approve the report')
        # Continue must reveal an unfinished node even when another step is selected.
        form.get_by_label('What do you do?', exact=True).first.fill(' ')
        workflow.get_by_role('button', name='Diagram', exact=True).click()
        expect(workflow.locator('.diagram-node').nth(1)).to_have_attribute('aria-pressed', 'true')
        form.get_by_role('button', name='Save & continue').click()
        expect(workflow.locator('.diagram-node').first).to_have_attribute('aria-pressed', 'true')
        expect(form.get_by_label('What do you do?', exact=True)).to_be_focused()
        assert form.get_by_label('What do you do?', exact=True).evaluate('(input)=>!input.validity.valid')
        form.get_by_label('What do you do?', exact=True).fill('Draft a summary')
        form.get_by_role('button', name='Add a diagram step', exact=True).click()
        expect(workflow.locator('.diagram-node')).to_have_count(3)
        expect(workflow.locator('[data-node-support]').last).to_have_text('Needs description')
        expect(workflow.locator('.diagram-node-meta').last).to_be_hidden()
        expect(workflow.locator('[data-workflow-completion]')).to_have_text('2 of 3 described')
        expect(form.get_by_label('What do you do?', exact=True)).to_be_focused()
        form.get_by_label('What do you do?', exact=True).fill('Send the report')
        expect(workflow.locator('[data-workflow-completion]')).to_have_text('3 of 3 described')
        form.get_by_role('button', name='Move step 3 up', exact=True).click()
        expect(form.get_by_label('What do you do?', exact=True)).to_have_value('Send the report')
        expect(workflow.locator('.diagram-node').nth(1)).to_have_attribute('aria-pressed', 'true')
        form.get_by_role('button', name='Remove step 2', exact=True).click()
        expect(workflow.locator('.diagram-node')).to_have_count(2)
        expect(form.get_by_label('What do you do?', exact=True)).to_have_value('Approve the report')
        # Long diagrams keep the selected node visible after structural changes.
        for number in range(3, 6):
            form.get_by_role('button', name='Add a diagram step', exact=True).click()
            form.get_by_label('What do you do?', exact=True).fill(f'Temporary step {number}')
            assert workflow.locator('.workflow-diagram').evaluate("""diagram => {
                const selected = diagram.querySelector('.diagram-node[aria-pressed="true"]').getBoundingClientRect();
                const bounds = diagram.getBoundingClientRect();
                return selected.left >= bounds.left && selected.right <= bounds.right && selected.top >= bounds.top && selected.bottom <= bounds.bottom;
            }"""), 'Adding a step must keep its node in view'
        form.screenshot(path=str(ARTIFACTS/'workflow-ux-five-steps.png'),full_page=True, animations='disabled')
        assert workflow.locator('.workflow-diagram').evaluate('(diagram)=>diagram.scrollWidth <= diagram.clientWidth + 1'), 'Diagram must not require sideways scrolling'
        scroll_before = workflow.locator('.workflow-diagram').evaluate('(diagram)=>diagram.scrollTop')
        workflow.locator('.diagram-node').last.click()
        assert abs(workflow.locator('.workflow-diagram').evaluate('(diagram)=>diagram.scrollTop') - scroll_before) < 2
        workflow.locator('.diagram-node').last.press('Home')
        expect(workflow.locator('.diagram-node').first).to_have_attribute('aria-pressed', 'true')
        workflow.locator('.diagram-node').first.press('End')
        expect(workflow.locator('.diagram-node').last).to_have_attribute('aria-pressed', 'true')
        for number in range(5, 2, -1):
            form.get_by_role('button', name=f'Remove step {number}', exact=True).click()
        expect(workflow.locator('.diagram-node')).to_have_count(2)
        # Other workflows retain an independent view and a one-step minimum.
        form.get_by_role('button', name='Add another workflow', exact=True).click()
        second_workflow = form.locator('.workflow-editor').nth(1)
        expect(second_workflow.get_by_role('button', name='Text', exact=True)).to_have_attribute('aria-pressed', 'true')
        expect(workflow.get_by_role('button', name='Diagram', exact=True)).to_have_attribute('aria-pressed', 'true')
        second_workflow.get_by_role('button', name='Diagram', exact=True).click()
        expect(second_workflow.get_by_role('button', name='Remove step 1', exact=True)).to_be_disabled()
        form.once('dialog', lambda dialog: dialog.accept())
        form.get_by_role('button', name='Remove workflow 2', exact=True).click()
        expect(form.locator('.workflow-editor')).to_have_count(1)
        form.screenshot(path=str(ARTIFACTS/'employee-workflow-diagram.png'), full_page=True, animations='disabled')

        locked = []
        def check_save_lock(route):
            if route.request.method == 'PUT':
                locked.append(form.locator('#intake-form').get_attribute('inert') is not None)
            route.continue_()
        form.route('**/api/intake', check_save_lock)
        form.get_by_role('button', name='Save draft', exact=True).click()
        expect(form.locator('#toast')).to_contain_text('Your draft is saved')
        assert locked and all(locked), 'Intake must be locked while saving to prevent lost edits'
        expect(form.locator('#save-status')).to_contain_text('All changes saved')
        expect(workflow.locator('[data-workflow-saved]')).to_have_text('Saved')
        saved_assessment = form.evaluate('JSON.stringify(state.intake.assessment)')
        workflow.get_by_role('button', name='Text', exact=True).click()
        workflow.get_by_role('button', name='Diagram', exact=True).click()
        workflow.locator('.diagram-node').first.click()
        assert not form.evaluate('unsavedParts().length'), 'Changing views must not mark answers as modified'
        assert form.evaluate('JSON.stringify(state.intake.assessment)') == saved_assessment
        # Saving one workflow leaves another workflow's edits unsaved and says so.
        form.get_by_role('button', name='Add another workflow', exact=True).click()
        second_workflow = form.locator('.workflow-editor').nth(1)
        expect(second_workflow.locator('[data-workflow-saved]')).to_have_text('Not saved yet')
        second_workflow.get_by_label('Workflow name', exact=True).fill('Invoice follow-up')
        second_workflow.get_by_label('What do you do?', exact=True).fill('Chase overdue invoices')
        workflow.get_by_label('What do you do?', exact=True).fill('Draft a short summary')
        expect(workflow.locator('[data-workflow-saved]')).to_have_text('Unsaved changes')
        expect(form.locator('#save-status')).to_have_text('Not saved yet: workflow 1, workflow 2')
        second_workflow.get_by_label('Number of times', exact=True).fill('')
        second_workflow.get_by_role('button', name='Save workflow 2', exact=True).click()
        assert second_workflow.get_by_label('Number of times', exact=True).evaluate('(input)=>!input.validity.valid')
        expect(second_workflow.locator('[data-workflow-saved]')).to_have_text('Not saved yet')
        second_workflow.get_by_label('Number of times', exact=True).fill('2')
        second_workflow.get_by_role('button', name='Save workflow 2', exact=True).click()
        expect(form.locator('#toast')).to_contain_text('Invoice follow-up is saved')
        expect(second_workflow.locator('[data-workflow-saved]')).to_have_text('Saved')
        expect(workflow.locator('[data-workflow-saved]')).to_have_text('Unsaved changes')
        expect(form.locator('#save-status')).to_have_text('Not saved yet: workflow 1')
        stored = "api('/api/intake').then((d)=>d.assessment.workflows.map((w)=>w.steps[0].action))"
        assert form.evaluate(stored) == ['Draft a summary', 'Chase overdue invoices'], 'Only workflow 2 may be saved'
        # Undoing an edit returns the workflow to its saved state.
        workflow.get_by_label('What do you do?', exact=True).fill('Draft a summary')
        expect(workflow.locator('[data-workflow-saved]')).to_have_text('Saved')
        expect(form.locator('#save-status')).to_contain_text('All changes saved')
        # Removing a saved workflow deletes it from the server immediately.
        form.once('dialog', lambda dialog: dialog.accept())
        form.get_by_role('button', name='Remove workflow 2', exact=True).click()
        expect(form.locator('.workflow-editor')).to_have_count(1)
        expect(form.locator('#save-status')).to_contain_text('All changes saved')
        assert form.evaluate(stored) == ['Draft a summary']
        form.reload()
        form.get_by_role('button', name='Save & continue').click()
        expect(form.get_by_label('Workflow name', exact=True)).to_have_value('Weekly reporting')
        expect(form.get_by_label('Number of times', exact=True)).to_have_value('5')
        expect(form.get_by_label('Frequency period', exact=True)).to_have_value('week')
        expect(form.get_by_label('What do you do?', exact=True).nth(1)).to_have_value('Approve the report')
        form.screenshot(path=str(ARTIFACTS/'employee-workflow.png'), full_page=True, animations='disabled')
        form.get_by_role('button', name='Save & continue').click()
        form.get_by_label('Anything else you’d like your team to know? (optional)').fill('Start with a reviewed pilot.')
        form.get_by_role('button', name='Share my assessment').click()
        expect(form.get_by_role('heading', name='Thanks for sharing your work, Alex.')).to_be_visible()
        form.reload()
        expect(form.get_by_role('heading', name='Thanks for sharing your work, Alex.')).to_be_visible()

        page.get_by_role('link', name='Overview', exact=True).click()
        expect(page.get_by_role('heading', name='Weekly reporting assistant', exact=True)).to_be_visible()
        expect(page.get_by_text('1.3h', exact=False).first).to_be_visible()
        page.get_by_role('button', name='Explore opportunity').click()
        expect(page.get_by_role('heading', name='Supporting workflows')).to_be_visible()
        expect(page.get_by_text('Human review is part of the source workflow.', exact=False)).to_be_visible()
        page.get_by_role('button', name='Done', exact=True).click()
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(ARTIFACTS/'dashboard-desktop.png'), full_page=True, animations='disabled')
        page.get_by_role('link', name='Digital tools', exact=True).click()
        expect(page.get_by_text('Internal portal', exact=True)).to_be_visible()
        page.on('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Add Internal portal to the tools list', exact=True).click()
        page.get_by_label('Category', exact=True).fill('Internal systems')
        page.locator('#modal').get_by_role('button', name='Add tool').click()
        internal = page.locator('.panel').filter(has=page.get_by_role('heading', name='Internal systems', exact=True))
        expect(internal).to_contain_text('Internal portal')
        expect(internal).to_contain_text('1 person')
        page.get_by_role('button', name='Edit ChatGPT', exact=True).click()
        page.get_by_label('Tool name', exact=True).fill('ChatGPT Enterprise')
        page.get_by_role('button', name='Save tool').click()
        expect(page.locator('.catalog-tool').filter(has_text='ChatGPT Enterprise')).to_contain_text('1 person')
        page.get_by_role('button', name='Delete Zoom', exact=True).click()
        expect(page.get_by_text('Zoom', exact=True)).to_have_count(0)
        page.get_by_role('link', name='Agent opportunities', exact=True).click()
        with page.expect_download() as download:
            page.get_by_role('button', name='Export opportunities').click()
        assert download.value.suggested_filename.endswith('.csv')
        page.get_by_role('link', name='Organization', exact=True).click()
        page.get_by_role('button', name='Add entity', exact=True).click()
        page.get_by_label('Entity name', exact=True).fill('Commercial')
        page.get_by_role('button', name='Create entity').click()
        page.locator('.panel').filter(has=page.get_by_role('heading', name='Commercial', exact=True)).get_by_role('button', name='Add team', exact=True).click()
        page.get_by_label('Team name', exact=True).fill('Sales')
        page.get_by_role('button', name='Create team').click()
        page.get_by_role('link', name='People & assessments').click()
        page.get_by_role('button', name='Edit Alex Morgan', exact=True).click()
        page.get_by_label('Entity', exact=True).select_option(label='Commercial')
        expect(page.get_by_label('Team', exact=True)).to_contain_text('Sales')

        page.get_by_label('Role / job title').fill('Senior operations analyst')
        page.get_by_role('button', name='Save employee').click()
        expect(page.get_by_text('Senior operations analyst', exact=True)).to_be_visible()
        expect(page.get_by_role('cell').filter(has_text='Commercial')).to_be_visible()
        page.get_by_label('Filter by entity').select_option(label='Operations')
        expect(page.get_by_role('heading', name='Bring your people into the picture')).to_be_visible()
        page.get_by_label('Filter by entity').select_option(label='Commercial')
        page.get_by_label('Search employees').fill('no match')
        expect(page.get_by_role('heading', name='Bring your people into the picture')).to_be_visible()
        page.get_by_label('Search employees').fill('alex')
        expect(page.get_by_text('Alex Morgan', exact=True)).to_be_visible()
        page.get_by_role('button', name='View assessment for Alex Morgan', exact=True).click()
        expect(page.get_by_role('heading', name='Alex Morgan’s workflows')).to_be_visible()
        page.get_by_role('button', name='Close', exact=True).click()

        page.get_by_role('link', name='Organization', exact=True).click()
        page.get_by_role('button', name='Rename Operations', exact=True).click()
        page.get_by_label('Entity name', exact=True).fill('Operations Hub')
        page.get_by_role('button', name='Save entity').click()
        expect(page.get_by_role('heading', name='Operations Hub', exact=True)).to_be_visible()
        page.get_by_role('button', name='Delete Commercial', exact=True).click()
        expect(page.locator('#toast')).to_contain_text('teams first')
        page.get_by_role('button', name='Edit Sales', exact=True).click()
        page.get_by_label('Team name', exact=True).fill('Field Sales')
        page.get_by_label('Entity', exact=True).select_option(label='Operations Hub')
        page.get_by_role('button', name='Save team').click()
        expect(page.locator('.panel').filter(has=page.get_by_role('heading', name='Operations Hub', exact=True))).to_contain_text('Field Sales')
        page.get_by_role('button', name='Delete Commercial', exact=True).click()
        expect(page.get_by_role('heading', name='Commercial', exact=True)).to_have_count(0)
        page.get_by_role('button', name='Delete Business Operations', exact=True).click()
        expect(page.get_by_text('Business Operations', exact=True)).to_have_count(0)
        page.get_by_role('link', name='Overview', exact=True).click()
        expect(page.get_by_text('Operations Hub / Field Sales', exact=False).first).to_be_visible()

        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button', name='Toggle navigation').click()
        page.get_by_role('link', name='Overview', exact=True).click()
        page.screenshot(path=str(ARTIFACTS/'dashboard-mobile.png'),full_page=True, animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Dashboard overflowed mobile width'
        page.get_by_role('button', name='Toggle navigation').click()
        page.get_by_role('link', name='Organization', exact=True).click()
        expect(page.get_by_role('heading', name='Your organization', exact=True)).to_be_visible()
        page.screenshot(path=str(ARTIFACTS/'organization-mobile.png'),full_page=True, animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Organization overflowed mobile width'
        page.get_by_role('button', name='Toggle navigation').click()
        page.get_by_role('link', name='Digital tools', exact=True).click()
        expect(page.get_by_role('heading', name='The tools behind the work', exact=True)).to_be_visible()
        page.screenshot(path=str(ARTIFACTS/'tools-mobile.png'),full_page=True, animations='disabled')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Digital tools overflowed mobile width'
        form.set_viewport_size({'width':390,'height':844})
        form.get_by_role('button', name='Review or update my answers').click()
        form.get_by_role('button', name='Edit', exact=False).nth(1).click()
        form.screenshot(path=str(ARTIFACTS/'intake-mobile.png'),full_page=True, animations='disabled')
        assert form.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Intake overflowed mobile width'
        form.get_by_role('button', name='Diagram', exact=True).click()
        expect(form.locator('.diagram-node')).to_have_count(2)
        form.locator('.diagram-node').nth(1).click()
        expect(form.get_by_label('What do you do?', exact=True)).to_have_value('Approve the report')
        form.screenshot(path=str(ARTIFACTS/'intake-diagram-mobile.png'),full_page=True, animations='disabled')
        assert form.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Diagram overflowed mobile width'
        assert not errors, errors
        print('PASS: browser admin setup, invitations, custom tool Enter, workflow ordering, draft reload, save locking, Text/Diagram editing, hidden-step validation, compact diagrams, frequency units, keyboard navigation, diagram add/reorder/remove, submission, suggestions, CSV export, editing, organization rename/move/delete, tool list editing, search, and responsive layouts; no JavaScript errors.')
        employee.close(); admin.close(); browser.close()


if __name__ == '__main__':
    run()
