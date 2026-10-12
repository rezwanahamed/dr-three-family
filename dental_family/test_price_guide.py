import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from .models import WebsiteWorkspace
from .content import seeds


class PriceGuideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff=get_user_model().objects.create_user(username='price-editor',email='prices@example.com',password='PricePassword!847',is_staff=True)

    def setUp(self):
        self.client.force_login(self.staff)
        self.base=self.client.get('/dashboard/content/').json()
        self.prices=[r for r in self.base['records'] if r['section']=='prices']

    def submit(self,state,path='/dashboard/publish/'):
        return self.client.generic('PUT' if path.endswith('content/') else 'POST',path,json.dumps({'state':state,'revision':self.base['revision']}),content_type='application/json')

    def test_prices_saved_as_drafts_then_published_in_existing_design(self):
        self.assertEqual(len(self.prices),11)
        edited={**self.prices[0],'price':'650–900 Tk','description':'650–900 Tk','category':'Updated dental essentials','order':1}
        new={**edited,'id':'new-price','title':'New price treatment','price':'Contact for estimate','order':2}
        state={'drafts':[edited,new],'deletions':[{'id':self.prices[-1]['id']}],'activity':[]}
        self.assertEqual(self.submit(state,'/dashboard/content/').status_code,200)
        self.assertNotContains(self.client.get('/pricing-guide-2/'),'650–900 Tk')
        self.base=self.client.get('/dashboard/content/').json()
        self.assertEqual(self.submit(state).status_code,200)
        response=self.client.get('/pricing-guide-2/')
        self.assertContains(response,'650–900 Tk')
        soup=BeautifulSoup(response.content,'html.parser')
        first=soup.select_one('main .price-card')
        self.assertEqual(first.h2.text,'Updated dental essentials')
        self.assertEqual([dt.text for dt in first.select('dt')],[edited['title'],new['title']])
        self.assertNotIn(self.prices[-1]['title'],soup.select_one('.prices-grid').text)
        self.assertIsNotNone(soup.select_one('.page-cta'))
        public=Client()
        self.assertContains(public.get('/pricing-guide-2/'),'New price treatment')

    def test_empty_library_stays_empty_after_deletion(self):
        state={'drafts':[],'deletions':[{'id':r['id']} for r in self.prices],'activity':[]}
        self.assertEqual(self.submit(state).status_code,200)
        self.assertEqual(len(BeautifulSoup(self.client.get('/pricing-guide-2/').content,'html.parser').select('.price-card')),0)
        self.assertFalse(any(r['section']=='prices' for r in self.client.get('/dashboard/content/').json()['records']))

    def test_invalid_prices_rejected_and_output_escaped(self):
        for changes in [{'category':''},{'price':''},{'order':-1},{'order':'2'},{'url':'/incorrect/'}]:
            response=self.submit({'drafts':[{**self.prices[0],**changes}]})
            self.assertEqual(response.status_code,400)
        record={**self.prices[0],'price':'<script>alert(1)</script>'}
        self.assertEqual(self.submit({'drafts':[record]}).status_code,200)
        soup=BeautifulSoup(self.client.get('/pricing-guide-2/').content,'html.parser')
        self.assertIsNone(soup.select_one('.price-card script'))
        self.assertEqual(soup.select_one('.price-card dd').text,record['price'])

    def test_old_published_workspace_gets_initial_price_entries(self):
        old=deepcopy(seeds());old.pop('price_guide_initialized')
        old['records']=[r for r in old['records'] if r['section']!='prices']
        WebsiteWorkspace.objects.update_or_create(pk=1,defaults={'published':old})
        data=self.client.get('/dashboard/content/').json()
        self.assertEqual(len([r for r in data['records'] if r['section']=='prices']),11)
        self.assertContains(self.client.get('/pricing-guide-2/'),'500 Tk')

    def test_canonical_price_guide_ignores_legacy_treatment_redirect(self):
        old=deepcopy(seeds())
        page=next(r for r in old['records'] if r['id']=='/pricing-guide-2/')
        page.update(section='treatments',url='/old-price-guide-slug/',url_aliases=['/pricing-guide-2/'])
        entry=next(r for r in old['records'] if r['section']=='prices')
        entry['price']='925 Tk'
        WebsiteWorkspace.objects.update_or_create(pk=1,defaults={'published':old})
        response=self.client.get('/pricing-guide-2/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'925 Tk')
        legacy=self.client.get('/price-guide/')
        self.assertEqual(legacy.status_code,301)
        self.assertEqual(legacy.url,'/pricing-guide-2/')

    def test_public_price_guide_uses_seed_without_workspace(self):
        WebsiteWorkspace.objects.all().delete()
        response=Client().get('/pricing-guide-2/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(BeautifulSoup(response.content,'html.parser').select('.price-card dl > div')),11)

    def test_title_slug_renders_price_guide_with_published_prices(self):
        old=deepcopy(seeds())
        page=next(r for r in old['records'] if r['id']=='/pricing-guide-2/')
        page.update(section='treatments',url='/a-little-clarity-on-costs/',url_aliases=['/pricing-guide-2/'],_edited=True)
        price=next(r for r in old['records'] if r['section']=='prices')
        price['price']='1,250 Tk'
        WebsiteWorkspace.objects.update_or_create(pk=1,defaults={'published':old})
        response=self.client.get('/a-little-clarity-on-costs/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'1,250 Tk')
        soup=BeautifulSoup(response.content,'html.parser')
        self.assertEqual(len(soup.select('main .price-card')),3)
        self.assertRedirects(self.client.get('/a-little-clarity-on-costs'),'/a-little-clarity-on-costs/',status_code=301)

    def test_title_slug_price_guide_available_before_publishing(self):
        WebsiteWorkspace.objects.all().delete()
        response=self.client.get('/a-little-clarity-on-costs/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Dental essentials')
