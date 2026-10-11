from django.urls import include, path

urlpatterns = [path('', include('dental_family.urls'))]
handler404 = 'dental_family.views.not_found'
handler500 = 'dental_family.views.server_error'
