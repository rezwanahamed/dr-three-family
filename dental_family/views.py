import json
from io import BytesIO
from uuid import uuid4
import warnings
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView
from django.views.decorators.cache import never_cache
from .forms import DashboardAuthenticationForm

ROOT = Path(__file__).resolve().parent.parent
ROUTES = json.loads((ROOT / 'routes.json').read_text(encoding='utf-8'))


def page(request, route='/'):
    info = ROUTES.get(route)
    if info is None:
        raise Http404('Page not found')
    return render(request, info['template'])


def legacy_redirect(request, destination, **kwargs):
    return redirect(destination, permanent=True)


def metadata_file(request, filename):
    types = {'robots.txt': 'text/plain', 'sitemap.xml': 'application/xml',
             'icon.svg': 'image/svg+xml', 'favicon.ico': 'image/x-icon'}
    if filename not in types:
        raise Http404
    return FileResponse((ROOT / 'static/dental_family' / filename).open('rb'), content_type=types[filename])


def not_found(request, exception=None):
    return render(request, 'dental_family/pages/404.html', status=404)


def missing_page(request, unmatched_path=''):
    # The fallback also matches slashless URLs, so preserve their canonical redirect.
    canonical = '/' + unmatched_path.rstrip('/') + '/'
    if not request.path.endswith('/') and canonical in ROUTES:
        return redirect(canonical, permanent=True)
    return not_found(request)


def server_error(request):
    return render(request, 'dental_family/pages/500.html', status=500)


class DashboardLoginView(LoginView):
    template_name = 'dental_family/dashboard/login.html'
    authentication_form = DashboardAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(None if form.cleaned_data['remember'] else 0)
        return response


@never_cache
@ensure_csrf_cookie
@user_passes_test(lambda user: user.is_active and user.is_staff)
def dashboard(request):
    """Staff dashboard; content drafts remain browser-local."""
    return render(request, 'dental_family/dashboard/index.html')


@require_POST
@csrf_protect
def upload_image(request):
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated and user.is_active and user.is_staff):
        return JsonResponse({'error': 'Staff access is required.'}, status=403)
    if len(request.FILES.getlist('image')) > 1:
        return JsonResponse({'error': 'Choose only one image.'}, status=400)
    upload = request.FILES.get('image')
    if not upload:
        return JsonResponse({'error': 'Choose an image to upload.'}, status=400)
    if upload.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'Images must be 10 MB or smaller.'}, status=400)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(upload) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Choose a JPEG, PNG, or WebP image.')
                if source.width * source.height > 40_000_000:
                    raise ValueError('Image resolution must be below 40 megapixels.')
                if getattr(source, 'is_animated', False):
                    raise ValueError('Choose a still image rather than an animation.')
                source.verify()
            upload.seek(0)
            with Image.open(upload) as source:
                image = ImageOps.exif_transpose(source)
                image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
                image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                output = BytesIO()
                image.save(output, format='WEBP', quality=85, method=6)
                width, height = image.size
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return JsonResponse({'error': 'This file is not a valid supported image.'}, status=400)
    filename = default_storage.save(f'gallery/{uuid4().hex}.webp', ContentFile(output.getvalue()))
    return JsonResponse({'url': default_storage.url(filename), 'filename': filename,
                         'width': width, 'height': height}, status=201)
