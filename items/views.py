from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.urls import reverse

from accounts.models import Profile
from .models import Item, Category
from .forms import ItemForm, CategoryForm
from notifications import services as notif_svc
from matches import engine as match_engine


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_admin_user(user):
    if user.is_superuser:
        return True
    try:
        return user.profile.role == Profile.ROLE_ADMIN
    except Profile.DoesNotExist:
        return False


# ─────────────────────────────────────────────
# Item List & Discovery Views (Sprint 3)
# ─────────────────────────────────────────────

def item_list_view(request, default_type=None, page_mode='ALL'):
    """
    Search, filter, sort, and paginate active Lost and Found items.
    Archived items are strictly excluded from public browse/discovery results.
    """
    items = Item.objects.filter(status=Item.STATUS_ACTIVE).select_related('category', 'reporter')

    # 1. Search (Title, Description, Location, Category Name)
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q) |
            Q(category__name__icontains=q)
        )

    # 2. Item Type Filter
    # In dedicated views (page_mode='LOST' or 'FOUND'), default_type applies unless overridden
    item_type = request.GET.get('type', default_type or '').strip().upper()
    if item_type in [Item.TYPE_LOST, Item.TYPE_FOUND]:
        items = items.filter(item_type=item_type)
    else:
        item_type = ''

    # 3. Category Filter
    category_id = request.GET.get('category', '').strip()
    selected_category_obj = None
    if category_id:
        if category_id.isdigit():
            selected_category_obj = Category.objects.filter(id=int(category_id)).first()
            if selected_category_obj:
                items = items.filter(category=selected_category_obj)
        else:
            cat = Category.objects.filter(name__iexact=category_id).first()
            if cat:
                selected_category_obj = cat
                category_id = str(cat.id)
                items = items.filter(category=cat)

    # 4. Location Filter
    location = request.GET.get('location', '').strip()
    if location:
        items = items.filter(location__icontains=location)

    # 5. Date Filters (date_occurred)
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if date_from:
        try:
            d_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            items = items.filter(date_occurred__gte=d_from_obj)
        except ValueError:
            date_from = ''

    if date_to:
        try:
            d_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            items = items.filter(date_occurred__lte=d_to_obj)
        except ValueError:
            date_to = ''

    # 6. Sorting
    sort_param = request.GET.get('sort', 'newest').strip()
    sort_mapping = {
        'newest': ('-created_at',),
        'oldest': ('created_at',),
        'date_newest': ('-date_occurred', '-created_at'),
        'date_oldest': ('date_occurred', 'created_at'),
        'title_asc': ('title',),
        'title_desc': ('-title',),
    }
    order_fields = sort_mapping.get(sort_param, ('-created_at',))
    items = items.order_by(*order_fields)

    total_count = items.count()

    # 7. Pagination (10 per page)
    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Query string for preserving filters in pagination & clear links
    params_for_pagination = request.GET.copy()
    if 'page' in params_for_pagination:
        params_for_pagination.pop('page')
    query_string_no_page = params_for_pagination.urlencode()

    # Active Filter Badges with per-filter removal URLs
    base_url = request.path

    def get_remove_url(param_to_remove):
        p = request.GET.copy()
        if param_to_remove in p:
            p.pop(param_to_remove)
        if 'page' in p:
            p.pop('page')
        encoded = p.urlencode()
        return f"{base_url}?{encoded}" if encoded else base_url

    active_filters = []
    if q:
        active_filters.append({
            'label': 'Search',
            'value': f'"{q}"',
            'param': 'q',
            'remove_url': get_remove_url('q'),
        })
    if item_type and page_mode == 'ALL':
        active_filters.append({
            'label': 'Type',
            'value': 'Lost' if item_type == Item.TYPE_LOST else 'Found',
            'param': 'type',
            'remove_url': get_remove_url('type'),
        })
    if selected_category_obj:
        active_filters.append({
            'label': 'Category',
            'value': selected_category_obj.name,
            'param': 'category',
            'remove_url': get_remove_url('category'),
        })
    if location:
        active_filters.append({
            'label': 'Location',
            'value': location,
            'param': 'location',
            'remove_url': get_remove_url('location'),
        })
    if date_from:
        active_filters.append({
            'label': 'From',
            'value': date_from,
            'param': 'date_from',
            'remove_url': get_remove_url('date_from'),
        })
    if date_to:
        active_filters.append({
            'label': 'To',
            'value': date_to,
            'param': 'date_to',
            'remove_url': get_remove_url('date_to'),
        })
    if sort_param and sort_param != 'newest':
        sort_names = {
            'oldest': 'Oldest Reported',
            'date_newest': 'Newest Occurred',
            'date_oldest': 'Oldest Occurred',
            'title_asc': 'Title A-Z',
            'title_desc': 'Title Z-A',
        }
        active_filters.append({
            'label': 'Sort',
            'value': sort_names.get(sort_param, sort_param),
            'param': 'sort',
            'remove_url': get_remove_url('sort'),
        })

    categories = Category.objects.all().order_by('name')

    # View Mode Configuration
    if page_mode == 'LOST':
        page_title = 'Lost Items'
        page_subtitle = 'Browse and search items reported as lost by their owners.'
        page_icon = 'bi-question-circle-fill'
        page_color = 'text-warning'
        clear_url = reverse('items:lost_items')
    elif page_mode == 'FOUND':
        page_title = 'Found Items'
        page_subtitle = 'Browse and search items discovered and turned in.'
        page_icon = 'bi-bag-check-fill'
        page_color = 'text-success'
        clear_url = reverse('items:found_items')
    else:
        page_title = 'Browse Items'
        page_subtitle = 'Search and discover all active lost and found items.'
        page_icon = 'bi-grid-3x3-gap-fill'
        page_color = 'text-primary'
        clear_url = reverse('items:item_list')

    context = {
        'items': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': total_count,
        'categories': categories,
        'q': q,
        'selected_type': item_type,
        'selected_category': category_id,
        'selected_category_obj': selected_category_obj,
        'selected_location': location,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort_param,
        'active_filters': active_filters,
        'query_string_no_page': query_string_no_page,
        'page_mode': page_mode,
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'page_icon': page_icon,
        'page_color': page_color,
        'clear_url': clear_url,
    }
    return render(request, 'items/item_list.html', context)


