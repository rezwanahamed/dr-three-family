from django.urls import path, re_path
from . import views
from .appointments import appointment_booking
from .admin_accounts import admin_accounts
from django.contrib.auth.views import LogoutView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from .forms import DashboardSetPasswordForm

app_name = 'dental_family'
from .doctors import doctor_profile

urlpatterns = [
    path('our-doctors/<slug:slug>/', doctor_profile, name='doctor-profile'),
    path('api/appointment/', appointment_booking, name='appointment-booking'),
    path('dashboard/admins/', admin_accounts, name='admin-accounts'),
    path('api/services/', views.public_services, name='public-services'),
    path('simple-ways-to-pay/', views.page, {'route':'/simple-ways-to-pay/'}, name='payment-options'),
    path('simple-ways-to-pay', views.legacy_redirect, {'destination':'/simple-ways-to-pay/'}),
    path('a-little-clarity-on-costs/', views.page, {'route':'/a-little-clarity-on-costs/'}, name='price-guide-details'),
    path('a-little-clarity-on-costs', views.legacy_redirect, {'destination':'/a-little-clarity-on-costs/'}),
    path('dashboard/login/', views.DashboardLoginView.as_view(), name='login'),
    path('dashboard/forgot-password/', views.DashboardPasswordResetView.as_view(), name='password-reset'),
    path('dashboard/forgot-password/sent/', PasswordResetDoneView.as_view(template_name='dental_family/dashboard/password_reset_done.html'), name='password-reset-done'),
    path('dashboard/reset-password/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='dental_family/dashboard/password_reset_confirm.html', form_class=DashboardSetPasswordForm, success_url=reverse_lazy('dental_family:password-reset-complete')), name='password-reset-confirm'),
    path('dashboard/reset-password/complete/', PasswordResetCompleteView.as_view(template_name='dental_family/dashboard/password_reset_complete.html'), name='password-reset-complete'),
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
