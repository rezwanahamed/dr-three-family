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
        response = self.client.get(route, follow=True)
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
        self.assertIsNone(public.select_one('.article-hero img'))
        self.assertEqual(self.soup('/blog/').select_one('a.blog-card[href="/new-story/"] img')['src'],'/media/gallery/story.webp')
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
        self.assertIsNone(public.select_one('.location-card iframe'))
        self.assertIn('22.3%2C%2091.8',public.select_one('.location-card .location-directions')['href'])
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

    def test_treatment_image_shown_in_hero_and_listing_cards(self):
        treatment=self.edit('treatments',title='Treatment without detail thumbnail',image='/media/gallery/treatment-thumb.webp',short_details='Treatment card summary',details='<p>Treatment details remain visible.</p>')
        self.assertEqual(self.submit().status_code,200)
        detail=self.soup(treatment['url'])
        self.assertIsNone(detail.select_one('main .article-hero'))
        self.assertEqual(detail.select_one('main .page-intro-photo')['src'], treatment['image'])
        self.assertIn('Treatment details remain visible.',detail.select_one('.prose').text)
        listing=self.soup('/services/')
        canonical=self.client.get(treatment["url"]).url
        card=listing.select_one(f'a.treatment-card--card[href="{canonical}"]')
        self.assertEqual(card.img['src'],treatment['image'])

    def test_homepage_treatment_selection_order_and_limit(self):
        treatments=[r for r in self.base['records'] if r['section']=='treatments']
        self.assertEqual(len([r for r in treatments if r.get('show_on_homepage')]),3)
        chosen=list(reversed(treatments[-3:]))
        self.state['homepageTreatmentOrder']=[r['id'] for r in chosen]
        self.assertEqual(self.submit().status_code,200)
        cards=self.soup('/').select('main .treatment-card--card')
        self.assertEqual([card['href'] for card in cards],[r['url'] for r in chosen])
        self.base=self.client.get('/dashboard/content/').json()
        self.state['homepageTreatmentOrder']=[r['id'] for r in treatments[:4]]
        self.assertEqual(self.submit('/dashboard/content/').status_code,400)
        self.assertEqual(self.submit().status_code,400)
        self.assertEqual(len(self.soup('/').select('main .treatment-card--card')),3)

    def test_homepage_treatment_selection_survives_edit_and_can_be_empty(self):
        selected=next(r for r in self.base['records'] if r['section']=='treatments' and r.get('show_on_homepage'))
        edited={**selected,'title':'Updated homepage treatment'}
        edited.pop('show_on_homepage');edited.pop('homepage_order')
        self.state['drafts']=[edited]
        self.assertEqual(self.submit().status_code,200)
        self.assertIn('Updated homepage treatment',self.soup('/').get_text())
        self.base=self.client.get('/dashboard/content/').json()
        self.state={'drafts':[],'homepageTreatmentOrder':[]}
        self.assertEqual(self.submit().status_code,200)
        self.assertEqual(len(self.soup('/').select('main .treatment-card--card')),0)

    def test_title_generates_unique_treatment_slug_and_detail_url(self):
        template=next(r for r in self.base['records'] if r['section']=='treatments')
        self.state['drafts']=[{**template,'id':f'new-{i}','show_on_homepage':False,'title':"Café & Children's Dental Care!",'url':f'/ignored-{i}/','details':f'<p>Details for treatment {i}</p>'} for i in range(2)]
        response=self.submit()
        self.assertEqual(response.status_code,200)
        records=[r for r in response.json()['records'] if r['id'].startswith('new-')]
        self.assertEqual([r['slug'] for r in records],['cafe-and-childrens-dental-care','cafe-and-childrens-dental-care-2'])
        for i,record in enumerate(records):
            self.assertEqual(record['url'],f"/{record['slug']}/")
            self.assertContains(self.client.get(record['url']),f'Details for treatment {i}')
            self.assertRedirects(self.client.get(record['url'].rstrip('/')),record['url'],status_code=301)
            self.assertIsNotNone(self.soup('/services/').select_one(f'a[href="{record["url"]}"]'))

    def test_renaming_treatment_updates_url_and_redirects_old_url(self):
        record=self.edit('treatments',title='Modern Smile Care',details='<p>Matching treatment details</p>')
        old_url=record['url']
        self.assertEqual(self.submit().status_code,200)
        self.assertRedirects(self.client.get(old_url),'/modern-smile-care/',status_code=301)
        self.base=self.client.get('/dashboard/content/').json()
        current=next(r for r in self.base['records'] if r['id']==record['id'])
        self.state={'drafts':[{**current,'title':'Modern Smile Care Plus'}]}
        self.assertEqual(self.submit().status_code,200)
        self.assertRedirects(self.client.get('/modern-smile-care/'),'/modern-smile-care-plus/',status_code=301)
        self.assertRedirects(self.client.get(old_url),'/modern-smile-care-plus/',status_code=301)
        self.assertContains(self.client.get('/modern-smile-care-plus/'),'Matching treatment details')

    def test_treatment_slugs_avoid_page_and_topic_urls(self):
        template=next(r for r in self.base['records'] if r['section']=='treatments')
        self.state['drafts']=[{**template,'id':'new-services','show_on_homepage':False,'title':'Services','url':'/arbitrary/'}]
        response=self.submit()
        self.assertEqual(response.status_code,200)
        record=next(r for r in response.json()['records'] if r['id']=='new-services')
        self.assertEqual(record['url'],'/services-2/')

    def test_service_dropdown_latest_three_link_to_treatment_details(self):
        service=self.base['services'][0]
        template=next(r for r in self.base['records'] if r['section']=='treatments')
        additions=[{**template,'id':f'nav-treatment-{i}','title':f'Latest service treatment {i}','service':service['id'],'show_on_homepage':False,'url':f'/nav-treatment-{i}/','details':f'<p>Service treatment details {i}</p>'} for i in range(4)]
        self.state['drafts']=additions
        self.assertEqual(self.submit('/dashboard/content/').status_code,200)
        self.assertNotIn('Latest service treatment',self.soup('/').select_one('.doctor-nav--serviceGrid').text)
        self.base=self.client.get('/dashboard/content/').json()
        self.assertEqual(self.submit().status_code,200)
        nav=self.soup('/').select_one('.doctor-nav--serviceGrid > li')
        links=nav.select('.doctor-nav--treatmentList a')
        self.assertEqual([a.text for a in links],[f'Latest service treatment {i}' for i in [3,2,1]])
        for link,i in zip(links,[3,2,1]):
            self.assertContains(self.client.get(link['href']),f'Service treatment details {i}')
        self.base=self.client.get('/dashboard/content/').json()
        oldest=next(r for r in self.base['records'] if r['id']=='nav-treatment-0')
        self.state={'drafts':[{**oldest,'title':'Edited oldest treatment'}]}
        self.assertEqual(self.submit().status_code,200)
        nav=self.soup('/services/').select_one('.doctor-nav--serviceGrid > li')
        self.assertNotIn('Edited oldest treatment',nav.text)
        self.assertEqual(len(nav.select('.doctor-nav--treatmentList a')),3)

    def test_service_dropdown_without_publication_uses_real_records(self):
        soup=self.soup('/')
        services=soup.select('.doctor-nav--serviceGrid > li')
        cosmetic=next(card for card in services if card.select_one('.doctor-nav--serviceTitle').text=='Cosmetic dentistry')
        links=cosmetic.select('.doctor-nav--treatmentList a')
        self.assertEqual([a['href'] for a in links],['/veneers/','/teeth-whitening/','/gum-reshaping/'])
        self.assertTrue(all(len(card.select('.doctor-nav--treatmentList a'))<=3 for card in services))

    def test_treatment_dropdown_shows_maximum_six_services(self):
        self.state['services']=[{'id':f'extra-service-{i}','name':f'Extra service {i}','treatments':[]} for i in range(3)]
        self.assertEqual(self.submit().status_code,200)
        cards=self.soup('/').select('.doctor-nav--serviceGrid > li')
        self.assertEqual(len(cards),6)
        self.assertEqual([card.select_one('.doctor-nav--serviceTitle').text for card in cards],[service['name'] for service in self.base['services'][:6]])
        self.assertNotIn('Extra service',self.soup('/services/').select_one('.doctor-nav--serviceGrid').text)

    def test_article_image_is_shown_in_hero_and_listing_card(self):
        article=self.edit('articles',image='/media/gallery/article-thumb.webp',details='<h2>Article heading</h2><p>Article body remains visible.</p>')
        self.assertEqual(self.submit().status_code,200)
        detail=self.soup(article['url'])
        self.assertIsNone(detail.select_one('main .article-hero'))
        self.assertEqual(detail.select_one('main .page-intro-photo')['src'], article['image'])
        self.assertIn('Article body remains visible.',detail.select_one('.prose').text)
        card=self.soup('/blog/').select_one(f'a.blog-card[href="{article["url"]}"]')
        self.assertEqual(card.img['src'],article['image'])

    def test_new_article_hero_uses_saved_image(self):
        original=next(r for r in self.base['records'] if r['section']=='articles')
        article={**original,'id':'new-article-no-hero','title':'New article without hero','url':'/new-article-no-hero/','image':'/media/gallery/new-article-thumb.webp','details':'<p>New article body.</p>'}
        self.state['drafts']=[article]
        self.assertEqual(self.submit().status_code,200)
        detail=self.soup(article['url'])
        self.assertIsNone(detail.select_one('main .article-hero'))
        self.assertEqual(detail.select_one('main .page-intro-photo')['src'], article['image'])
        self.assertIsNotNone(self.soup('/blog/').select_one(f'a.blog-card[href="{article["url"]}"] img'))

    def test_treatment_hero_uses_published_image(self):
        treatment = self.edit('treatments', image='/media/gallery/treatment-hero.webp', image_alt='Treatment photo')
        self.assertEqual(self.submit().status_code, 200)
        hero = self.soup(treatment['url']).select_one('main .page-intro-photo')
        self.assertEqual(hero['src'], treatment['image'])
        self.assertEqual(hero['alt'], 'Treatment photo')

    def test_initial_article_details_have_no_thumbnail(self):
        for article in [r for r in self.base['records'] if r['section']=='articles']:
            if article['url'].startswith('/category/'):
                continue
            self.assertIsNone(self.soup(article['url']).select_one('main .article-hero'))

    def test_treatment_service_filter_uses_published_catalog_and_assignments(self):
        self.state['services']=[{'id':'new-service-filter','name':'New service filter','treatments':[]}]
        treatment=self.edit('treatments',service='new-service-filter',short_details='Searchable treatment summary')
        response=self.submit()
        self.assertEqual(response.status_code,200)
        published=next(r for r in response.json()['records'] if r['id']==treatment['id'])
        soup=self.soup('/services/')
        self.assertIsNotNone(soup.select_one('[data-treatment-search]'))
        self.assertEqual(soup.select_one('[data-treatment-service] option[value="new-service-filter"]').text,'New service filter')
        card=soup.select_one(f'a.treatment-card--card[href="{published["url"]}"]')
        self.assertEqual(card['data-service'],'new-service-filter')
        self.assertIn('Searchable treatment summary',card['data-search'])
        self.assertIn('New service filter',card['data-search'])

    def test_initial_treatment_service_filter_has_seed_assignments(self):
        soup=self.soup('/services/')
        self.assertEqual(len(soup.select('[data-treatment-service] option')),len(self.base['services'])+1)
        self.assertEqual(soup.select_one('a[href="/teeth-whitening/"].treatment-card--card')['data-service'],'cosmetic_dentistry')
        self.assertIsNone(self.soup('/').select_one('[data-treatment-search]'))

    def test_service_filter_uses_dashboard_changes_without_publishing(self):
        original, removed = self.base['services'][:2]
        self.state.update({
            'services': [{'id': 'new-care', 'name': 'New & gentle care', 'treatments': []}],
            'serviceEdits': {original['id']: {**original, 'name': 'Renamed care'}},
            'deletedServices': [removed['id']],
            'serviceOrder': ['new-care', original['id']],
        })
        response = self.submit('/dashboard/content/')
        self.assertEqual(response.status_code, 200)
        # No publication step: public options must match the saved dashboard catalog.
        client = Client()
        response = client.get('/api/services/')
        self.assertEqual(response.status_code, 200)
        services = response.json()['services']
        self.assertEqual(services[:2], [
            {'id': 'new-care', 'name': 'New & gentle care'},
            {'id': original['id'], 'name': 'Renamed care'},
        ])
        self.assertNotIn(removed['id'], [s['id'] for s in services])
        self.assertTrue(all(set(s) == {'id', 'name'} for s in services))
        soup = BeautifulSoup(client.get('/services/').content, 'html.parser')
        self.assertEqual([(o['value'], o.text) for o in soup.select('[data-treatment-service] option')],
                         [('', 'All services')] + [(s['id'], s['name']) for s in services])
        self.assertIn('no-store', response['Cache-Control'])

    def test_service_filter_all_services_removed(self):
        self.state['deletedServices'] = [s['id'] for s in self.base['services']]
        self.assertEqual(self.submit('/dashboard/content/').status_code, 200)
        self.assertEqual(Client().get('/api/services/').json(), {'services': []})
        self.assertEqual(len(self.soup('/services/').select('[data-treatment-service] option')), 1)

    def test_treatment_comparison_images_publish_and_can_be_removed(self):
        record = self.edit('treatments', before_image='/media/gallery/before.webp', after_image='/media/gallery/after.webp')
        self.assertEqual(self.submit().status_code, 200)
        comparison = self.soup(record['url']).select_one('[data-treatment-comparison]')
        self.assertIsNotNone(comparison)
        self.assertEqual(comparison.select_one('.smile-comparison--before img')['src'], record['before_image'])
        self.assertEqual(comparison.select_one('.smile-comparison--after')['src'], record['after_image'])
        self.assertIsNotNone(comparison.select_one('[data-comparison] input[type="range"]'))
        self.assertIn('related-section', comparison.find_next_sibling().get('class', []))
        self.base = self.client.get('/dashboard/content/').json()
        record['before_image'] = ''
        self.state['drafts'] = [record]
        self.assertEqual(self.submit().status_code, 200)
        self.assertIsNone(self.soup(record['url']).select_one('[data-treatment-comparison]'))

    def test_treatment_comparison_rejects_unsafe_image_urls(self):
        self.edit('treatments', before_image='javascript:alert(1)', after_image='/media/gallery/after.webp')
        self.assertEqual(self.submit().status_code, 400)

    def test_branch_schedule_photo_and_buttons_publish(self):
        self.edit('locations', image='/media/gallery/branch.webp', photo_alt='Branch reception', saturday_status='open', saturday_open='10:00', saturday_close='20:00', friday_status='closed', booking_label='Reserve a visit', booking_url='/appointment/?branch=chandgaon', directions_label='Find our clinic', directions_url='https://maps.google.com/?q=clinic')
        self.assertNotContains(self.client.get('/contact/'), 'Reserve a visit')
        self.assertEqual(self.submit().status_code, 200)
        card = self.soup('/contact/').select_one('.location-card')
        self.assertEqual(card.select_one('img')['src'], '/media/gallery/branch.webp')
        self.assertEqual(card.select_one('img')['alt'], 'Branch reception')
        self.assertIn('10:00 AM – 8:00 PM', card.text)
        self.assertIn('FridayClosed', card.get_text('', strip=True))
        self.assertEqual(card.select_one('.location-booking')['href'], '/appointment/?branch=chandgaon')
        self.assertIn('Reserve a visit', card.text)
        self.assertEqual(len(card.select('.location-links a')), 2)

    def test_invalid_branch_schedule_and_links_are_rejected(self):
        record = self.edit('locations', saturday_status='open', saturday_open='25:00', saturday_close='20:00')
        self.assertEqual(self.submit().status_code, 400)
        record.update(saturday_open='10:00', booking_url='javascript:alert(1)')
        self.assertEqual(self.submit().status_code, 400)

    def test_homepage_branches_are_selected_ordered_and_limited_to_two(self):
        locations = [deepcopy(r) for r in self.base['records'] if r['section'] == 'locations']
        first, second = locations[:2]
        first.update(show_on_homepage=True, homepage_order=3)
        second.update(show_on_homepage=True, homepage_order=2)
        third = {**first, 'id': 'third-branch', 'title': 'Third branch', 'homepage_order': 1}
        self.state['drafts'] = [first, second, third]
        self.assertEqual(self.submit().status_code, 200)
        home = self.soup('/')
        self.assertEqual([node.text for node in home.select('.locations-grid .location-card h3')], [third['title'], second['title']])
        self.assertEqual(home.select_one('.hero--location a')['href'], '#locations')
        self.assertIn('Third', home.select_one('.hero--location').text)
        self.assertNotIn(first['title'].removesuffix(' branch'), home.select_one('.hero--location').text)
        self.assertEqual(len(self.soup('/contact/').select('.locations-grid .location-card')), 3)
        self.base = self.client.get('/dashboard/content/').json()
        self.state['drafts'] = [{**record, 'show_on_homepage': False} for record in (first, second, third)]
        self.assertEqual(self.submit().status_code, 200)
        home = self.soup('/')
        self.assertIsNone(home.select_one('.hero--location'))
        self.assertIsNone(home.select_one('#locations'))
        self.assertEqual(len(self.soup('/contact/').select('.locations-grid .location-card')), 3)

    def test_moving_one_branch_to_first_shifts_the_existing_branch(self):
        branches = sorted((r for r in self.base['records'] if r['section'] == 'locations'), key=lambda r: r['order'])
        moved = deepcopy(branches[1])
        moved.update(homepage_order=1, order=1, show_on_homepage=True)
        self.state['drafts'] = [moved]
        saved = self.submit('/dashboard/content/')
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.submit(revision=saved.json()['revision']).status_code, 200)
        for route in ('/', '/contact/'):
            titles = [node.text for node in self.soup(route).select('.locations-grid .location-card h3')]
            self.assertEqual(titles[:2], [branches[1]['title'], branches[0]['title']])
        published = self.client.get('/dashboard/content/').json()['records']
        locations = [r for r in published if r['section'] == 'locations']
        self.assertEqual(sorted(r['homepage_order'] for r in locations), [1, 2])
        self.assertEqual(sorted(r['order'] for r in locations), [1, 2])
