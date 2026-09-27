from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from accounts.models import Profile
from accounts.views import admin_required, is_admin_user
from items.models import Item, Category
from items.forms import CategoryForm
from claims.models import Claim
from notifications.models import Notification
from matches.models import ItemMatch


# ─────────────────────────────────────────────
# 1. Admin Dashboard View
# ─────────────────────────────────────────────

@admin_required
def admin_dashboard_view(request):
    """
    Main Admin Dashboard displaying real database statistics,
    quick actions, recent activity, and summary breakdowns.
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': Profile.ROLE_ADMIN}
    )

    # User statistics
    total_users = User.objects.count()
    admin_users_qs = User.objects.filter(
        Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN)
    ).distinct()
    total_admins = admin_users_qs.count()
    active_users = User.objects.filter(is_active=True).count()
    total_regular_users = User.objects.exclude(
        Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN)
    ).count()

    # Item statistics
    all_items = Item.objects.all()
    total_active_items = all_items.filter(status=Item.STATUS_ACTIVE).count()
    total_archived_items = all_items.filter(status=Item.STATUS_ARCHIVED).count()
    total_lost_items = all_items.filter(item_type=Item.TYPE_LOST).count()
    total_found_items = all_items.filter(item_type=Item.TYPE_FOUND).count()
    total_items = all_items.count()

    # Category statistics
    total_categories = Category.objects.count()

    # Claim statistics
    all_claims = Claim.objects.all()
    total_claims = all_claims.count()
    total_claims_pending = all_claims.filter(status=Claim.STATUS_PENDING).count()
    total_claims_approved = all_claims.filter(status=Claim.STATUS_APPROVED).count()
    total_claims_rejected = all_claims.filter(status=Claim.STATUS_REJECTED).count()
    total_claims_withdrawn = all_claims.filter(status=Claim.STATUS_WITHDRAWN).count()

    # Notification statistics (Sprint 6)
    all_notifications = Notification.objects.all()
    total_notifications = all_notifications.count()
    total_unread_notifications = all_notifications.filter(is_read=False).count()

    # Match statistics (Sprint 6)
    all_matches = ItemMatch.objects.all()
    total_matches = all_matches.count()
    total_matches_pending = all_matches.filter(status=ItemMatch.STATUS_PENDING).count()
    total_matches_confirmed = all_matches.filter(status=ItemMatch.STATUS_CONFIRMED).count()
    total_matches_dismissed = all_matches.filter(status=ItemMatch.STATUS_DISMISSED).count()

    # Summary calculations for progress bars / report summary
    lost_percent = int((total_lost_items / total_items * 100)) if total_items > 0 else 0
    found_percent = 100 - lost_percent if total_items > 0 else 0

    pending_claim_percent = int((total_claims_pending / total_claims * 100)) if total_claims > 0 else 0
    approved_claim_percent = int((total_claims_approved / total_claims * 100)) if total_claims > 0 else 0
    rejected_claim_percent = int((total_claims_rejected / total_claims * 100)) if total_claims > 0 else 0

    active_user_percent = int((active_users / total_users * 100)) if total_users > 0 else 0

    # Recent Activity aggregation (last ~10 items)
    activities = []

    # Recent user registrations
    for u in User.objects.order_by('-date_joined')[:6]:
        activities.append({
            'type': 'user_registration',
            'icon': 'bi-person-plus-fill',
            'color': 'primary',
            'title': f'New user registered: @{u.username}',
            'timestamp': u.date_joined,
            'url': f'/admin-dashboard/users/{u.pk}/',
            'detail': u.email or 'No email provided',
        })

    # Recent item reports
    for item in Item.objects.select_related('reporter').order_by('-created_at')[:6]:
        badge_color = 'warning' if item.is_lost() else 'success'
        activities.append({
            'type': 'item_report',
            'icon': 'bi-box-seam-fill',
            'color': badge_color,
            'title': f'Reported {item.get_item_type_display()}: "{item.title}"',
            'timestamp': item.created_at,
            'url': f'/items/{item.pk}/',
            'detail': f'Reported by @{item.reporter.username} in {item.location}',
        })

    # Recent claim submissions
    for claim in Claim.objects.select_related('claimant', 'item').order_by('-created_at')[:6]:
        activities.append({
            'type': 'claim_submitted',
            'icon': 'bi-hand-index-thumb-fill',
            'color': 'info',
            'title': f'Claim submitted for "{claim.item.title}"',
            'timestamp': claim.created_at,
            'url': f'/claims/{claim.pk}/',
            'detail': f'Claimant: @{claim.claimant.username}',
        })

    # Recent claim approvals / rejections
    for claim in Claim.objects.filter(status__in=[Claim.STATUS_APPROVED, Claim.STATUS_REJECTED], reviewed_at__isnull=False).select_related('claimant', 'item', 'reviewed_by').order_by('-reviewed_at')[:6]:
        is_appr = claim.status == Claim.STATUS_APPROVED
        activities.append({
            'type': 'claim_reviewed',
            'icon': 'bi-check-circle-fill' if is_appr else 'bi-x-circle-fill',
            'color': 'success' if is_appr else 'danger',
            'title': f'Claim {claim.get_status_display().lower()} for "{claim.item.title}"',
            'timestamp': claim.reviewed_at,
            'url': f'/claims/{claim.pk}/',
            'detail': f'Reviewed by @{claim.reviewed_by.username if claim.reviewed_by else "Admin"}',
        })

    # Sort combined activities by timestamp descending and take top 10
    activities.sort(key=lambda x: x['timestamp'] or timezone.now(), reverse=True)
    recent_activities = activities[:10]

    context = {
        'user': request.user,
        'profile': profile,
        # User stats
        'total_users': total_users,
        'total_admins': total_admins,
        'active_users': active_users,
        'total_regular_users': total_regular_users,
        'active_user_percent': active_user_percent,
        # Item stats
        'total_items': total_items,
        'total_active_items': total_active_items,
        'total_archived_items': total_archived_items,
        'total_lost_items': total_lost_items,
        'total_found_items': total_found_items,
        'lost_percent': lost_percent,
        'found_percent': found_percent,
        # Category stats
        'total_categories': total_categories,
        # Claim stats
        'total_claims': total_claims,
        'total_claims_pending': total_claims_pending,
        'total_claims_approved': total_claims_approved,
        'total_claims_rejected': total_claims_rejected,
        'total_claims_withdrawn': total_claims_withdrawn,
        'pending_claim_percent': pending_claim_percent,
        'approved_claim_percent': approved_claim_percent,
        'rejected_claim_percent': rejected_claim_percent,
        # Notification stats (Sprint 6)
        'total_notifications': total_notifications,
        'total_unread_notifications': total_unread_notifications,
        # Match stats (Sprint 6)
        'total_matches': total_matches,
        'total_matches_pending': total_matches_pending,
        'total_matches_confirmed': total_matches_confirmed,
        'total_matches_dismissed': total_matches_dismissed,
        # Activities
        'recent_activities': recent_activities,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


# ─────────────────────────────────────────────
# 2. User Management
# ─────────────────────────────────────────────

@admin_required
def admin_users_view(request):
    """
    List of all users with search, role and status filtering, and pagination.
    """
    users_qs = User.objects.select_related('profile').all().order_by('-date_joined')

    # Search: username, first_name, last_name, email
    q = request.GET.get('q', '').strip()
    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    # Filter by role: 'USER', 'ADMIN'
    role_filter = request.GET.get('role', '').strip().upper()
    if role_filter == 'ADMIN':
        users_qs = users_qs.filter(Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN))
    elif role_filter == 'USER':
        users_qs = users_qs.filter(profile__role=Profile.ROLE_USER, is_superuser=False)
    else:
        role_filter = ''

    # Filter by account status: 'active', 'inactive'
    status_filter = request.GET.get('status', '').strip().lower()
    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)
    else:
        status_filter = ''

    # Pagination: 10 per page
    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page')
    try:
        users_page = paginator.page(page_number)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)

    # Build querystring preserving filters (excluding page)
    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    querystring = get_params.urlencode()

    return render(request, 'admin_dashboard/users.html', {
        'users_page': users_page,
        'total_count': paginator.count,
        'q': q,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'querystring': querystring,
    })


@admin_required
def admin_user_detail_view(request, user_id):
    """
    Detailed inspection of a user's account, reports, claims, and actions.
    """
    target_user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)

    # User activity statistics
    reported_items = Item.objects.filter(reporter=target_user).select_related('category').order_by('-created_at')
    submitted_claims = Claim.objects.filter(claimant=target_user).select_related('item').order_by('-created_at')

    reports_count = reported_items.count()
    lost_reports_count = reported_items.filter(item_type=Item.TYPE_LOST).count()
    found_reports_count = reported_items.filter(item_type=Item.TYPE_FOUND).count()

    claims_count = submitted_claims.count()
    pending_claims_count = submitted_claims.filter(status=Claim.STATUS_PENDING).count()
    approved_claims_count = submitted_claims.filter(status=Claim.STATUS_APPROVED).count()
    rejected_claims_count = submitted_claims.filter(status=Claim.STATUS_REJECTED).count()

    return render(request, 'admin_dashboard/user_detail.html', {
        'target_user': target_user,
        'reports_count': reports_count,
        'lost_reports_count': lost_reports_count,
        'found_reports_count': found_reports_count,
        'claims_count': claims_count,
        'pending_claims_count': pending_claims_count,
        'approved_claims_count': approved_claims_count,
        'rejected_claims_count': rejected_claims_count,
        'recent_reports': reported_items[:5],
        'recent_claims': submitted_claims[:5],
        'is_self': target_user.pk == request.user.pk,
    })


@admin_required
def admin_user_toggle_status_view(request, user_id):
    """
    Activate or deactivate user account with confirmation.
    Prevents administrator from deactivating their own account.
    """
    target_user = get_object_or_404(User, pk=user_id)

    # Safety check: prevent deactivating own account
    if target_user.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own administrator account.')
        return redirect('accounts:admin_user_detail', user_id=target_user.pk)

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        action_verb = 'activated' if target_user.is_active else 'deactivated'
        messages.success(request, f'User account "@{target_user.username}" has been {action_verb}.')
        return redirect('accounts:admin_user_detail', user_id=target_user.pk)

    return render(request, 'admin_dashboard/confirm_user_status.html', {
        'target_user': target_user,
        'will_activate': not target_user.is_active,
    })


@admin_required
def admin_user_change_role_view(request, user_id):
    """
    Change user application role between USER and ADMIN with confirmation.
    Prevents self-demotion to avoid administrator lockout.
    """
    target_user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)

    # Safety check: prevent changing own role
    if target_user.pk == request.user.pk:
        messages.error(request, 'You cannot change your own administrator role.')
        return redirect('accounts:admin_user_detail', user_id=target_user.pk)

    current_role = target_user.profile.role

    if request.method == 'POST':
        new_role = request.POST.get('role', '').strip().upper()
        if new_role not in [Profile.ROLE_USER, Profile.ROLE_ADMIN]:
            messages.error(request, 'Invalid role selection.')
            return redirect('accounts:admin_user_detail', user_id=target_user.pk)

        target_user.profile.role = new_role
        target_user.profile.save()
        messages.success(
            request,
            f'Role for "@{target_user.username}" changed from {current_role} to {new_role}.'
        )
        return redirect('accounts:admin_user_detail', user_id=target_user.pk)

    return render(request, 'admin_dashboard/confirm_user_role.html', {
        'target_user': target_user,
        'current_role': current_role,
        'proposed_role': Profile.ROLE_USER if current_role == Profile.ROLE_ADMIN else Profile.ROLE_ADMIN,
    })


# ─────────────────────────────────────────────
# 3. Item Management
# ─────────────────────────────────────────────

@admin_required
def admin_items_view(request):
    """
    Admin management page for all items with search, type/status/category filters,
    and archive/restore actions.
    """
    items_qs = Item.objects.select_related('category', 'reporter').all().order_by('-created_at')

    # Search: title, description, location, reporter username
    q = request.GET.get('q', '').strip()
    if q:
        items_qs = items_qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q) |
            Q(reporter__username__icontains=q)
        )

    # Filter: Item Type (LOST, FOUND)
    item_type = request.GET.get('type', '').strip().upper()
    if item_type in [Item.TYPE_LOST, Item.TYPE_FOUND]:
        items_qs = items_qs.filter(item_type=item_type)
    else:
        item_type = ''

    # Filter: Status (ACTIVE, ARCHIVED)
    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter in [Item.STATUS_ACTIVE, Item.STATUS_ARCHIVED]:
        items_qs = items_qs.filter(status=status_filter)
    else:
        status_filter = ''

    # Filter: Category
    category_id = request.GET.get('category', '').strip()
    selected_category = None
    if category_id.isdigit():
        items_qs = items_qs.filter(category_id=int(category_id))
        selected_category = int(category_id)

    # Pagination: 10 per page
    paginator = Paginator(items_qs, 10)
    page_number = request.GET.get('page')
    try:
        items_page = paginator.page(page_number)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    # Build querystring preserving parameters (excluding page)
    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    querystring = get_params.urlencode()

    categories = Category.objects.all().order_by('name')

    return render(request, 'admin_dashboard/items.html', {
        'items_page': items_page,
        'total_count': paginator.count,
        'categories': categories,
        'q': q,
        'item_type': item_type,
        'status_filter': status_filter,
        'selected_category': selected_category,
        'querystring': querystring,
    })


# ─────────────────────────────────────────────
# 4. Claim Management
# ─────────────────────────────────────────────

@admin_required
def admin_claims_view(request):
    """
    Admin management view for claims with search, status filtering, and pagination.
    """
    claims_qs = Claim.objects.select_related(
        'item', 'item__category', 'claimant', 'reviewed_by'
    ).all().order_by('-created_at')

    # Search: item title, claimant username, claimant email
    q = request.GET.get('q', '').strip()
    if q:
        claims_qs = claims_qs.filter(
            Q(item__title__icontains=q) |
            Q(claimant__username__icontains=q) |
            Q(claimant__email__icontains=q) |
            Q(message__icontains=q) |
            Q(proof_description__icontains=q)
        )

    # Filter by Status
    status_filter = request.GET.get('status', '').strip().upper()
    valid_statuses = [
        Claim.STATUS_PENDING,
        Claim.STATUS_APPROVED,
        Claim.STATUS_REJECTED,
        Claim.STATUS_WITHDRAWN,
    ]
    if status_filter in valid_statuses:
        claims_qs = claims_qs.filter(status=status_filter)
    else:
        status_filter = ''

    # Pagination: 10 per page
    paginator = Paginator(claims_qs, 10)
    page_number = request.GET.get('page')
    try:
        claims_page = paginator.page(page_number)
    except PageNotAnInteger:
        claims_page = paginator.page(1)
    except EmptyPage:
        claims_page = paginator.page(paginator.num_pages)

    # Build querystring
    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    querystring = get_params.urlencode()

    all_claims = Claim.objects.all()
    counts = {
        'all': all_claims.count(),
        'pending': all_claims.filter(status=Claim.STATUS_PENDING).count(),
        'approved': all_claims.filter(status=Claim.STATUS_APPROVED).count(),
        'rejected': all_claims.filter(status=Claim.STATUS_REJECTED).count(),
        'withdrawn': all_claims.filter(status=Claim.STATUS_WITHDRAWN).count(),
    }

    return render(request, 'admin_dashboard/claims.html', {
        'claims_page': claims_page,
        'total_count': paginator.count,
        'counts': counts,
        'q': q,
        'status_filter': status_filter,
        'querystring': querystring,
    })


# ─────────────────────────────────────────────
# 5. Category Management
# ─────────────────────────────────────────────

@admin_required
def admin_categories_view(request):
    """
    List categories with item count, search, and pagination.
    """
    categories_qs = Category.objects.annotate(item_count=Count('items')).order_by('name')

    q = request.GET.get('q', '').strip()
    if q:
        categories_qs = categories_qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    # Pagination: 10 per page
    paginator = Paginator(categories_qs, 10)
    page_number = request.GET.get('page')
    try:
        categories_page = paginator.page(page_number)
    except PageNotAnInteger:
        categories_page = paginator.page(1)
    except EmptyPage:
        categories_page = paginator.page(paginator.num_pages)

    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    querystring = get_params.urlencode()

    return render(request, 'admin_dashboard/categories.html', {
        'categories_page': categories_page,
        'total_count': paginator.count,
        'q': q,
        'querystring': querystring,
    })


@admin_required
def admin_category_create_view(request):
    """
    Create a new item category.
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('accounts:admin_categories')
    else:
        form = CategoryForm()

    return render(request, 'admin_dashboard/category_form.html', {
        'form': form,
        'action_title': 'Add New Category',
        'submit_label': 'Create Category',
        'is_edit': False,
    })