def lost_items_view(request):
    """Convenience route displaying only active Lost items."""
    return item_list_view(request, default_type=Item.TYPE_LOST, page_mode='LOST')


def found_items_view(request):
    """Convenience route displaying only active Found items."""
    return item_list_view(request, default_type=Item.TYPE_FOUND, page_mode='FOUND')



# ─────────────────────────────────────────────
# Item Detail
# ─────────────────────────────────────────────

def item_detail_view(request, pk):
    item = get_object_or_404(Item, pk=pk)
    can_edit = False
    can_archive = False
    can_restore = False
    can_claim = False
    has_pending_claim = False
    user_claim = None
    item_claims_count = 0

    if request.user.is_authenticated:
        is_owner = item.reporter == request.user
        is_admin = is_admin_user(request.user)
        can_edit = is_owner or is_admin
        if item.is_active():
            can_archive = is_owner or is_admin
        if item.is_archived():
            can_restore = is_owner or is_admin

        # Claim logic
        if item.is_active() and not is_owner and not is_admin:
            from claims.models import Claim as ClaimModel
            existing = ClaimModel.objects.filter(
                item=item, claimant=request.user
            ).order_by('-created_at').first()
            if existing and existing.is_pending():
                has_pending_claim = True
                user_claim = existing
            elif not existing or existing.status in [ClaimModel.STATUS_REJECTED, ClaimModel.STATUS_WITHDRAWN]:
                can_claim = True

        # Count claims for item reporter / admin
        if is_owner or is_admin:
            from claims.models import Claim as ClaimModel
            item_claims_count = ClaimModel.objects.filter(item=item).count()

    return render(request, 'items/item_detail.html', {
        'item': item,
        'can_edit': can_edit,
        'can_archive': can_archive,
        'can_restore': can_restore,
        'can_claim': can_claim,
        'has_pending_claim': has_pending_claim,
        'user_claim': user_claim,
        'item_claims_count': item_claims_count,
    })



