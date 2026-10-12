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
        first=next(card for card in soup.select('main .price-card') if card.h2.text=='Updated dental essentials')
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

    def test_services_create_rename_and_order_public_cards(self):
        names=self.base['price_services']
        self.assertEqual(len(names),3)
        moved={**self.prices[0],'category':'Personalized care'}
        order=['Personalized care',names[2],names[1],names[0]]
        state={'drafts':[moved],'priceServices':order}
        self.assertEqual(self.submit(state).status_code,200)
        soup=BeautifulSoup(self.client.get('/a-little-clarity-on-costs/').content,'html.parser')
        self.assertEqual([h.text for h in soup.select('.price-card h2')],order)
        self.base=self.client.get('/dashboard/content/').json()
        renamed='Personal care'
        current=next(r for r in self.base['records'] if r['id']==moved['id'])
        state={'drafts':[{**current,'category':renamed}],'priceServices':[renamed,*order[1:]]}
        self.assertEqual(self.submit(state).status_code,200)
        self.assertContains(self.client.get('/pricing-guide-2/'),renamed)
        self.assertNotContains(self.client.get('/pricing-guide-2/'),'Personalized care')

    def test_service_delete_requires_price_reassignment(self):
        names=self.base['price_services']
        remaining=names[1:]
        self.assertEqual(self.submit({'priceServices':remaining}).status_code,400)
        updates=[{**r,'category':remaining[0]} for r in self.prices if r['category']==names[0]]
        self.assertEqual(self.submit({'priceServices':remaining,'drafts':updates}).status_code,200)
        self.assertEqual(self.client.get('/dashboard/content/').json()['price_services'],remaining)
        self.assertNotContains(self.client.get('/pricing-guide-2/'),names[0])
        self.base=self.client.get('/dashboard/content/').json()
        self.assertEqual(self.submit({'drafts':[]}).status_code,200)
        self.assertEqual(self.client.get('/dashboard/content/').json()['price_services'],remaining)

    def test_service_names_are_unique_and_empty_services_can_be_saved(self):
        names=self.base['price_services']
        self.assertEqual(self.submit({'priceServices':[names[0],names[0].upper()]}).status_code,400)
        self.assertEqual(self.submit({'priceServices':[names[0],'  ']}).status_code,400)
        response=self.submit({'priceServices':[*names,'New empty service']})
        self.assertEqual(response.status_code,200)
        self.assertIn('New empty service',response.json()['price_services'])
        self.assertNotContains(self.client.get('/pricing-guide-2/'),'New empty service')

    def test_single_and_range_prices_are_formatted_by_backend(self):
        record={**self.prices[0],'price_type':'range','price_min':'1000','price_max':'1500','price':'untrusted display'}
        response=self.submit({'drafts':[record]})
        self.assertEqual(response.status_code,200)
        saved=next(r for r in response.json()['records'] if r['id']==record['id'])
        self.assertEqual(saved['price'],'1,000–1,500 Tk')
        self.assertContains(self.client.get('/a-little-clarity-on-costs/'),'1,000–1,500 Tk')
        self.base=self.client.get('/dashboard/content/').json()
        record={**saved,'price_type':'single','price_min':'1250.50'}
        response=self.submit({'drafts':[record]})
        self.assertEqual(response.status_code,200)
        saved=next(r for r in response.json()['records'] if r['id']==record['id'])
        self.assertEqual(saved['price'],'1,250.5 Tk')
        self.assertNotIn('price_max',saved)

    def test_invalid_price_ranges_are_rejected(self):
        template={**self.prices[0],'price_type':'range','price_min':'1000','price_max':'1500'}
        for changes in [{'price_max':'500'},{'price_max':'1000'},{'price_min':'-1'},{'price_max':'NaN'},{'price_min':'1.001'},{'price_type':{}},{'price_min':'1000000001'}]:
            self.assertEqual(self.submit({'drafts':[{**template,**changes}]}).status_code,400)

    def test_custom_price_text_is_preserved(self):
        record={**self.prices[0],'price_type':'custom','price':'Contact for estimate','price_min':'1000','price_max':'1500'}
        response=self.submit({'drafts':[record]})
        self.assertEqual(response.status_code,200)
        saved=next(r for r in response.json()['records'] if r['id']==record['id'])
        self.assertEqual(saved['price'],'Contact for estimate')
        self.assertNotIn('price_min',saved)
        self.assertNotIn('price_max',saved)