@admin_required
def admin_category_edit_view(request, pk):
    """
    Edit an existing category.
    """
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('accounts:admin_categories')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'admin_dashboard/category_form.html', {
        'form': form,
        'category': category,
        'action_title': f'Edit Category: {category.name}',
        'submit_label': 'Save Changes',
        'is_edit': True,
    })


@admin_required
def admin_category_delete_view(request, pk):
    """
    Safely delete a category.
    If items reference the category, prevent deletion with a clear message.
    """
    category = get_object_or_404(Category, pk=pk)
    item_count = category.items.count()

    if item_count > 0:
        messages.error(
            request,
            f'Cannot delete category "{category.name}" because it contains {item_count} item(s). '
            f'Please reassign or delete those items first.'
        )
        return redirect('accounts:admin_categories')

    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" was successfully deleted.')
        return redirect('accounts:admin_categories')

    return render(request, 'admin_dashboard/confirm_delete_category.html', {
        'category': category,
        'item_count': item_count,
    })


# ─────────────────────────────────────────────
# 6. Admin Match Management (Sprint 6)
# ─────────────────────────────────────────────

@admin_required
def admin_matches_view(request):
    """Admin view to inspect, search, filter, and review all item matches."""
    matches_qs = ItemMatch.objects.select_related(
        'lost_item', 'lost_item__reporter',
        'found_item', 'found_item__reporter',
        'lost_item__category', 'found_item__category'
    )

    # Status filter
    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter in [ItemMatch.STATUS_PENDING, ItemMatch.STATUS_CONFIRMED, ItemMatch.STATUS_DISMISSED]:
        matches_qs = matches_qs.filter(status=status_filter)
    else:
        status_filter = ''

    # Search (item titles, reporter usernames)
    q = request.GET.get('q', '').strip()
    if q:
        matches_qs = matches_qs.filter(
            Q(lost_item__title__icontains=q) |
            Q(found_item__title__icontains=q) |
            Q(lost_item__reporter__username__icontains=q) |
            Q(found_item__reporter__username__icontains=q)
        )

    # Sort
    sort_param = request.GET.get('sort', 'highest_score').strip()
    if sort_param == 'lowest_score':
        matches_qs = matches_qs.order_by('score', '-created_at')
    elif sort_param == 'newest':
        matches_qs = matches_qs.order_by('-created_at')
    else:
        matches_qs = matches_qs.order_by('-score', '-created_at')

    counts = {
        'all': ItemMatch.objects.count(),
        'pending': ItemMatch.objects.filter(status=ItemMatch.STATUS_PENDING).count(),
        'confirmed': ItemMatch.objects.filter(status=ItemMatch.STATUS_CONFIRMED).count(),
        'dismissed': ItemMatch.objects.filter(status=ItemMatch.STATUS_DISMISSED).count(),
    }

    paginator = Paginator(matches_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_dashboard/matches.html', {
        'matches': page_obj,
        'page_obj': page_obj,
        'counts': counts,
        'status_filter': status_filter,
        'q': q,
        'sort': sort_param,
    })