# ─────────────────────────────────────────────
# Report Lost Item
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def report_lost_view(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.item_type = Item.TYPE_LOST
            item.reporter = request.user
            item.status = Item.STATUS_ACTIVE
            item.save()
            # Run the matching engine and send match notifications for new matches
            _run_matching_for_item(item)
            messages.success(request, f'Lost item "{item.title}" has been reported successfully.')
            return redirect('items:my_items')
    else:
        form = ItemForm()

    return render(request, 'items/item_form.html', {
        'form': form,
        'form_title': 'Report a Lost Item',
        'form_subtitle': 'Fill in the details about the item you lost.',
        'form_icon': 'bi-question-circle-fill',
        'form_color': 'text-warning',
        'submit_label': 'Submit Lost Report',
        'item_type': 'LOST',
    })


# ─────────────────────────────────────────────
# Report Found Item
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def report_found_view(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.item_type = Item.TYPE_FOUND
            item.reporter = request.user
            item.status = Item.STATUS_ACTIVE
            item.save()
            # Run the matching engine and send match notifications for new matches
            _run_matching_for_item(item)
            messages.success(request, f'Found item "{item.title}" has been reported successfully.')
            return redirect('items:my_items')
    else:
        form = ItemForm()

    return render(request, 'items/item_form.html', {
        'form': form,
        'form_title': 'Report a Found Item',
        'form_subtitle': 'Fill in the details about the item you found.',
        'form_icon': 'bi-bag-check-fill',
        'form_color': 'text-success',
        'submit_label': 'Submit Found Report',
        'item_type': 'FOUND',
    })


# ─────────────────────────────────────────────
# My Reports
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def my_items_view(request):
    user_items = Item.objects.filter(reporter=request.user).select_related('category')
    active_items = user_items.filter(status=Item.STATUS_ACTIVE)
    archived_items = user_items.filter(status=Item.STATUS_ARCHIVED)

    return render(request, 'items/my_items.html', {
        'active_items': active_items,
        'archived_items': archived_items,
    })


# ─────────────────────────────────────────────
# Edit Item
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def edit_item_view(request, pk):
    item = get_object_or_404(Item, pk=pk)

    # Permission check — server-side
    if not (item.reporter == request.user or is_admin_user(request.user)):
        messages.error(request, 'You do not have permission to edit this item.')
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            updated = form.save(commit=False)
            # Prevent changing reporter or timestamps
            updated.reporter = item.reporter
            updated.save()
            messages.success(request, f'Item "{item.title}" has been updated.')
            return redirect('items:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)

    return render(request, 'items/item_form.html', {
        'form': form,
        'item': item,
        'form_title': f'Edit: {item.title}',
        'form_subtitle': 'Update the details for this report.',
        'form_icon': 'bi-pencil-square',
        'form_color': 'text-primary',
        'submit_label': 'Save Changes',
        'item_type': item.item_type,
        'is_edit': True,
    })


# ─────────────────────────────────────────────
# Archive Item
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def archive_item_view(request, pk):
    item = get_object_or_404(Item, pk=pk)

    if not (item.reporter == request.user or is_admin_user(request.user)):
        messages.error(request, 'You do not have permission to archive this item.')
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        item.status = Item.STATUS_ARCHIVED
        item.save()
        # Notify reporter if admin archived it
        notif_svc.notify_item_archived(item, triggering_user=request.user)
        messages.success(request, f'Item "{item.title}" has been archived.')
        if is_admin_user(request.user):
            return redirect('items:item_list')
        return redirect('items:my_items')

    return render(request, 'items/confirm_archive.html', {'item': item})


# ─────────────────────────────────────────────
# Restore Item
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def restore_item_view(request, pk):
    item = get_object_or_404(Item, pk=pk)

    if not (item.reporter == request.user or is_admin_user(request.user)):
        messages.error(request, 'You do not have permission to restore this item.')
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        item.status = Item.STATUS_ACTIVE
        item.save()
        # Notify reporter if admin restored it
        notif_svc.notify_item_restored(item, triggering_user=request.user)
        # Re-run matching since the item is active again
        _run_matching_for_item(item)
        messages.success(request, f'Item "{item.title}" has been restored to active.')
        if is_admin_user(request.user):
            return redirect('items:item_list')
        return redirect('items:my_items')

    return render(request, 'items/confirm_restore.html', {'item': item})


# ─────────────────────────────────────────────
# Category Management (Admin only)
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def category_list_view(request):
    if not is_admin_user(request.user):
        messages.error(request, 'Only administrators can manage categories.')
        return render(request, '403.html', status=403)
    categories = Category.objects.all().order_by('name')
    return render(request, 'items/category_list.html', {'categories': categories})


@login_required(login_url='/login/')
def category_create_view(request):
    if not is_admin_user(request.user):
        messages.error(request, 'Only administrators can add categories.')
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('items:category_list')
    else:
        form = CategoryForm()

    return render(request, 'items/category_form.html', {
        'form': form,
        'action_title': 'Add New Category',
        'submit_label': 'Create Category',
        'is_edit': False,
    })


@login_required(login_url='/login/')
def category_edit_view(request, pk):
    if not is_admin_user(request.user):
        messages.error(request, 'Only administrators can edit categories.')
        return render(request, '403.html', status=403)

    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('items:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'items/category_form.html', {
        'form': form,
        'category': category,
        'action_title': f'Edit Category: {category.name}',
        'submit_label': 'Save Changes',
        'is_edit': True,
    })


@login_required(login_url='/login/')
def category_delete_view(request, pk):
    if not is_admin_user(request.user):
        messages.error(request, 'Only administrators can delete categories.')
        return render(request, '403.html', status=403)

    category = get_object_or_404(Category, pk=pk)
    item_count = category.items.count()
    if item_count > 0:
        messages.error(
            request,
            f'Cannot delete category "{category.name}" because it contains {item_count} item(s). '
            f'Please reassign or delete the items first.'
        )
        return redirect('items:category_list')

    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" was deleted successfully.')
        return redirect('items:category_list')

    return render(request, 'items/confirm_delete_category.html', {'category': category, 'item_count': item_count})


# ─────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────

def _run_matching_for_item(item):
    """
    Run the match engine for *item* and create match notifications
    for any new matches found.  Called after an item is created or restored.
    """
    results = match_engine.generate_matches_for_item(item)
    for match, created in results:
        if created:
            notif_svc.notify_possible_match(match)
