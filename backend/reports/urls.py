from django.urls import path
from reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard_view, name='index'),
    path('items/export/', views.export_items_csv, name='export_items'),
    path('claims/export/', views.export_claims_csv, name='export_claims'),
    path('users/export/', views.export_users_csv, name='export_users'),
    path('categories/export/', views.export_categories_csv, name='export_categories'),
    path('matches/export/', views.export_matches_csv, name='export_matches'),
]
