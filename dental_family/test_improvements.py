import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import WebsiteWorkspace


class ImprovementOptionsTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user(username='goals-editor',password='test',is_staff=True)
        self.client.force_login(user)
        self.base=self.client.get('/dashboard/content/').json()
        self.treatments=[r for r in self.base['records'] if r['section']=='treatments']
        self.record=deepcopy(self.treatments[0])
        self.options=[{'id':'goal-smile','title':'Improve my smile','image':'/static/dental_family/assets/images/theme/smile.png','treatment_id':self.treatments[1]['id']}, {'id':'goal-align','title':'Straighten my teeth','image':'/static/dental_family/assets/images/theme/aligners.png','treatment_id':self.treatments[2]['id']}]
        self.record['improvement_options']=[o['id'] for o in self.options]
        self.state={'drafts':[self.record],'improvementOptions':self.options}

    def submit(self,endpoint,revision,state=None):
        return self.client.generic('PUT' if endpoint.endswith('content/') else 'POST',endpoint,json.dumps({'revision':revision,'state':state or self.state}),content_type='application/json')

    def test_multiselect_saved_and_public_only_after_publish(self):
        response=self.submit('/dashboard/content/',self.base['revision'])
        self.assertEqual(response.status_code,200,response.content)
        restored=self.client.get('/dashboard/content/').json()
        self.assertEqual(restored['state']['drafts'][0]['improvement_options'],['goal-smile','goal-align'])
        self.assertNotContains(self.client.get(self.record['url']), 'class="treatment-goals"')
        response=self.submit('/dashboard/publish/',restored['revision'])
        self.assertEqual(response.status_code,200,response.content)
        data=self.client.get('/dashboard/content/').json()
        record=next(r for r in data['records'] if r['id']==self.record['id'])
        self.assertNotContains(self.client.get(record['url']), 'class="treatment-goals"')
        soup=BeautifulSoup(self.client.get('/').content,'html.parser')
        cards=soup.select('.treatment-goal-card')
        self.assertEqual(len(cards),2)
        self.assertEqual(cards[0]['href'],'/smile-goals/goal-smile/')
        self.assertIn('Improve my smile',cards[0].text)
        self.assertEqual(data['improvement_options'],self.options)
        results=self.client.get(cards[0]['href'])
        self.assertEqual(results.status_code,200)
        listing=BeautifulSoup(results.content,'html.parser')
        self.assertEqual(len(listing.select('.goal-treatment-list > li')),2)
        self.assertContains(results,self.record['title'])
        target=next(r for r in data['records'] if r['id']==self.options[0]['treatment_id'])
        self.assertContains(results,target['title'])
        for link in listing.select('.goal-treatment-view'):
            self.assertEqual(self.client.get(link['href']).status_code,200)

    def test_remove_option_cleans_saved_selections(self):
        response=self.submit('/dashboard/publish/',self.base['revision'])
        self.assertEqual(response.status_code,200)
        response=self.submit('/dashboard/publish/',response.json()['revision'],{'drafts':[],'improvementOptions':[]})
        self.assertEqual(response.status_code,200,response.content)
        data=self.client.get('/dashboard/content/').json()
        self.assertEqual(data['improvement_options'],[])
        record=next(r for r in data['records'] if r['id']==self.record['id'])
        self.assertEqual(record['improvement_options'],[])
        self.assertNotContains(self.client.get(record['url']),'class="treatment-goals"')
        self.assertFalse(BeautifulSoup(self.client.get('/').content,'html.parser').select('.treatment-goal-card'))
        self.assertEqual(self.client.get('/smile-goals/goal-smile/').status_code,404)

    def test_rejects_unsafe_images_and_invalid_selection_shapes(self):
        self.options[0]['image']='javascript:alert(1)'
        self.assertEqual(self.submit('/dashboard/content/',self.base['revision']).status_code,400)
        self.options[0]['image']='/static/image.jpg'
        self.record['improvement_options']='goal-smile'
        self.assertEqual(self.submit('/dashboard/content/',self.base['revision']).status_code,400)

class CuratedGoalCatalogTests(TestCase):
    def test_preview_does_not_change_workspace(self):
        from django.core.management import call_command
        from io import StringIO
        from .content import seeds
        original=WebsiteWorkspace.objects.create(pk=1,published=seeds(),draft={'drafts':[]},revision=17)
        call_command('populate_improvement_goals',stdout=StringIO())
        original.refresh_from_db()
        self.assertEqual(original.revision,17)
        self.assertNotIn('improvement_options',original.published)

    def test_population_preserves_existing_choices_and_is_idempotent(self):
        from django.core.management import call_command
        from io import StringIO
        from .content import seeds
        data=seeds()
        record=next(r for r in data['records'] if r['id']=='/clear_aligner/')
        record['improvement_options']=[]
        workspace=WebsiteWorkspace.objects.create(pk=1,published=data,draft={'drafts':[],'settings':{'name':'Keep my workspace'}},revision=17)
        call_command('populate_improvement_goals',publish=True,stdout=StringIO())
        workspace.refresh_from_db()
        self.assertEqual(len(workspace.published['improvement_options']),8)
        self.assertEqual(workspace.draft['settings']['name'],'Keep my workspace')
        unchanged=next(r for r in workspace.published['records'] if r['id']=='/clear_aligner/')
        self.assertEqual(unchanged['improvement_options'],[])
        filled=next(r for r in workspace.published['records'] if r['id']=='/root-canals/')
        self.assertTrue(filled['improvement_options'])
        revision=workspace.revision
        call_command('populate_improvement_goals',publish=True,stdout=StringIO())
        workspace.refresh_from_db()
        self.assertEqual(workspace.revision,revision)
