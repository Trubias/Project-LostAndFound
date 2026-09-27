import csv
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg
from django.utils import timezone

from accounts.views import admin_required
from accounts.models import Profile
from items.models import Item, Category
from claims.models import Claim
from matches.models import ItemMatch


@admin_required
def reports_dashboard_view(request):
    """
    Admin-only reporting dashboard displaying live database statistics
    for items, claims, categories, locations, matching, and users.
    Includes print-friendly formatting.
    """
    now = timezone.now()

    # Item Statistics
    all_items = Item.objects.all()
    total_items = all_items.count()
    total_lost = all_items.filter(item_type=Item.TYPE_LOST).count()
    total_found = all_items.filter(item_type=Item.TYPE_FOUND).count()
    active_items = all_items.filter(status=Item.STATUS_ACTIVE).count()
    archived_items = all_items.filter(status=Item.STATUS_ARCHIVED).count()

    active_lost = all_items.filter(item_type=Item.TYPE_LOST, status=Item.STATUS_ACTIVE).count()
    active_found = all_items.filter(item_type=Item.TYPE_FOUND, status=Item.STATUS_ACTIVE).count()
    archived_lost = all_items.filter(item_type=Item.TYPE_LOST, status=Item.STATUS_ARCHIVED).count()
    archived_found = all_items.filter(item_type=Item.TYPE_FOUND, status=Item.STATUS_ARCHIVED).count()

    # Claim Statistics
    all_claims = Claim.objects.all()
    total_claims = all_claims.count()
    pending_claims = all_claims.filter(status=Claim.STATUS_PENDING).count()
    approved_claims = all_claims.filter(status=Claim.STATUS_APPROVED).count()
    rejected_claims = all_claims.filter(status=Claim.STATUS_REJECTED).count()
    withdrawn_claims = all_claims.filter(status=Claim.STATUS_WITHDRAWN).count()

    # Matching Statistics
    all_matches = ItemMatch.objects.all()
    total_matches = all_matches.count()
    pending_matches = all_matches.filter(status=ItemMatch.STATUS_PENDING).count()
    confirmed_matches = all_matches.filter(status=ItemMatch.STATUS_CONFIRMED).count()
    dismissed_matches = all_matches.filter(status=ItemMatch.STATUS_DISMISSED).count()
    avg_score = all_matches.aggregate(avg=Avg('score'))['avg'] or 0

    # Category Statistics
    categories = Category.objects.annotate(
        item_count=Count('items'),
        lost_count=Count('items', filter=Q(items__item_type=Item.TYPE_LOST)),
        found_count=Count('items', filter=Q(items__item_type=Item.TYPE_FOUND)),
    ).order_by('-item_count', 'name')

    # Location Statistics (top 15 locations)
    locations = Item.objects.values('location').annotate(
        total=Count('id'),
        lost_count=Count('id', filter=Q(item_type=Item.TYPE_LOST)),
        found_count=Count('id', filter=Q(item_type=Item.TYPE_FOUND)),
    ).order_by('-total')[:15]

    # User Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admin_users = User.objects.filter(
        Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN)
    ).distinct().count()
    regular_users = total_users - admin_users

    context = {
        'generated_at': now,
        # Items
        'total_items': total_items,
        'total_lost': total_lost,
        'total_found': total_found,
        'active_items': active_items,
        'archived_items': archived_items,
        'active_lost': active_lost,
        'active_found': active_found,
        'archived_lost': archived_lost,
        'archived_found': archived_found,
        # Claims
        'total_claims': total_claims,
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
        'withdrawn_claims': withdrawn_claims,
        # Matches
        'total_matches': total_matches,
        'pending_matches': pending_matches,
        'confirmed_matches': confirmed_matches,
        'dismissed_matches': dismissed_matches,
        'avg_score': round(avg_score, 1),
        # Categorized data
        'categories': categories,
        'locations': locations,
        # Users
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'regular_users': regular_users,
    }
    return render(request, 'reports/index.html', context)


