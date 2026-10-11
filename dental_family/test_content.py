import json
from copy import deepcopy
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from .content import seeds
from .models import WebsiteWorkspace


class ContentIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(username='editor', email='editor@example.com', password='test-password', is_staff=True)

    def setUp(self):
        self.client.force_login(self.staff)
        self.base = self.client.get('/dashboard/content/').json()
        self.state = {'drafts': [], 'deletions': [], 'activity': []}

    def submit(self, url='/dashboard/publish/', revision=None, state=None):
        return self.client.generic('PUT' if url.endswith('content/') else 'POST', url,
            json.dumps({'revision': self.base['revision'] if revision is None else revision, 'state': self.state if state is None else state}), content_type='application/json')

    def edit(self, section, **changes):
        record = deepcopy(next(r for r in self.base['records'] if r['section']==section))
        record.update(changes)
        self.state['drafts'].append(record)
        return record

    def soup(self, route):
        response = self.client.get(route)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, 'html.parser')

    def test_drafts_shared_but_not_public_until_publish(self):
        record = self.edit('treatments', title='New shared heading', details='<h2>New details</h2><p>Saved in database.</p>', short_details='Updated summary')
        response = self.submit('/dashboard/content/')
        self.assertEqual(response.status_code,200)
        other = Client();other.force_login(self.staff)
        self.assertEqual(other.get('/dashboard/content/').json()['state']['drafts'][0]['title'],record['title'])
        self.assertNotContains(self.client.get(record['url']),'New shared heading')
        self.assertEqual(self.submit(revision=response.json()['revision']).status_code,200)
        public = self.soup(record['url'])
        self.assertEqual(public.select_one('h1').text,'New shared heading')
        self.assertIn('Saved in database.',public.select_one('.prose').text)
        self.assertEqual(WebsiteWorkspace.objects.get(pk=1).draft['drafts'],[])

    def test_new_routes_seo_and_deleted_routes(self):
        self.state['drafts']=[{'id':'new-article','section':'articles','url':'/new-story/','title':'New article','description':'Story summary','short_details':'Short story','details':'<h2>Story</h2><p>Actual article body.</p>','seo_title':'Article SEO title','meta_description':'Search summary','robots':'index,follow','image':'/media/gallery/story.webp'}]
        old = next(r for r in self.base['records'] if r['section']=='articles')
        self.state['deletions']=[{'id':old['id']}]
        self.assertEqual(self.submit().status_code,200)
        public=self.soup('/new-story/')
        self.assertEqual(public.title.text,'Article SEO title')
        self.assertEqual(public.select_one('meta[name="description"]')['content'],'Search summary')
        self.assertEqual(public.select_one('.article-hero img')['src'],'/media/gallery/story.webp')
        self.assertEqual(self.client.get(old['url']).status_code,404)
        self.assertEqual(self.client.get('/new-story').status_code,301)
        self.assertContains(self.client.get('/blog/'),'New article')
        self.assertContains(self.client.get('/sitemap.xml'),'/new-story/')

    def test_faq_topics_questions_and_order(self):
        question=self.edit('faqs',title='Published patient question?',description='Published patient answer.',topic='new-faq',url='/new-faq/',order=1)
        self.state['faqTopics']=[{'id':'new-faq','title':'New FAQ topic','url':'/new-faq/'}]
        self.state['faqTopicOrder']=['new-faq']
        self.assertEqual(self.submit().status_code,200)
        self.assertEqual(self.soup('/faq/').select_one('.topic-card')['href'],'/new-faq/')
        public=self.soup('/new-faq/')
        self.assertEqual(public.select_one('.accordion-item h3 button').get_text(strip=True),'Published patient question?+')
        self.assertIn(question['description'], public.select_one('.accordion-panel').text)

    def test_photos_doctors_clinic_and_locations(self):
        gallery=self.edit('gallery',title='Published photo',image='/media/gallery/new.webp',alt='Uploaded clinic photo',order=1)
        doctor=self.edit('doctors',title='Dr. Updated Name',specialty='Updated specialty',qualifications='BDS\nAdditional qualification',registration='1234')
        clinic=self.edit('clinic',title='Updated clinic space',description='A new clinic caption',image='/media/gallery/clinic.webp')
        location=self.edit('locations',title='Updated branch',address='New street, Chattogram',phone='+8801999961517',map_pin='22.3, 91.8')
        self.assertEqual(self.submit().status_code,200)
        self.assertEqual(self.soup('/gallery/').select_one('.gallery-grid button img')['src'],gallery['image'])
        self.assertIn(doctor['title'],self.soup('/our-doctors/').select_one('.doctor-profile').text)
        self.assertContains(self.client.get('/'),doctor['title'])
        self.assertContains(self.client.get('/about-us/'),clinic['description'])
        public=self.soup('/contact/')
        self.assertIn(location['address'],public.select_one('.location-card').text)
        self.assertIn('22.3%2C%2091.8',public.select_one('.location-card iframe')['src'])
        self.assertContains(self.client.get('/'),location['title'])

    def test_services_navigation_and_rich_text_sanitization(self):
        service=self.base['services'][0]
        self.state['serviceEdits']={service['id']:{**service,'name':'New service label','treatments':['First treatment','Second treatment','Third treatment','Hidden fourth']}}
        self.state['serviceOrder']=[service['id']]
        record=self.edit('treatments',details='<p onclick="alert(1)">Safe details</p><script>alert(1)</script><a href="javascript:alert(1)">Unsafe link</a>')
        self.assertEqual(self.submit().status_code,200)
        public=self.soup(record['url'])
        self.assertNotIn('onclick',str(public.select_one('.prose')))
        self.assertNotIn('javascript:',str(public.select_one('.prose')))
        nav=self.soup('/').select_one('.doctor-nav--serviceCategory')
        self.assertIn('New service label',nav.text)
        self.assertEqual(len(nav.select('.doctor-nav--treatmentList li')),3)

    def test_conflicts_and_duplicate_routes_rejected(self):
        self.assertEqual(self.submit('/dashboard/content/').status_code,200)
        self.assertEqual(self.submit().status_code,409)
        revision=WebsiteWorkspace.objects.get(pk=1).revision
        self.state['drafts']=[{'id':'collision','section':'pages','url':'/','title':'Collision','description':'Duplicate homepage'}]
        self.assertEqual(self.submit(revision=revision).status_code,400)
        self.assertFalse(WebsiteWorkspace.objects.get(pk=1).published)

    def test_staff_and_csrf_required(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/dashboard/content/').status_code,403)
        client.force_login(self.staff)
        self.assertEqual(client.post('/dashboard/publish/',json.dumps({'state':self.state,'revision':0}),content_type='application/json').status_code,403)
        client.get('/dashboard/')
        response=client.post('/dashboard/publish/',json.dumps({'state':self.state,'revision':0}),content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code,200)

    def test_gallery_deletion_only_visible_after_publication(self):
        photo = next(r for r in self.base['records'] if r['section']=='gallery')
        initial = len(self.soup('/gallery/').select('.gallery-grid button'))
        self.state['deletions']=[{'id': photo['id'], 'section': 'gallery'}]
        saved = self.submit('/dashboard/content/')
        self.assertEqual(saved.status_code,200)
        self.assertEqual(len(self.soup('/gallery/').select('.gallery-grid button')),initial)
        self.assertEqual(self.submit(revision=saved.json()['revision']).status_code,200)
        public = self.soup('/gallery/')
        self.assertEqual(len(public.select('.gallery-grid button')),initial-1)
        self.assertFalse(any(img.get('src')==photo['image'] for img in public.select('.gallery-grid img')))

    def test_gallery_sections_saved_and_published_as_filters(self):
        record=self.edit('gallery',gallery_category='Clinic events',title='Community event')
        self.state['galleryCategories']=['Clinic events']
        saved=self.submit('/dashboard/content/')
        self.assertEqual(saved.status_code,200)
        shared=self.client.get('/dashboard/content/').json()
        self.assertEqual(shared['state']['galleryCategories'],['Clinic events'])
        self.assertEqual(self.submit(revision=saved.json()['revision']).status_code,200)
        public=self.soup('/gallery/')
        self.assertIn('Clinic events',[node.text for node in public.select('.filter-label')])
        self.assertEqual(public.select_one('.gallery-grid button')['data-category'],'Clinic events')
        self.assertEqual(self.client.get('/dashboard/content/').json()['gallery_sections'],['Our space','Our team','Our technology','Clinic events'])

    def test_gallery_section_rename_delete_and_reassignment(self):
        team=[r for r in self.base['records'] if r['section']=='gallery' and r.get('gallery_category')=='Our team']
        self.state['galleryCategories']=['People']
        self.state['deletedGalleryCategories']=['Our team']
        self.state['drafts']=[{**record,'gallery_category':'People'} for record in team]
        published=self.submit()
        self.assertEqual(published.status_code,200)
        self.assertNotIn('Our team',published.json()['gallery_sections'])
        self.assertIn('People',published.json()['gallery_sections'])
        public=self.soup('/gallery/')
        self.assertEqual(len(public.select('[data-category="People"]')),len(team))
        self.state={'drafts':[], 'activity':[], 'deletedGalleryCategories':['People']}
        self.assertEqual(self.submit(revision=published.json()['revision']).status_code,400)
        self.state['drafts']=[{**record,'gallery_category':'Our space'} for record in team]
        removed=self.submit(revision=published.json()['revision'])
        self.assertEqual(removed.status_code,200)
        self.assertNotIn('People',removed.json()['gallery_sections'])
        self.assertNotIn('Our team',removed.json()['gallery_sections'])
        again=self.submit(revision=removed.json()['revision'],state={'drafts':[],'activity':[]})
        self.assertEqual(again.status_code,200)
        self.assertNotIn('Our team',again.json()['gallery_sections'])
        self.assertNotIn('People',again.json()['gallery_sections'])

    def test_public_gallery_filters_use_backend_sections_with_all_default(self):
        snapshot=seeds()
        snapshot['gallery_sections']=['Our team','Our technology','Our spaces','Our space','Community events']
        WebsiteWorkspace.objects.filter(pk=1).update(published=snapshot)
        public=self.soup('/gallery/')
        filters=public.select('.filter-row button')
        self.assertEqual([button.select_one('.filter-label').text for button in filters],['All photos','Our team','Our technology','Our space','Community events'])
        self.assertEqual([button['aria-pressed'] for button in filters],['true','false','false','false','false'])
        self.assertFalse(any(button.has_attr('hidden') for button in public.select('.gallery-grid button')))
        backend=self.client.get('/dashboard/content/').json()
        self.assertEqual(backend['gallery_sections'],['Our team','Our technology','Our space','Community events'])

    def test_unpublished_gallery_uses_backend_initial_sections(self):
        public=self.soup('/gallery/')
        self.assertEqual([node.text for node in public.select('.filter-label')],['All photos','Our space','Our team','Our technology'])
        self.assertEqual(public.select_one('.filter-row button')['aria-pressed'],'true')
