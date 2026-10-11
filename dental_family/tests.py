from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from PIL import Image


class ImageUploadTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.directory.name, DEBUG=True)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.client = Client(enforce_csrf_checks=True)
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
        with override_settings(DEBUG=False):
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
