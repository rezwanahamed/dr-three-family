from django.urls import path, re_path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'dental_family'
urlpatterns = [
    path('dashboard/login/', views.DashboardLoginView.as_view(), name='login'),
    path('dashboard/logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/upload-image/', views.upload_image, name='upload-image'),
    path('dashboard/content/', views.dashboard_content, name='dashboard-content'),
    path('dashboard/publish/', views.publish_content, name='publish-content'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard', views.legacy_redirect, {'destination': '/dashboard/'}),
] + [
    path(route.lstrip('/'), views.page, {'route': route}, name='home' if route == '/' else route.strip('/').replace('/', '-'))
    for route in views.ROUTES
]
for filename in ['robots.txt', 'sitemap.xml', 'icon.svg', 'favicon.ico']:
    urlpatterns.append(path(filename, views.metadata_file, {'filename': filename}))

for old, destination in {
    'price-guide': '/pricing-guide-2/', 'financing': '/financing-2/',
    'oral-surgery': '/advanced_oral_surgery/', 'edit': '/',
    'elementor-page-2017': '/', 'metform-form/contact-form-new': '/contact/',
}.items():
    urlpatterns.append(re_path(r'^' + old + r'/?$', views.legacy_redirect, {'destination': destination}))
urlpatterns += [
    re_path(r'^metform-form/[^/]+/?$', views.legacy_redirect, {'destination': '/appointment/'}),
    re_path(r'^author/[^/]+/?$', views.legacy_redirect, {'destination': '/blog/'}),
    # Return the branded page even during DEBUG=True local development.
    re_path(r'^(?!static(?:/|$))(?P<unmatched_path>.*)$', views.missing_page, name='not-found'),
]
