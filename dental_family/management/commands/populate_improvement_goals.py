"""Populate the requested goal cards without replacing existing editorial content."""
import json
from copy import deepcopy
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from dental_family.content import seeds
from dental_family.improvements import validate_options
from dental_family.models import WebsiteWorkspace


class Command(BaseCommand):
    help = 'Preview or publish the curated improvement-goal catalog and treatment selections.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh-selections', action='store_true', help='Replace treatment-goal associations with the curated catalog.')
        parser.add_argument('--publish', action='store_true', help='Apply the catalog to this website workspace.')

    @transaction.atomic
    def handle(self, *args, **options):
        catalog = json.loads((settings.BASE_DIR / 'static/dental_family/improvement-catalog.json').read_text())
        workspace = WebsiteWorkspace.objects.select_for_update().filter(pk=1).first()
        published = deepcopy(workspace.published if workspace and workspace.published else seeds())
        draft = deepcopy(workspace.draft if workspace else {})
        treatments = {r['id']:r for r in published['records'] if r['section']=='treatments'}
        additions = [o for o in catalog['options'] if o['treatment_id'] in treatments]
        library = {o['id']:o for o in published.get('improvement_options', [])}
        for option in additions:
            image = settings.BASE_DIR / option['image'].lstrip('/')
            if not image.is_file():
                raise CommandError('Missing generated image: '+option['image'])
            library.setdefault(option['id'], option)
        validate_options(list(library.values()))
        published['improvement_options'] = list(library.values())
        added_ids = set(library)
        updated = 0
        for identifier, values in catalog['selections'].items():
            record = treatments.get(identifier)
            if record is not None and (options['refresh_selections'] or record.get('improvement_options') is None):
                record['improvement_options'] = [value for value in values if value in added_ids]
                updated += 1
        if 'improvementOptions' in draft:
            pending = {o['id']:o for o in draft['improvementOptions']}
            for option in additions:
                pending.setdefault(option['id'], option)
            draft['improvementOptions'] = list(pending.values())
        self.stdout.write(f'{len(additions)} curated options; {updated} treatment pages receive selections.')
        if not options['publish']:
            self.stdout.write('Preview only. Use --publish to apply.')
            return
        if workspace:
            backup = Path('/tmp') / ('dental-goals-workspace-'+timezone.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
            backup.write_text(json.dumps({'revision':workspace.revision, 'published':workspace.published, 'draft':workspace.draft},ensure_ascii=False,indent=2))
            self.stdout.write('Workspace backup: '+str(backup))
        else:
            workspace = WebsiteWorkspace(pk=1)
        if published == workspace.published and draft == workspace.draft:
            self.stdout.write('Catalog already applied; no changes needed.')
            return
        workspace.published = published
        workspace.draft = draft
        workspace.revision += 1
        workspace.save()
        self.stdout.write(self.style.SUCCESS(f'Published improvement goals. Workspace revision {workspace.revision}.'))