@admin_required
def admin_match_confirm_view(request, match_id):
    """Admin action to confirm a match."""
    if request.method != 'POST':
        return redirect('accounts:admin_matches')
    match = get_object_or_404(ItemMatch, pk=match_id)
    match.status = ItemMatch.STATUS_CONFIRMED
    match.save(update_fields=['status', 'updated_at'])
    messages.success(request, f'Match #{match.pk} has been confirmed.')
    return redirect('accounts:admin_matches')


@admin_required
def admin_match_dismiss_view(request, match_id):
    """Admin action to dismiss a match."""
    if request.method != 'POST':
        return redirect('accounts:admin_matches')
    match = get_object_or_404(ItemMatch, pk=match_id)
    match.status = ItemMatch.STATUS_DISMISSED
    match.save(update_fields=['status', 'updated_at'])
    messages.info(request, f'Match #{match.pk} has been dismissed.')
    return redirect('accounts:admin_matches')


# ─────────────────────────────────────────────
# 7. Admin Notification Management (Sprint 6)
# ─────────────────────────────────────────────

@admin_required
def admin_notifications_view(request):
    """Admin view to inspect notification records across the system."""
    notifs_qs = Notification.objects.select_related(
        'recipient', 'related_item', 'related_claim'
    )

    # Filter by notification_type
    type_filter = request.GET.get('type', '').strip().upper()
    valid_types = [t[0] for t in Notification.NOTIFICATION_TYPE_CHOICES]
    if type_filter in valid_types:
        notifs_qs = notifs_qs.filter(notification_type=type_filter)
    else:
        type_filter = ''

    # Filter by read status
    read_filter = request.GET.get('read', '').strip().lower()
    if read_filter == 'read':
        notifs_qs = notifs_qs.filter(is_read=True)
    elif read_filter == 'unread':
        notifs_qs = notifs_qs.filter(is_read=False)
    else:
        read_filter = ''

    # Search by recipient username or title
    q = request.GET.get('q', '').strip()
    if q:
        notifs_qs = notifs_qs.filter(
            Q(recipient__username__icontains=q) |
            Q(title__icontains=q) |
            Q(message__icontains=q)
        )

    counts = {
        'all': Notification.objects.count(),
        'unread': Notification.objects.filter(is_read=False).count(),
        'read': Notification.objects.filter(is_read=True).count(),
    }

    paginator = Paginator(notifs_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_dashboard/notifications.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'counts': counts,
        'type_filter': type_filter,
        'read_filter': read_filter,
        'q': q,
        'type_choices': Notification.NOTIFICATION_TYPE_CHOICES,
    })
