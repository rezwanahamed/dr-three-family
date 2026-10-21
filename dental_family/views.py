import json
from io import BytesIO
from uuid import uuid4
import warnings
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView, PasswordResetView
from django.views.decorators.cache import never_cache
from .forms import DashboardAuthenticationForm, DashboardPasswordResetForm, reset_expiry_label
from django.urls import reverse_lazy

ROOT = Path(__file__).resolve().parent.parent
ROUTES = json.loads((ROOT / 'routes.json').read_text(encoding='utf-8'))


@never_cache
def public_services(request):
    from .models import WebsiteWorkspace
    from .content import available_services
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    services = available_services(workspace.published if workspace else {}, workspace.draft if workspace else {})
    return JsonResponse({'services': [{'id': s['id'], 'name': s['name']} for s in services]})


def page(request, route='/'):
    from .models import WebsiteWorkspace
    from .public_content import managed_html
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    published = workspace.published if workspace else {}
    info = ROUTES.get(route)
    if route == '/services/':
        from .content import available_services, seeds
        services = available_services(published, workspace.draft if workspace else {})
        return HttpResponse(managed_html(info['template'], request, route, published or seeds(), filter_services=services))
    if route in {'/financing-2/', '/simple-ways-to-pay/'}:
        from .content import seeds
        return HttpResponse(managed_html(ROUTES['/financing-2/']['template'], request, route, published or seeds()))
    if route in {'/pricing-guide-2/', '/a-little-clarity-on-costs/'}:
        from .content import seeds
        return HttpResponse(managed_html(ROUTES['/pricing-guide-2/']['template'], request, route, published or seeds()))
    if published:
        alias = next((r for r in published['records'] if r['section']=='treatments' and route in r.get('url_aliases',[])),None)
        if alias:
            return redirect(alias['url'], permanent=True)
        record = next((r for r in published['records'] if r['url']==route and r['section'] in {'pages','treatments','articles'}), None)
        topic = next((topic for topic in published['topics'] if topic['url']==route), None)
        if info and route.startswith('/faqs') and not topic:
            return not_found(request)
        if not info and topic:
            info = {'template': ROUTES['/faqs-dental-braces/']['template']}
        elif not info and record:
            example = '/clear_aligner/' if record['section']=='treatments' else '/9-signs-that-your-child-should-see-a-padiatric-dentist/' if record['section']=='articles' else '/privacy-policy/'
            info = {'template': ROUTES[example]['template']}
        if info and not record and not topic:
            return not_found(request)
        if info:
            return HttpResponse(managed_html(info['template'], request, route, published, route not in ROUTES))
    if info is None:
        raise Http404('Page not found')
    from .content import seeds
    seed_data = seeds()
    if any(r['section'] in {'treatments', 'articles'} and r['url']==route for r in seed_data['records']):
        return HttpResponse(managed_html(info['template'], request, route, seed_data))
    if route in {'/gallery/','/services/','/contact/','/','/appointment/','/about-us/','/our-doctors/'}:
        from .content import seeds
        return HttpResponse(managed_html(info['template'], request, route, seeds()))
    from django.template.loader import render_to_string
    from .content import seeds
    from .public_content import treatment_navigation_html
    return HttpResponse(treatment_navigation_html(render_to_string(info['template'], request=request), seeds()))


def legacy_redirect(request, destination, **kwargs):
    return redirect(destination, permanent=True)


def metadata_file(request, filename):
    types = {'robots.txt': 'text/plain', 'sitemap.xml': 'application/xml',
             'icon.svg': 'image/svg+xml', 'favicon.ico': 'image/x-icon'}
    if filename not in types:
        raise Http404
    if filename == 'sitemap.xml':
        from .models import WebsiteWorkspace
        from xml.etree.ElementTree import Element, SubElement, tostring
        workspace = WebsiteWorkspace.objects.filter(pk=1).first()
        if workspace and workspace.published:
            root = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
            routes = {r['url'] for r in workspace.published['records'] if r['section'] in {'pages','treatments','articles'} and not r.get('robots','').startswith('noindex')} | {t['url'] for t in workspace.published['topics']}
            for route in sorted(routes):
                SubElement(SubElement(root,'url'),'loc').text = request.build_absolute_uri(route)
            return HttpResponse(tostring(root, encoding='utf-8', xml_declaration=True), content_type=types[filename])
    return FileResponse((ROOT / 'static/dental_family' / filename).open('rb'), content_type=types[filename])


def not_found(request, exception=None):
    return render(request, 'dental_family/pages/404.html', status=404)


