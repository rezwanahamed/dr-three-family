from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [path('', include('dental_family.urls'))]
handler404 = 'dental_family.views.not_found'
handler500 = 'dental_family.views.server_error'
