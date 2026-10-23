from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change_form.html',
            success_url=reverse_lazy('accounts:password_change_done'),
        ),
        name='password_change',
    ),
    path(
        'password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html',
        ),
        name='password_change_done',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    # Legacy server-rendered admin screens stay available under their own
    # prefix; /admin-dashboard remains owned by the Next.js frontend.
    path('django-admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('django-admin/users/', views.admin_users_view, name='admin_users'),
    path('django-admin/users/<int:user_id>/', views.admin_user_detail_view, name='admin_user_detail'),
    path('django-admin/users/<int:user_id>/toggle-status/', views.admin_user_toggle_status_view, name='admin_user_toggle_status'),
    path('django-admin/users/<int:user_id>/change-role/', views.admin_user_change_role_view, name='admin_user_change_role'),
    path('django-admin/items/', views.admin_items_view, name='admin_items'),
    path('django-admin/claims/', views.admin_claims_view, name='admin_claims'),
    path('django-admin/categories/', views.admin_categories_view, name='admin_categories'),
    path('django-admin/categories/add/', views.admin_category_create_view, name='admin_category_create'),
    path('django-admin/categories/<int:pk>/edit/', views.admin_category_edit_view, name='admin_category_edit'),
    path('django-admin/categories/<int:pk>/delete/', views.admin_category_delete_view, name='admin_category_delete'),
    path('django-admin/matches/', views.admin_matches_view, name='admin_matches'),
    path('django-admin/matches/<int:match_id>/confirm/', views.admin_match_confirm_view, name='admin_match_confirm'),
    path('django-admin/matches/<int:match_id>/dismiss/', views.admin_match_dismiss_view, name='admin_match_dismiss'),
    path('django-admin/notifications/', views.admin_notifications_view, name='admin_notifications'),
]
