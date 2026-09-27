from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from .forms import RegisterForm, ProfileUpdateForm
from .models import Profile

# Lazy import to avoid circular issues — items app may not be ready at import time
def _get_item_model():
    from items.models import Item
    return Item


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_admin_user(user):
    """Return True if the user has ADMIN role or is a superuser."""
    if user.is_superuser:
        return True
    try:
        return user.profile.role == Profile.ROLE_ADMIN
    except Profile.DoesNotExist:
        return False


def admin_required(view_func):
    """Decorator: redirect to dashboard if user is not an admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access that page.')
            return redirect('accounts:login')
        if not is_admin_user(request.user):
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─────────────────────────────────────────────
# Home / Root Redirect
# ─────────────────────────────────────────────

def home_view(request):
    if request.user.is_authenticated:
        if is_admin_user(request.user):
            return redirect('accounts:admin_dashboard')
        return redirect('accounts:dashboard')
    return redirect('accounts:login')


# ─────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            # Profile is auto-created via signal with USER role
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('accounts:login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        if is_admin_user(request.user):
            return redirect('accounts:admin_dashboard')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if is_admin_user(user):
                return redirect('accounts:admin_dashboard')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


# ─────────────────────────────────────────────
# User Dashboard
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def dashboard_view(request):
    # Admins have their own separate dashboard and cannot access the user dashboard
    if is_admin_user(request.user):
        return redirect('accounts:admin_dashboard')

    # Item stats for this user
    Item = _get_item_model()
    my_items = Item.objects.filter(reporter=request.user)
    active_items = Item.objects.filter(status=Item.STATUS_ACTIVE).select_related('category', 'reporter')
    latest_lost_items = active_items.filter(item_type=Item.TYPE_LOST)[:4]
    latest_found_items = active_items.filter(item_type=Item.TYPE_FOUND)[:4]

    # Claim stats for this user (Sprint 4)
    from claims.models import Claim
    my_claims = Claim.objects.filter(claimant=request.user)

    # Notifications & Matches (Sprint 6)
    from notifications.models import Notification
    from matches.models import ItemMatch
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    possible_matches_count = ItemMatch.objects.filter(
        Q(lost_item__reporter=request.user) | Q(found_item__reporter=request.user),
        status=ItemMatch.STATUS_PENDING
    ).count()

    context = {
        'user': request.user,
        'my_active_count': my_items.filter(status=Item.STATUS_ACTIVE).count(),
        'my_archived_count': my_items.filter(status=Item.STATUS_ARCHIVED).count(),
        'my_lost_count': my_items.filter(item_type=Item.TYPE_LOST).count(),
        'my_found_count': my_items.filter(item_type=Item.TYPE_FOUND).count(),
        'latest_lost_items': latest_lost_items,
        'latest_found_items': latest_found_items,
        # Claim counts
        'my_claims_pending': my_claims.filter(status=Claim.STATUS_PENDING).count(),
        'my_claims_approved': my_claims.filter(status=Claim.STATUS_APPROVED).count(),
        'my_claims_rejected': my_claims.filter(status=Claim.STATUS_REJECTED).count(),
        'my_claims_total': my_claims.count(),
        # Notifications & Matches counts
        'unread_notifications_count': unread_notifications_count,
        'possible_matches_count': possible_matches_count,
    }
    return render(request, 'dashboard/user_dashboard.html', context)



# ─────────────────────────────────────────────
# Admin Views (Sprint 5)
# ─────────────────────────────────────────────
from .admin_views import (
    admin_dashboard_view,
    admin_users_view,
    admin_user_detail_view,
    admin_user_toggle_status_view,
    admin_user_change_role_view,
    admin_items_view,
    admin_claims_view,
    admin_categories_view,
    admin_category_create_view,
    admin_category_edit_view,
    admin_category_delete_view,
    # Sprint 6
    admin_matches_view,
    admin_match_confirm_view,
    admin_match_dismiss_view,
    admin_notifications_view,
)


# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def profile_view(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': Profile.ROLE_USER}
    )

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Update User fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            # Save profile (phone, profile_image) — role NOT editable
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(
            instance=profile,
            initial={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        )

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
    })
