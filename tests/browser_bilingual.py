"""Bilingual browser regressions; run with the same environment as browser_smoke.py."""
import csv
import io

from playwright.sync_api import expect, sync_playwright

from browser_smoke import ARTIFACTS, BASE, PASSWORD, run


def switch(page, language):
    page.locator('#language-select').select_option(language)
    expect(page.locator('html')).to_have_attribute('lang', language)
    assert page.evaluate('localStorage.getItem("atlas_language")') == language


def intake_snapshot(page):
    return page.evaluate('''JSON.stringify({
        assessment: state.intake.assessment, stage: state.stage,
        views: state.intake.assessment.workflows.map(workflowView),
        saved: state.intake.assessment.workflows.map(workflowSaveState),
        savedRest: state.savedRest, savedAt: state.savedAt
    })''')


def browser_checks():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        admin = browser.new_context(locale='fr-FR', viewport={'width': 1440, 'height': 1100})
        page = admin.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        expect(page.get_by_role('heading', name='Bon retour.', exact=True)).to_be_visible()
        expect(page.locator('html')).to_have_attribute('lang', 'fr')
        page.locator('#password').fill(PASSWORD)
        switch(page, 'en')
        expect(page.locator('#password')).to_have_value(PASSWORD)
        page.reload()
        expect(page.get_by_role('heading', name='Welcome back.', exact=True)).to_be_visible()
        assert page.evaluate('navigator.language') == 'fr-FR'
        switch(page, 'fr')
        page.locator('#password').fill('wrong-password')
        page.locator('#login-form button[type=submit]').click()
        expect(page.locator('#login-error')).to_have_text('Mot de passe de l’espace de travail incorrect.')
        page.locator('#password').fill(PASSWORD)
        page.locator('#login-form button[type=submit]').click()
        sections = {
            'overview': 'Vue d’ensemble de la transformation',
            'people': 'Collaborateurs et questionnaires',
            'organization': 'Votre organisation',
            'tools': 'Les outils du quotidien',
            'roadmap': 'Vos prochaines opportunités d’agents',
        }
        expect(page.locator('#content h1')).to_have_text(sections['overview'])
        for section, heading in sections.items():
            page.locator(f'.nav a[href="#{section}"]').click()
            expect(page.locator('#content h1')).to_have_text(heading)
        page.locator('.nav a[href="#organization"]').click()
        page.locator('[data-action="add-entity"]').first.click()
        page.locator('#entity-name').fill('Organization')
        page.locator('#entity-form button[type=submit]').click()
        page.locator('[data-action="add-team"]').first.click()
        page.locator('#team-name').fill('Overview')
        page.locator('#team-form button[type=submit]').click()
        page.locator('.nav a[href="#people"]').click()
        page.locator('[data-action="add-person"]').first.click()
        page.locator('#person-name').fill('Alex English')
        page.locator('#person-email').fill('alex@example.com')
        page.locator('#person-role').fill('Transformation lead')
        page.locator('#person-form button[type=submit]').click()
        link = page.locator('#invite-url').input_value()
        page.locator('#modal [data-action="close-modal"]').last.click()
        assert page.evaluate('state.data.entities[0].name') == 'Organization'
        assert page.evaluate('state.data.teams[0].name') == 'Overview'
        expect(page.locator('#people-results')).to_contain_text('Transformation lead')

        employee = browser.new_context(locale='fr-FR', viewport={'width': 1280, 'height': 1000})
        form = employee.new_page()
        form.on('pageerror', lambda error: errors.append(str(error)))
        form.goto(link)
        expect(form.locator('h1')).to_have_text('Contribuez à améliorer votre quotidien professionnel, Alex.')
        expect(form.locator('.employee-context')).to_contain_text('Organization / Overview')
        expect(form.locator('.employee-context')).to_contain_text('Transformation lead')
        assert '#' not in form.url
        form.locator('input[data-tool="ChatGPT"]').check()
        form.locator('#intake-form button[type=submit]').click()
        form.locator('[data-action="add-workflow"]').click()
        form.locator('#wf-0-name').fill('Weekly "reporting"')
        form.locator('#wf-0-frequency').fill('5')
        form.locator('#wf-0-trigger').fill('Every Monday')
        form.locator('#wf-0-outcome').fill('Report sent')
        form.locator('#s-0-0-action').fill('=Draft "summary"')
        form.locator('#s-0-0-tool').select_option('ChatGPT')
        form.locator('#s-0-0-time').fill('60')
        form.locator('#s-0-0-support').select_option('automate')
        form.locator('[data-action="add-step"]').first.click()
        form.locator('#s-0-1-action').fill('Approve report')
        form.locator('#s-0-1-support').select_option('manual')
        form.locator('[data-action="workflow-view"][data-mode="diagram"]').click()
        form.locator('.diagram-node').nth(1).click()
        before = intake_snapshot(form)
        switch(form, 'en')
        assert intake_snapshot(form) == before, 'Switching must preserve draft, views, selection, and save bookkeeping'
        expect(form.locator('#wf-0-name')).to_have_value('Weekly "reporting"')
        expect(form.locator('.diagram-node').nth(1)).to_have_attribute('aria-pressed', 'true')
        expect(form.locator('[data-workflow-saved]')).to_have_text('Not saved yet')
        form.locator('[data-action="save-draft"]').click()
        expect(form.locator('[data-workflow-saved]')).to_have_text('Saved')
        form.locator('#s-0-1-action').fill('Approve and send report')
        before = intake_snapshot(form)
        switch(form, 'fr')
        assert intake_snapshot(form) == before
        expect(form.locator('[data-workflow-saved]')).to_have_text('Modifications non enregistrées')
        expect(form.locator('#s-0-1-action')).to_have_value('Approve and send report')
        expect(form.locator('[data-mode="diagram"]')).to_have_attribute('aria-pressed', 'true')
        expect(form.locator('.diagram-node').first.locator('[data-node-support]')).to_have_text('Automatisée')
        form.locator('[data-action="save-draft"]').click()
        expect(form.locator('[data-workflow-saved]')).to_have_text('Enregistré')
        saved = form.evaluate('JSON.stringify(state.intake.assessment)')
        form.reload()
        expect(form.locator('#intake-form')).to_be_visible()
        assert form.evaluate('JSON.stringify(state.intake.assessment)') == saved
        expect(form.locator('html')).to_have_attribute('lang', 'fr')
        form.locator('#intake-form button[type=submit]').click()
        expect(form.locator('#wf-0-name')).to_have_value('Weekly "reporting"')
        form.locator('#intake-form button[type=submit]').click()
        form.locator('#assessment-notes').fill('Keep English input untouched.')
        form.locator('#intake-form button[type=submit]').click()
        expect(form.locator('.success-panel h1')).to_have_text('Merci d’avoir partagé votre travail, Alex.')
        submitted = form.evaluate('JSON.stringify(state.intake.assessment)')
        switch(form, 'en')
        expect(form.locator('.success-panel h1')).to_have_text('Thanks for sharing your work, Alex.')
        assert form.evaluate('JSON.stringify(state.intake.assessment)') == submitted
        switch(form, 'fr')
        form.reload()
        expect(form.locator('.success-panel h1')).to_have_text('Merci d’avoir partagé votre travail, Alex.')

        page.locator('.nav a[href="#roadmap"]').click()
        expect(page.locator('.agent-card h3')).to_have_text('Assistant pour Weekly "reporting"')
        expect(page.locator('.agent-card .tag').first).to_have_text('Priorité : Élevée')
        assert page.evaluate('state.data.opportunities[0].priority') == 'High'
        with page.expect_download() as downloaded:
            page.locator('[data-action="export"]').click()
        destination = ARTIFACTS / 'bilingual-opportunities-fr.csv'
        downloaded.value.save_as(destination)
        raw = destination.read_bytes()
        assert raw.startswith(b'\xef\xbb\xbf'), 'CSV must keep its UTF-8 BOM'
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
        assert rows[0] == ['Agent suggéré', 'Entité', 'Équipe', 'Priorité', 'Heures potentielles / semaine',
                           'Collaborateurs', 'Outils', 'Vérification humaine', 'Actions suggérées']
        assert rows[1][:4] == ['Assistant pour Weekly "reporting"', 'Organization', 'Overview', 'Élevée']
        assert rows[1][8].startswith('\'=Draft "summary"'), 'CSV must protect formula-like user input'
        assert rows[1][5:7] == ['Alex English', 'ChatGPT']
        switch(page, 'en')
        expect(page.locator('.agent-card h3')).to_have_text('Weekly "reporting" assistant')
        switch(page, 'fr')
        page.set_viewport_size({'width': 390, 'height': 844})
        for section, heading in sections.items():
            page.goto(BASE + '#' + section)
            expect(page.locator('#content h1')).to_have_text(heading)
            page.screenshot(path=str(ARTIFACTS / f'bilingual-{section}-mobile.png'), full_page=True, animations='disabled')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (section, page.evaluate('''[...document.querySelectorAll('body *')]
                .filter(node => node.getBoundingClientRect().right > innerWidth)
                .slice(0, 12).map(node => ({tag: node.tagName, class: node.className, text: node.textContent.slice(0, 60)}))'''))
        form.set_viewport_size({'width': 390, 'height': 844})
        assert form.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'French success overflowed'
        form.locator('[data-action="edit-assessment"]').click()
        form.locator('[data-action="go-workflows"]').click()
        assert form.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'French workflow overflowed'
        form.screenshot(path=str(ARTIFACTS / 'bilingual-intake-mobile.png'), full_page=True, animations='disabled')

        invalid = browser.new_context(locale='fr-FR')
        error_page = invalid.new_page()
        error_page.on('pageerror', lambda error: errors.append(str(error)))
        error_page.goto(BASE + '/intake#invalid-invitation')
        expect(error_page.locator('h1')).to_have_text('Retrouvons le bon lien.')
        expect(error_page.locator('.intake-error p')).to_contain_text('expiré')
        switch(error_page, 'en')
        expect(error_page.locator('h1')).to_have_text('Let’s get you the right link.')
        expect(error_page.locator('.intake-error p')).to_contain_text('expired or is invalid')
        switch(error_page, 'fr')
        offline_page = invalid.new_page()
        offline_page.route('**/api/admin/workspace', lambda route: route.abort())
        offline_page.goto(BASE)
        expect(offline_page.locator('.intake-error p')).to_have_text('Connexion impossible. Veuillez réessayer.')
        switch(offline_page, 'en')
        expect(offline_page.locator('.intake-error p')).to_have_text('Unable to connect. Please try again.')
        assert not errors, errors
        print('PASS: French defaults, persistent choice, login, admin, unchanged input, draft/view preservation, submission, localized CSV, invalid invitations, and mobile layouts.')
        invalid.close()
        employee.close()
        admin.close()
        browser.close()


if __name__ == '__main__':
    run(browser_checks)
