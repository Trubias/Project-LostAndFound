from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('api/', views.api_items_view, name='api_items'),
    path('', views.item_list_view, name='item_list'),
    path('lost/', views.lost_items_view, name='lost_items'),
    path('found/', views.found_items_view, name='found_items'),
    path('<int:pk>/', views.item_detail_view, name='item_detail'),

    path('report/lost/', views.report_lost_view, name='report_lost'),
    path('report/found/', views.report_found_view, name='report_found'),
    path('<int:pk>/report/', views.report_item_concern_view, name='report_concern'),
    path('my-reports/', views.my_items_view, name='my_items'),
    path('<int:pk>/edit/', views.edit_item_view, name='edit_item'),
    path('<int:pk>/archive/', views.archive_item_view, name='archive_item'),
    path('<int:pk>/restore/', views.restore_item_view, name='restore_item'),
]