@admin_required
def export_items_csv(request):
    """Export all items in CSV format."""
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="items_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Title', 'Type', 'Category', 'Location',
        'Date Occurred', 'Status', 'Reporter Username', 'Reporter Email', 'Created At'
    ])

    items = Item.objects.select_related('category', 'reporter').order_by('-created_at')
    for item in items:
        writer.writerow([
            item.id,
            item.title,
            item.get_item_type_display(),
            item.category.name if item.category else 'Uncategorized',
            item.location,
            item.date_occurred.strftime('%Y-%m-%d') if item.date_occurred else '',
            item.get_status_display(),
            item.reporter.username if item.reporter else '',
            item.reporter.email if item.reporter else '',
            item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
        ])

    return response


@admin_required
def export_claims_csv(request):
    """Export all claims in CSV format."""
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="claims_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Claim ID', 'Item ID', 'Item Title', 'Claimant Username', 'Claimant Email',
        'Status', 'Reviewer Username', 'Created At', 'Reviewed At',
        'Claim Message', 'Proof Description', 'Reviewer Notes'
    ])

    claims = Claim.objects.select_related('item', 'claimant', 'reviewed_by').order_by('-created_at')
    for claim in claims:
        writer.writerow([
            claim.id,
            claim.item.id,
            claim.item.title,
            claim.claimant.username if claim.claimant else '',
            claim.claimant.email if claim.claimant else '',
            claim.get_status_display(),
            claim.reviewed_by.username if claim.reviewed_by else 'None',
            claim.created_at.strftime('%Y-%m-%d %H:%M:%S') if claim.created_at else '',
            claim.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if claim.reviewed_at else '',
            claim.message.strip(),
            claim.proof_description.strip(),
            (claim.reviewer_notes or '').strip(),
        ])

    return response


@admin_required
def export_users_csv(request):
    """
    Export users in CSV format.
    Never exports passwords, password hashes, secrets, or tokens.
    """
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="users_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'Email', 'First Name', 'Last Name',
        'Role', 'Is Active', 'Is Superuser', 'Date Joined', 'Last Login',
        'Items Reported', 'Claims Submitted'
    ])

    users = User.objects.select_related('profile').annotate(
        items_count=Count('reported_items', distinct=True),
        claims_count=Count('claims', distinct=True),
    ).order_by('id')

    for u in users:
        role = 'Admin' if (u.is_superuser or (hasattr(u, 'profile') and u.profile.role == Profile.ROLE_ADMIN)) else 'User'
        writer.writerow([
            u.id,
            u.username,
            u.email,
            u.first_name,
            u.last_name,
            role,
            'Yes' if u.is_active else 'No',
            'Yes' if u.is_superuser else 'No',
            u.date_joined.strftime('%Y-%m-%d %H:%M:%S') if u.date_joined else '',
            u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else 'Never',
            u.items_count,
            u.claims_count,
        ])

    return response


@admin_required
def export_categories_csv(request):
    """Export categories in CSV format."""
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="categories_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Name', 'Description', 'Total Items', 'Lost Items', 'Found Items', 'Created At'
    ])

    categories = Category.objects.annotate(
        total_items=Count('items'),
        lost_items=Count('items', filter=Q(items__item_type=Item.TYPE_LOST)),
        found_items=Count('items', filter=Q(items__item_type=Item.TYPE_FOUND)),
    ).order_by('name')

    for cat in categories:
        writer.writerow([
            cat.id,
            cat.name,
            cat.description or '',
            cat.total_items,
            cat.lost_items,
            cat.found_items,
            cat.created_at.strftime('%Y-%m-%d %H:%M:%S') if cat.created_at else '',
        ])

    return response


@admin_required
def export_matches_csv(request):
    """Export potential matches in CSV format."""
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="matches_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Match ID', 'Lost Item ID', 'Lost Item Title', 'Found Item ID', 'Found Item Title',
        'Overall Score', 'Status', 'Category Score', 'Location Score', 'Title Score',
        'Date Score', 'Created At'
    ])

    matches = ItemMatch.objects.select_related('lost_item', 'found_item').order_by('-score', '-created_at')
    for m in matches:
        writer.writerow([
            m.id,
            m.lost_item_id,
            m.lost_item.title if m.lost_item else '',
            m.found_item_id,
            m.found_item.title if m.found_item else '',
            m.score,
            m.get_status_display(),
            m.score_category,
            m.score_location,
            m.score_title,
            m.score_date,
            m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else '',
        ])

    return response
