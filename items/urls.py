from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('', views.item_list_view, name='item_list'),
    path('lost/', views.lost_items_view, name='lost_items'),
    path('found/', views.found_items_view, name='found_items'),
    path('<int:pk>/', views.item_detail_view, name='item_detail'),

    path('report/lost/', views.report_lost_view, name='report_lost'),
    path('report/found/', views.report_found_view, name='report_found'),
    path('my-reports/', views.my_items_view, name='my_items'),
    path('<int:pk>/edit/', views.edit_item_view, name='edit_item'),
    path('<int:pk>/archive/', views.archive_item_view, name='archive_item'),
    path('<int:pk>/restore/', views.restore_item_view, name='restore_item'),
    # Categories (Admin)
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/add/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),
]

