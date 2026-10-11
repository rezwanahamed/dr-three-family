from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image
from django.contrib.auth import get_user_model


class ImageUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(username="upload-staff", is_staff=True)
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.directory.name, DEBUG=True)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.staff)
        self.client.get('/dashboard/')
        self.token = self.client.cookies['csrftoken'].value

    def upload(self, data, name='photo.jpg', token=True):
        return self.client.post('/dashboard/upload-image/',
            {'image': SimpleUploadedFile(name, data, content_type='image/jpeg')},
            **({'HTTP_X_CSRFTOKEN': self.token} if token else {}))

    def test_valid_image_stored_as_resized_webp(self):
        data = BytesIO()
        Image.new('RGB', (3000, 1500), 'purple').save(data, 'JPEG')
        response = self.upload(data.getvalue(), '../../photo.jpg')
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertTrue(result['filename'].startswith('gallery/'))
        self.assertEqual((result['width'], result['height']), (2400, 1200))
        with Image.open(Path(self.directory.name) / result['filename']) as image:
            self.assertEqual(image.format, 'WEBP')
            self.assertEqual(image.size, (2400, 1200))
        self.assertTrue(result['url'].startswith('/media/gallery/'))

    def test_exif_rotation_and_metadata_removed(self):
        data = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (60, 30), 'purple').save(data, 'JPEG', exif=exif)
        result = self.upload(data.getvalue()).json()
        self.assertEqual((result['width'], result['height']), (30, 60))
        with Image.open(Path(self.directory.name) / result['filename']) as image:
            self.assertFalse(image.getexif())

    def test_invalid_oversized_and_unsupported_files_rejected(self):
        self.assertEqual(self.upload(b'not an image').status_code, 400)
        self.assertEqual(self.upload(b'x' * (10 * 1024 * 1024 + 1)).status_code, 400)
        data = BytesIO()
        Image.new('RGB', (20, 20)).save(data, 'GIF')
        self.assertEqual(self.upload(data.getvalue(), 'image.gif').status_code, 400)
        self.assertEqual(list(Path(self.directory.name).rglob('*.webp')), [])

    def test_csrf_and_production_access_required(self):
        self.assertEqual(self.upload(b'image', token=False).status_code, 403)
        self.client.logout()
        self.client.get('/dashboard/login/')
        self.token = self.client.cookies['csrftoken'].value
        self.assertEqual(self.upload(b'image').status_code, 403)
        self.assertEqual(self.client.get('/dashboard/upload-image/').status_code, 405)

    def test_multiple_images_rejected_without_saving(self):
        response = self.client.post('/dashboard/upload-image/', {'image': [
            SimpleUploadedFile('one.png', b'one'),
            SimpleUploadedFile('two.png', b'two'),
        ]}, HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Choose only one image.')
        self.assertEqual(list(Path(self.directory.name).rglob('*.webp')), [])


class DashboardAuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user('staff-editor', email='staff@example.test', password='test-pass-not-real', is_staff=True)
        cls.visitor = get_user_model().objects.create_user('visitor', email='visitor@example.test', password='test-pass-not-real')

    def test_dashboard_requires_login_and_staff(self):
        self.assertRedirects(self.client.get('/dashboard/'), '/dashboard/login/?next=/dashboard/')
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)
        self.assertEqual(self.client.post('/dashboard/upload-image/').status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])

    def test_login_bad_credentials_and_nonstaff_rejected(self):
        for email, password in [('staff@example.test', 'wrong'), ('visitor@example.test', 'test-pass-not-real')]:
            response = self.client.post('/dashboard/login/', {'email': email, 'password': password})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_safe_redirect_and_session_expiry(self):
        response = self.client.post('/dashboard/login/', {'email': 'staff@example.test', 'password': 'test-pass-not-real', 'next': 'https://external.example/'})
        self.assertRedirects(response, '/dashboard/')
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        response = self.client.post('/dashboard/login/', {'email': 'staff@example.test', 'password': 'test-pass-not-real', 'remember': 'on', 'next': '/dashboard/#articles'})
        self.assertEqual(response.url, '/dashboard/#articles')
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_login_and_logout_require_csrf_and_logout_requires_post(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/dashboard/login/', {'email': 'staff@example.test', 'password': 'test-pass-not-real'}).status_code, 403)
        client.get('/dashboard/login/')
        token = client.cookies['csrftoken'].value
        response = client.post('/dashboard/login/', {'email': 'staff@example.test', 'password': 'test-pass-not-real'}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get('/dashboard/logout/').status_code, 405)
        self.assertEqual(client.post('/dashboard/logout/').status_code, 403)
        token = client.cookies['csrftoken'].value
        response = client.post('/dashboard/logout/', HTTP_X_CSRFTOKEN=token)
        self.assertRedirects(response, '/dashboard/login/')
        self.assertNotIn('_auth_user_id', client.session)
        self.assertEqual(client.get('/dashboard/').status_code, 302)

    def test_email_is_case_insensitive_and_username_is_not_a_login(self):
        response = self.client.post('/dashboard/login/', {'email': ' STAFF@EXAMPLE.TEST ', 'password': 'test-pass-not-real'})
        self.assertRedirects(response, '/dashboard/')
        self.client.logout()
        response = self.client.post('/dashboard/login/', {'username': 'staff-editor', 'password': 'test-pass-not-real'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_duplicate_email_inactive_and_unknown_accounts_rejected(self):
        get_user_model().objects.create_user('duplicate', email='STAFF@example.test', password='another-pass', is_staff=True)
        response = self.client.post('/dashboard/login/', {'email': 'staff@example.test', 'password': 'test-pass-not-real'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.staff.is_active = False
        self.staff.email = 'inactive@example.test'
        self.staff.save()
        for email in ['inactive@example.test', 'unknown@example.test']:
            response = self.client.post('/dashboard/login/', {'email': email, 'password': 'test-pass-not-real'})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)
