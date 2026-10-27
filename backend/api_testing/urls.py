from django.urls import path

from . import views

app_name = 'api_testing'

urlpatterns = [
    path('api/test-console/', views.console_view, name='console'),
    path('api/test-console/runs/', views.run_list_view, name='run_list'),
    path('api/test-console/runs/<int:run_id>/', views.run_detail_view, name='run_detail'),
    path('api/test-console/run/', views.start_run_view, name='start_run'),
]
