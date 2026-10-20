import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase
from .content import seeds
from .models import WebsiteWorkspace
from .pricing import calculator_data, price_bounds


class DatabasePricingTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user(username='pricing-db',password='test',is_staff=True)
        self.client.force_login(user)
        self.base=self.client.get('/dashboard/content/').json()
        self.treatment=next(r for r in self.base['records'] if r['section']=='treatments' and r.get('service'))

    def entry(self,**changes):
        return {'id':'db-price','section':'prices','url':'/pricing-guide-2/','title':self.treatment['title'],'category':'Service','service_id':self.treatment['service'],'treatment_id':self.treatment['id'],'price_type':'range','price_min':'1000','price_max':'1500','price':'1000–1500 Tk','order':1,**changes}

    def publish(self,state):
        return self.client.post('/dashboard/publish/',json.dumps({'revision':self.base['revision'],'state':state}),content_type='application/json')

    def test_db_catalog_and_linked_price(self):
        service=next(s for s in self.base['pricing_catalog'] if s['id']==self.treatment['service'])
        self.assertIn(self.treatment['id'],[r['id'] for r in service['treatments']])
        response=self.publish({'drafts':[self.entry()]})
        self.assertEqual(response.status_code,200,response.content)
        saved=next(r for r in response.json()['records'] if r['id']=='db-price')
        self.assertEqual(saved['category'],service['name'])
        page=self.client.get('/a-little-clarity-on-costs/')
        soup=BeautifulSoup(page.content,'html.parser')
        payload=json.loads(soup.select_one('#pricing-calculator-data').string)
        item=next(p for s in payload['services'] for p in s['prices'] if p['id']=='db-price')
        self.assertEqual((item['min'],item['max']),(100000,150000))

    def test_empty_service_accepts_service_price(self):
        state={'services':[{'id':'new-service','name':'New service from DB','treatments':[]}], 'drafts':[self.entry(service_id='new-service',treatment_id='',title='New service from DB')]}
        response=self.publish(state)
        self.assertEqual(response.status_code,200,response.content)
        service=next(s for s in response.json()['pricing_catalog'] if s['id']=='new-service')
        self.assertEqual(service['treatments'],[])

    def test_cross_service_and_unknown_service_rejected(self):
        for changes in [{'service_id':'missing'}, {'service_id':'clear_aligner','treatment_id':'/fillings/'}]:
            response=self.publish({'drafts':[self.entry(**changes)]})
            self.assertEqual(response.status_code,400,response.content)

    def test_deleted_treatment_cannot_receive_price(self):
        response=self.publish({'drafts':[self.entry()], 'deletions':[{'id':self.treatment['id']}]})
        self.assertEqual(response.status_code,400)

    def test_draft_price_does_not_leak_to_calculator(self):
        response=self.client.put('/dashboard/content/',json.dumps({'revision':self.base['revision'],'state':{'drafts':[self.entry(title='Unpublished calculator fee')]}}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertNotContains(self.client.get('/a-little-clarity-on-costs/'),'Unpublished calculator fee')

    def test_price_parsing_keeps_quote_items_distinct_from_zero(self):
        self.assertEqual(price_bounds({'price':'1,250–1,500 Tk'}),(125000,150000))
        self.assertEqual(price_bounds({'price_type':'single','price_min':'0'}),(0,0))
        self.assertIsNone(price_bounds({'price_type':'custom','price':'Contact for estimate'}))
        self.assertIsNone(price_bounds({'price':'Unexpected text'}))

    def test_calculator_uses_only_published_values_and_safe_json(self):
        data=seeds();price=next(r for r in data['records'] if r['section']=='prices');price['title']='</script><script>alert(1)</script>'
        WebsiteWorkspace.objects.update_or_create(pk=1,defaults={'published':data})
        response=self.client.get('/a-little-clarity-on-costs/')
        soup=BeautifulSoup(response.content,'html.parser');payload=json.loads(soup.select_one('#pricing-calculator-data').string)
        self.assertIn(price['title'],[p['title'] for s in payload['services'] for p in s['prices']])
        self.assertNotContains(response,'<script>alert(1)</script>')

    def test_service_fee_available_without_treatment_fees(self):
        data={'services':[{'id':'cosmetic','name':'Cosmetic dentistry'}], 'records':[
            {'id':'treatment','section':'treatments','service':'cosmetic','title':'Veneers'},
            {'id':'service-fee','section':'prices','service_id':'cosmetic','treatment_id':'',
             'category':'Cosmetic dentistry','title':'Cosmetic dentistry','price':'2,000 Tk'}]}
        service=calculator_data(data)['services'][0]
        self.assertEqual(len(service['prices']),1)
        self.assertEqual(service['prices'][0]['treatment_id'],'')
        self.assertEqual(service['prices'][0]['min'],200000)
