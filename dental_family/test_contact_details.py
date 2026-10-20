import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase


class ContactDetailsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff=get_user_model().objects.create_user(username='contact-editor',email='contact-editor@example.com',password='ContactPassword!927',is_staff=True)

    def setUp(self):
        self.client.force_login(self.staff)
        self.base=self.client.get('/dashboard/content/').json()

    def submit(self,state,path='/dashboard/publish/'):
        return self.client.generic('PUT' if path.endswith('content/') else 'POST',path,json.dumps({'state':state,'revision':self.base['revision']}),content_type='application/json')

    def test_contact_details_drafts_and_public_integration(self):
        details={**self.base['contact_details'],'phone':'+880 1888-123456','email':'hello@example.com','whatsapp':'+8801888123456','facebook':'','instagram':'https://www.instagram.com/updatedclinic','opening_hours':'Open Saturday–Thursday, 10am–8pm.'}
        state={'drafts':[],'contactDetails':details}
        self.assertEqual(self.submit(state,'/dashboard/content/').status_code,200)
        self.assertNotContains(self.client.get('/contact/'),'hello@example.com')
        self.base=self.client.get('/dashboard/content/').json()
        self.assertEqual(self.base['state']['contactDetails'],details)
        self.assertEqual(self.submit(state).status_code,200)
        for route in ['/contact/','/','/a-little-clarity-on-costs/','/blog/']:
            response=self.client.get(route)
            self.assertEqual(response.status_code,200)
            soup=BeautifulSoup(response.content,'html.parser')
            bar=soup.select_one('.mobile-action-bar')
            self.assertIsNotNone(bar)
            self.assertEqual(len(bar.select('a')),3)
            self.assertEqual(bar.select_one('a[href^="tel:"]')['href'],'tel:+8801888123456')
            self.assertEqual(bar.select_one('a[href^="https://wa.me/"]')['href'],'https://wa.me/8801888123456')
            self.assertEqual(bar.select_one('.mobile-action-bar--booking')['href'],'/appointment/')
            self.assertEqual(soup.select_one('.footer--email')['href'],'mailto:hello@example.com')
            self.assertEqual(soup.select_one('.footer--phone')['href'],'tel:+8801888123456')
            self.assertIn('+880 1888-123456',soup.select_one('.footer--phone').text)
            self.assertIsNone(soup.select_one('.footer--connection a[href*="facebook"]'))
            self.assertIsNotNone(soup.select_one('a[href="https://www.instagram.com/updatedclinic"]'))
        contact=BeautifulSoup(self.client.get('/contact/').content,'html.parser')
        self.assertEqual(contact.select_one('[data-contact-form]')['data-contact-email'],'hello@example.com')
        self.assertEqual(contact.select_one('.contact-methods a[href^="mailto:"] h3').text,'hello@example.com')
        self.assertEqual(contact.select_one('.hours-note').text,details['opening_hours'])
        self.assertIsNotNone(contact.select_one('a[href="https://wa.me/8801888123456"]'))
        self.assertEqual(self.client.get('/dashboard/content/').json()['contact_details'],details)

    def test_branch_specific_phone_is_preserved(self):
        location=deepcopy(next(r for r in self.base['records'] if r['section']=='locations'))
        location['phone']='+8801777123456'
        details={**self.base['contact_details'],'phone':'+880 1888-123456'}
        self.assertEqual(self.submit({'drafts':[location],'contactDetails':details}).status_code,200)
        soup=BeautifulSoup(self.client.get('/contact/').content,'html.parser')
        self.assertIsNotNone(soup.select_one('.location-card a[href="tel:+8801777123456"]'))
        self.assertEqual(soup.select_one('.footer--phone')['href'],'tel:+8801888123456')

    def test_invalid_contacts_rejected_and_optional_links_hidden(self):
        for changes in [{'email':'invalid-email'},{'phone':'123'},{'facebook':'javascript:alert(1)'},{'instagram':{}},{'whatsapp':'invalid'}]:
            self.assertEqual(self.submit({'contactDetails':{**self.base['contact_details'],**changes}}).status_code,400)
        details={**self.base['contact_details'],'whatsapp':'','facebook':'','instagram':''}
        self.assertEqual(self.submit({'contactDetails':details}).status_code,200)
        soup=BeautifulSoup(self.client.get('/contact/').content,'html.parser')
        self.assertFalse(soup.select('a[href^="https://wa.me/"]'))
        self.assertEqual(len(soup.select('.contact-methods > a')),2)
