from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from .forms import RegisterForm, ProfileUpdateForm
from .models import Profile


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
    return render(request, 'dashboard/user_dashboard.html', {
        'user': request.user,
    })


# ─────────────────────────────────────────────
# Admin Dashboard
# ─────────────────────────────────────────────

@admin_required
def admin_dashboard_view(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': Profile.ROLE_ADMIN}
    )
    total_users = User.objects.filter(
        Q(profile__role=Profile.ROLE_USER) | Q(is_superuser=False)
    ).distinct().count()

    # Count admins: superusers + profile role = ADMIN
    admin_users = User.objects.filter(
        Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN)
    ).distinct()
    total_admins = admin_users.count()

    # True regular users (not admins)
    total_regular_users = User.objects.exclude(
        Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN)
    ).count()

    context = {
        'user': request.user,
        'profile': profile,
        'total_users': User.objects.count(),
        'total_admins': total_admins,
        'total_regular_users': total_regular_users,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


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