def missing_page(request, unmatched_path=''):
    # The fallback also matches slashless URLs, so preserve their canonical redirect.
    canonical = '/' + unmatched_path.rstrip('/') + '/'
    if not request.path.endswith('/') and canonical in ROUTES:
        return redirect(canonical, permanent=True)
    from .models import WebsiteWorkspace
    workspace = WebsiteWorkspace.objects.filter(pk=1).first()
    if workspace and workspace.published:
        route = '/' + unmatched_path.strip('/') + '/'
        alias = next((r for r in workspace.published['records'] if r['section']=='treatments' and route in r.get('url_aliases',[])),None)
        if alias:
            return redirect(alias['url'], permanent=True)
        if any(record['url']==route and record['section'] in {'pages','treatments','articles'} for record in workspace.published['records']) or any(topic['url']==route for topic in workspace.published['topics']):
            if request.path != route:
                return redirect(route, permanent=True)
            return page(request, route)
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
    """Staff dashboard with shared database drafts and explicit publication."""
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


def staff_api(request):
    user = getattr(request, 'user', None)
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


def workspace_response(workspace):
    from .content import seeds
    from .content import gallery_snapshot
    base = gallery_snapshot(workspace.published or seeds())
    gallery = {r['id']:r.get('gallery_category') for r in seeds()['records'] if r['section']=='gallery'}
    records = [{**r,'gallery_category':r.get('gallery_category') or gallery.get(r['id']) or 'Our space'} if r['section']=='gallery' else r for r in base['records']]
    from .pricing import pricing_catalog, resolve_service_id
    records = [{**r,'pricing_service_id':resolve_service_id(r,base)} if r['section']=='prices' else r for r in records]
    return {'pricing_catalog':pricing_catalog(base,workspace.draft), 'improvement_options': base.get('improvement_options', []), 'records': records, 'topics': base['topics'], 'services': base['services'], 'contact_details':base['contact_details'], 'price_services': base.get('price_services',[]), 'gallery_sections': base.get('gallery_sections',['Our space','Our team','Our technology']),
            'state': workspace.draft, 'revision': workspace.revision,
            'published_settings': base.get('settings', {}),
            'published': bool(workspace.published)}


@never_cache
@csrf_protect
def dashboard_content(request):
    from django.db import transaction
    from django.core.exceptions import ValidationError
    from .models import WebsiteWorkspace
    from .content import validate_state
    if not staff_api(request):
        return JsonResponse({'error': 'Staff access is required.'}, status=403)
    if request.method not in {'GET','PUT'}:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
    with transaction.atomic():
        workspace, _ = WebsiteWorkspace.objects.get_or_create(pk=1)
        workspace = WebsiteWorkspace.objects.select_for_update().get(pk=1)
        if request.method == 'GET':
            return JsonResponse(workspace_response(workspace))
        try:
            payload = json.loads(request.body)
            if payload.get('revision') != workspace.revision:
                return JsonResponse({'error': 'Another session changed this workspace. Reload before saving.', 'conflict': True}, status=409)
            workspace.draft = validate_state(payload.get('state'), draft=True, published=workspace.published)
        except (ValueError, TypeError, AttributeError, ValidationError) as error:
            return JsonResponse({'error': str(error)}, status=400)
        workspace.revision += 1
        workspace.save()
        return JsonResponse({'revision': workspace.revision})


@require_POST
@csrf_protect
def publish_content(request):
    from django.db import transaction
    from django.core.exceptions import ValidationError
    from .models import WebsiteWorkspace
    from .content import validate_state, snapshot
    if not staff_api(request):
        return JsonResponse({'error':'Staff access is required.'}, status=403)
    with transaction.atomic():
        workspace, _ = WebsiteWorkspace.objects.get_or_create(pk=1)
        workspace = WebsiteWorkspace.objects.select_for_update().get(pk=1)
        try:
            payload = json.loads(request.body)
            if payload.get('revision') != workspace.revision:
                return JsonResponse({'error':'Another session changed this workspace. Reload before publishing.','conflict':True}, status=409)
            state = validate_state(payload.get('state'), published=workspace.published)
            workspace.published = snapshot(workspace.published, state)
        except (ValueError, TypeError, KeyError, AttributeError, ValidationError) as error:
            return JsonResponse({'error':str(error)}, status=400)
        workspace.draft = {'drafts': [], 'deletions': [], 'activity': state.get('activity', []), 'settings': state.get('settings', {})}
        workspace.revision += 1
        workspace.save()
        return JsonResponse(workspace_response(workspace))


class DashboardPasswordResetView(PasswordResetView):
    template_name = 'dental_family/dashboard/password_reset_form.html'
    email_template_name = 'dental_family/dashboard/password_reset_email.txt'
    subject_template_name = 'dental_family/dashboard/password_reset_subject.txt'
    form_class = DashboardPasswordResetForm
    success_url = reverse_lazy('dental_family:password-reset-done')

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['reset_expiry']=reset_expiry_label()
        return context

    def form_valid(self, form):
        from smtplib import SMTPException
        import logging
        try:
            return super().form_valid(form)
        except (SMTPException, OSError, ValueError) as error:
            logging.getLogger(__name__).error('Password-reset email delivery failed (%s). Check SMTP configuration and network connectivity.', type(error).__name__)
            form.add_error(None, 'We could not send the reset email right now. Please try again later or contact your administrator.')
            return self.form_invalid(form)
