from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='list'),
    path('<int:notification_id>/', views.notification_detail_view, name='detail'),
    path('<int:notification_id>/read/', views.mark_as_read_view, name='mark_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
    path('<int:notification_id>/delete/', views.delete_notification_view, name='delete'),
]
