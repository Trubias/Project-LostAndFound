from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/users/', views.admin_users_view, name='admin_users'),
    path('admin-dashboard/users/<int:user_id>/', views.admin_user_detail_view, name='admin_user_detail'),
    path('admin-dashboard/users/<int:user_id>/toggle-status/', views.admin_user_toggle_status_view, name='admin_user_toggle_status'),
    path('admin-dashboard/users/<int:user_id>/change-role/', views.admin_user_change_role_view, name='admin_user_change_role'),
    path('admin-dashboard/items/', views.admin_items_view, name='admin_items'),
    path('admin-dashboard/claims/', views.admin_claims_view, name='admin_claims'),
    path('admin-dashboard/categories/', views.admin_categories_view, name='admin_categories'),
    path('admin-dashboard/categories/add/', views.admin_category_create_view, name='admin_category_create'),
    path('admin-dashboard/categories/<int:pk>/edit/', views.admin_category_edit_view, name='admin_category_edit'),
    path('admin-dashboard/categories/<int:pk>/delete/', views.admin_category_delete_view, name='admin_category_delete'),
    # Sprint 6
    path('admin-dashboard/matches/', views.admin_matches_view, name='admin_matches'),
    path('admin-dashboard/matches/<int:match_id>/confirm/', views.admin_match_confirm_view, name='admin_match_confirm'),
    path('admin-dashboard/matches/<int:match_id>/dismiss/', views.admin_match_dismiss_view, name='admin_match_dismiss'),
    path('admin-dashboard/notifications/', views.admin_notifications_view, name='admin_notifications'),
    path('profile/', views.profile_view, name='profile'),
]
