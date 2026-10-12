import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase
from .content import seeds
from .models import WebsiteWorkspace


class PaymentOptionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff=get_user_model().objects.create_user(username='payment-editor',email='payment-editor@example.com',password='PaymentPassword!827',is_staff=True)

    def setUp(self):
        self.client.force_login(self.staff)
        self.base=self.client.get('/dashboard/content/').json()
        self.methods=[r for r in self.base['records'] if r['section']=='payments']

    def submit(self,state,path='/dashboard/publish/'):
        return self.client.generic('PUT' if path.endswith('content/') else 'POST',path,json.dumps({'state':state,'revision':self.base['revision']}),content_type='application/json')

    def test_payment_drafts_publish_and_frontend_order_visibility(self):
        self.assertEqual(len(self.methods),3)
        cash={**self.methods[0],'id':'cash-new','title':'Cash at reception','payment_type':'cash','payment_label':'At the clinic','notes':'Pay after your consultation.','order':1}
        hidden={**self.methods[0],'enabled':False}
        bank={**self.methods[2],'order':2,'account_number':'0011223344','routing':'001234567'}
        state={'drafts':[cash,hidden,bank],'deletions':[{'id':self.methods[1]['id']}]}
        self.assertEqual(self.submit(state,'/dashboard/content/').status_code,200)
        self.assertNotContains(self.client.get('/financing-2/'),'Cash at reception')
        self.base=self.client.get('/dashboard/content/').json()
        self.assertEqual(self.submit(state).status_code,200)
        for route in ['/financing-2/','/simple-ways-to-pay/']:
            response=self.client.get(route)
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            cards=soup.select('main .payment-card')
            self.assertEqual([card.h2.text for card in cards],['Cash at reception','BRAC Bank PLC'])
            self.assertIn('Account: 0011223344',cards[1].text)
            self.assertIn('Routing: 001234567',cards[1].text)
            self.assertIn('Pay after your consultation.',cards[0].text)
            self.assertIsNotNone(soup.select_one('.notice'))

    def test_payment_validation_and_escaping(self):
        for changes in [{'payment_type':{}},{'payment_type':'invalid'},{'mobile_number':'invalid'},{'order':0},{'enabled':'yes'},{'url':'/incorrect/'}]:
            self.assertEqual(self.submit({'drafts':[{**self.methods[0],**changes}]}).status_code,400)
        self.assertEqual(self.submit({'drafts':[{**self.methods[2],'account_number':'letters'}]}).status_code,400)
        self.assertEqual(self.submit({'drafts':[{**self.methods[2],'routing':'letters'}]}).status_code,400)
        record={**self.methods[0],'notes':'<script>alert(1)</script>'}
        self.assertEqual(self.submit({'drafts':[record]}).status_code,200)
        soup=BeautifulSoup(self.client.get('/financing-2/').content,'html.parser')
        self.assertIsNone(soup.select_one('.payment-card script'))
        self.assertIn(record['notes'],soup.select_one('.payment-card').text)

    def test_deleted_methods_do_not_return_and_legacy_route_works(self):
        self.assertEqual(self.submit({'deletions':[{'id':r['id']} for r in self.methods]}).status_code,200)
        self.assertFalse(any(r['section']=='payments' for r in self.client.get('/dashboard/content/').json()['records']))
        self.assertFalse(BeautifulSoup(self.client.get('/financing-2/').content,'html.parser').select('.payment-card'))
        old=deepcopy(seeds());old.pop('payments_initialized')
        old['records']=[r for r in old['records'] if r['section']!='payments']
        finance=next(r for r in old['records'] if r['id']=='/financing-2/')
        finance.update(section='treatments',url='/simple-ways-to-pay/',url_aliases=['/financing-2/'])
        WebsiteWorkspace.objects.update_or_create(pk=1,defaults={'published':old})
        self.assertEqual(len([r for r in self.client.get('/dashboard/content/').json()['records'] if r['section']=='payments']),3)
        self.assertEqual(self.client.get('/financing-2/').status_code,200)
        self.assertEqual(self.client.get('/simple-ways-to-pay/').status_code,200)
