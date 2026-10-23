"""JSON page data for the Next.js application shell."""
import re
from calendar import month_abbr
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.models import Profile
from claims.models import Claim
from items.models import Category, Item, ReportLocation
from items.locations import BUILDING_CHOICES, LOCATION_CHOICES, ROOM_CHOICES
from matches.models import ItemMatch
from notifications.models import Notification
from auditlog.models import AuditEvent
from reports.models import AbuseReport


def _item_card(item, request):
    reporter_profile = getattr(item.reporter, 'profile', None)
    return {
        'id': item.pk,
        'title': item.title,
        'subtitle': f"{item.get_item_type_display()} · {item.location}",
        'badge': item.get_status_display(),
        'type': item.item_type,
        'image': item.image.url if item.image else None,
        'href': f'/items/{item.pk}',
        'meta': [item.category.name if item.category else 'Uncategorized', item.date_occurred.isoformat()],
        'reporterName': item.reporter.get_full_name() or item.reporter.username,
        'reporterUsername': item.reporter.username,
        'reporterAvatar': reporter_profile.profile_image.url if reporter_profile and reporter_profile.profile_image else None,
    }


def _stats(pairs):
    return [{'label': label, 'value': value} for label, value in pairs]


def _paginate(queryset, request, per_page=50):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))


def _page_meta(page_obj):
    return {'page': page_obj.number, 'num_pages': page_obj.paginator.num_pages, 'has_previous': page_obj.has_previous(), 'has_next': page_obj.has_next()}


def _admin_report_trends():
    """Build date buckets from report creation dates for the admin overview chart."""
    today = timezone.localdate()
    year_start = today.replace(day=1)
    for _ in range(11):
        year_start = (year_start - timedelta(days=1)).replace(day=1)
    daily_counts = {
        (row['report_day'], row['item_type']): row['total']
        for row in Item.objects.filter(created_at__date__gte=year_start, created_at__date__lte=today)
        .annotate(report_day=TruncDate('created_at'))
        .values('report_day', 'item_type')
        .annotate(total=Count('pk'))
    }

    trends = {}
    week_start = today - timedelta(days=6)
    week_points = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        week_points.append({
            'label': day.strftime('%a'),
            'lost': daily_counts.get((day, Item.TYPE_LOST), 0),
            'found': daily_counts.get((day, Item.TYPE_FOUND), 0),
        })
    trends['7d'] = week_points

    month_start = today - timedelta(days=29)
    month_points = []
    for bucket in range(5):
        start = month_start + timedelta(days=bucket * 7)
        end = min(start + timedelta(days=6), today)
        month_points.append({
            'label': start.strftime('%b %d'),
            'lost': sum(daily_counts.get((start + timedelta(days=day), Item.TYPE_LOST), 0) for day in range((end - start).days + 1)),
            'found': sum(daily_counts.get((start + timedelta(days=day), Item.TYPE_FOUND), 0) for day in range((end - start).days + 1)),
        })
    trends['30d'] = month_points

    for key, month_count in [('6m', 6), ('1y', 12)]:
        current_month = today.replace(day=1)
        start_month = current_month
        for _ in range(month_count - 1):
            start_month = (start_month - timedelta(days=1)).replace(day=1)
        points = []
        for offset in range(month_count):
            point_month = start_month
            for _ in range(offset):
                point_month = (point_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            lost = 0
            found = 0
            for (report_day, item_type), total in daily_counts.items():
                if report_day.year == point_month.year and report_day.month == point_month.month:
                    if item_type == Item.TYPE_LOST:
                        lost += total
                    elif item_type == Item.TYPE_FOUND:
                        found += total
            points.append({'label': month_abbr[point_month.month], 'lost': lost, 'found': found})
        trends[key] = points
    return trends


def _admin_category_breakdown(limit=8):
    return [{
        'name': row.name, 'total': row.report_total,
        'lost': row.lost_total, 'found': row.found_total,
    } for row in Category.objects.annotate(
        report_total=Count('items'),
        lost_total=Count('items', filter=Q(items__item_type=Item.TYPE_LOST)),
        found_total=Count('items', filter=Q(items__item_type=Item.TYPE_FOUND)),
    ).order_by('-report_total', 'name')[:limit]]


def _admin_claim_status_counts():
    totals = {row['status']: row['total'] for row in Claim.objects.values('status').annotate(total=Count('pk'))}
    return [{'label': label, 'value': totals.get(status, 0)} for status, label in Claim.STATUS_CHOICES]


def _admin_recent_activity(request, limit=8):
    activity = []
    for item in Item.objects.select_related('reporter', 'category').order_by('-created_at')[:limit]:
        activity.append({
            'sort': item.created_at,
            'record': {'id': item.pk, 'title': item.title,
                'subtitle': f'{item.get_item_type_display()} report · {item.location}',
                'badge': item.get_status_display(), 'href': f'/items/{item.pk}',
                'meta': [f'Reported by {item.reporter.get_full_name() or item.reporter.username} (@{item.reporter.username})', f'Created {timezone.localtime(item.created_at).strftime("%b %d, %Y · %I:%M %p")}', f'Updated {timezone.localtime(item.updated_at).strftime("%b %d, %Y · %I:%M %p")}']},
        })
    for claim in Claim.objects.select_related('item', 'claimant', 'reviewed_by').order_by('-created_at')[:limit]:
        activity.append({
            'sort': claim.created_at,
            'record': {'id': claim.pk, 'title': f'Claim · {claim.item.title}',
                'subtitle': f'Claim submitted by @{claim.claimant.username}',
                'badge': claim.get_status_display(), 'href': f'/claims/{claim.pk}',
                'meta': [f'Submitted {timezone.localtime(claim.created_at).strftime("%b %d, %Y · %I:%M %p")}',
                    f'Reviewed by @{claim.reviewed_by.username}' if claim.reviewed_by_id else 'Awaiting reviewer',
                    f'Reviewed {timezone.localtime(claim.reviewed_at).strftime("%b %d, %Y · %I:%M %p")}' if claim.reviewed_at else 'No decision recorded',
                    f'Reviewer note: {claim.reviewer_notes}' if claim.reviewer_notes else 'No reviewer note']},
        })
    activity.sort(key=lambda entry: entry['sort'], reverse=True)
    return [entry['record'] for entry in activity[:limit]]


def _choice_options(choices, current=''):
    options = [{'value': value, 'label': label} for value, label in choices]
    if current and current not in {option['value'] for option in options}:
        options.append({'value': current, 'label': current})
    return options


def _location_options(kind, fallback):
    names = list(ReportLocation.objects.filter(kind=kind, active=True).order_by('name').values_list('name', flat=True))
    return [{'value': name, 'label': name} for name in names] if names else _choice_options(fallback)


def _protected(request, admin=False):
    if not request.user.is_authenticated:
        return {'mode': 'protected', 'title': 'Sign in to continue', 'summary': 'Sign in to access your Findly account.', 'href': '/login'}
    is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
    if admin and not is_admin:
        return {'mode': 'protected', 'title': 'Administrator access required', 'summary': 'This area is available to administrators.', 'href': '/dashboard'}
    return None


def _admin_payload(path, request):
    base = {'eyebrow': 'Workspace', 'mode': 'list', 'records': []}
    if path == '/admin-dashboard':
        items = Item.objects.all()
        claims = Claim.objects.all()
        matches = ItemMatch.objects.all()
        return {**base, 'mode': 'dashboard', 'title': 'Admin overview', 'summary': 'A clear, live view of reports, claims, and community activity.', 'stats': _stats([
            ('All reports', items.count()), ('Active reports', items.filter(status=Item.STATUS_ACTIVE).count()),
            ('Lost items', items.filter(item_type=Item.TYPE_LOST).count()), ('Found items', items.filter(item_type=Item.TYPE_FOUND).count()),
            ('Matches', matches.count()),
        ]), 'trends': _admin_report_trends(), 'adminActivity': _admin_recent_activity(request, 6),
            'claimStatusCounts': _admin_claim_status_counts(), 'categoryBreakdown': _admin_category_breakdown(6)}
    if path == '/admin-dashboard/handoffs':
        rows = Claim.objects.filter(status=Claim.STATUS_APPROVED).select_related('item', 'item__reporter', 'claimant').order_by('-reviewed_at')
        query = request.GET.get('q', '').strip()
        handoff_filter = request.GET.get('handoff', '').strip().lower()
        if not handoff_filter:
            handoff_filter = 'open'
        if query:
            rows = rows.filter(Q(item__title__icontains=query) | Q(item__reporter__username__icontains=query) | Q(claimant__username__icontains=query) | Q(handoff_location__icontains=query))
        if handoff_filter == 'open':
            rows = rows.filter(handoff_completed_at__isnull=True)
        elif handoff_filter == 'complete':
            rows = rows.filter(handoff_completed_at__isnull=False)
        elif handoff_filter != 'all':
            handoff_filter = ''
        page_obj = _paginate(rows, request)
        records = []
        for claim in page_obj.object_list:
            if claim.handoff_completed_at:
                state = 'Complete'
            elif not claim.handoff_at:
                state = 'Needs pickup plan'
            elif claim.handoff_change_request:
                state = 'Change requested'
            elif not claim.handoff_confirmed_by_claimant_at:
                state = 'Awaiting claimant'
            elif not claim.handoff_returned_by_claimant_at or not claim.handoff_returned_by_reporter_at:
                state = 'Awaiting handoff confirmations'
            else:
                state = 'Complete'
            records.append({
                'id': claim.pk, 'title': claim.item.title,
                'subtitle': f'Claimant @{claim.claimant.username} · reporter @{claim.item.reporter.username}',
                'badge': state, 'href': f'/claims/{claim.pk}',
                'meta': [
                    f'Pickup: {claim.handoff_location}' if claim.handoff_location else 'Pickup plan: not set',
                    f'Scheduled: {timezone.localtime(claim.handoff_at).strftime("%b %d, %Y · %I:%M %p")}' if claim.handoff_at else 'No time scheduled',
                    f'Change requested: {claim.handoff_change_request}' if claim.handoff_change_request else 'No change request',
                    f'Claim approved {timezone.localtime(claim.reviewed_at).strftime("%b %d, %Y")}' if claim.reviewed_at else 'Approval date unavailable',
                ],
            })
        return {**base, 'title':'Handoff queue', 'summary':'Approved claims that still need a pickup plan, plan confirmation, or return confirmation. Open a record to coordinate it.', 'records':records, **_page_meta(page_obj), 'filters':{'q':query,'handoff':handoff_filter}}
    if path == '/admin-dashboard/activity':
        rows = AuditEvent.objects.select_related('actor').order_by('-created_at')
        query = request.GET.get('q', '').strip()
        if query:
            rows = rows.filter(Q(summary__icontains=query) | Q(action__icontains=query) | Q(actor__username__icontains=query) | Q(object_type__icontains=query) | Q(object_id__icontains=query))
        page_obj = _paginate(rows, request)
        return {**base, 'title':'Activity log', 'summary':'Recorded account, report, claim, and handoff changes.', 'records':[{
            'id':event.pk, 'title':event.action.replace('.', ' ').title(),
            'subtitle':event.summary, 'badge':event.object_type,
            'href':f'/admin-dashboard/audit/{event.pk}',
            'meta':[f'By @{event.actor.username}' if event.actor_id else 'System action', f'Record #{event.object_id}' if event.object_id else 'No record ID', f'At {timezone.localtime(event.created_at).strftime("%b %d, %Y · %I:%M %p")}'],
        } for event in page_obj.object_list], **_page_meta(page_obj), 'filters':{'q':query}}
    if path == '/admin-dashboard/flags':
        rows = AbuseReport.objects.select_related('item', 'submitted_by').order_by('status', '-created_at')
        query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip().upper()
        if query:
            rows = rows.filter(Q(item__title__icontains=query) | Q(submitted_by__username__icontains=query) | Q(details__icontains=query))
        if status_filter in dict(AbuseReport.STATUS_CHOICES):
            rows = rows.filter(status=status_filter)
        else:
            status_filter = ''
        page_obj = _paginate(rows, request)
        return {**base, 'title':'Community reports', 'summary':'Review concerns submitted about item reports.', 'records':[{'id':flag.pk,'title':f'{flag.get_reason_display()} · {flag.item.title}','subtitle':flag.details,'badge':flag.get_status_display(),'href':f'/admin-dashboard/flags/{flag.pk}','meta':[f'Reported by @{flag.submitted_by.username}',f'Item #{flag.item_id}',f'Submitted {timezone.localtime(flag.created_at).strftime("%b %d, %Y · %I:%M %p")}']} for flag in page_obj.object_list], **_page_meta(page_obj), 'filters':{'q':query,'status':status_filter}}
    if path.endswith('/users'):
        users = User.objects.select_related('profile').order_by('username')
        query = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '').strip().upper()
        status_filter = request.GET.get('status', '').strip().lower()
        if query:
            users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
        if role_filter == Profile.ROLE_ADMIN:
            users = users.filter(Q(is_superuser=True) | Q(profile__role=Profile.ROLE_ADMIN))
        elif role_filter == Profile.ROLE_USER:
            users = users.filter(profile__role=Profile.ROLE_USER, is_superuser=False)
        else:
            role_filter = ''
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        else:
            status_filter = ''
        page_obj = _paginate(users, request)
        return {
            **base,
            'mode': 'table',
            'title': 'Community members',
            'summary': 'Review account details, roles, and access status.',
            **_page_meta(page_obj),
            'tableRows': [{
                'id': u.pk,
                'name': u.get_full_name() or u.username,
                'username': u.username,
                'email': u.email or 'No email provided',
                'role': getattr(getattr(u, 'profile', None), 'get_role_display', lambda: 'User')(),
                'status': 'Active' if u.is_active else 'Inactive',
                'joined': u.date_joined.strftime('%b %d, %Y'),
                'href': f'/admin-dashboard/users/{u.pk}',
            } for u in page_obj.object_list],
            'filters': {'q':query,'role':role_filter,'status':status_filter},
        }
    if path.endswith('/items'):
        rows = Item.objects.select_related('category', 'reporter').order_by('-created_at')
        query = request.GET.get('q', '').strip()
        item_type = request.GET.get('type', '').strip().upper()
        status_filter = request.GET.get('status', '').strip().upper()
        category_filter = request.GET.get('category', '').strip()
        if query:
            rows = rows.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query) | Q(reporter__username__icontains=query))
        if item_type in (Item.TYPE_LOST, Item.TYPE_FOUND):
            rows = rows.filter(item_type=item_type)
        else:
            item_type = ''
        if status_filter in (Item.STATUS_ACTIVE, Item.STATUS_ARCHIVED):
            rows = rows.filter(status=status_filter)
        else:
            status_filter = ''
        if category_filter.isdigit():
            rows = rows.filter(category_id=int(category_filter))
        else:
            category_filter = ''
        page_obj = _paginate(rows, request)
        rows = page_obj.object_list
        return {**base, **_page_meta(page_obj), 'title':'All item reports', 'summary':'Report ledger with owner, submission time, and latest update for each record.', 'records':[{
            **_item_card(i,request),
            'subtitle':f'{i.get_item_type_display()} report · {i.location} · {i.category.name if i.category else "Uncategorized"}',
            'meta':[f'Reported by {i.reporter.get_full_name() or i.reporter.username} (@{i.reporter.username})', f'Created {timezone.localtime(i.created_at).strftime("%b %d, %Y · %I:%M %p")}', f'Last updated {timezone.localtime(i.updated_at).strftime("%b %d, %Y · %I:%M %p")}'],
        } for i in rows], 'categories':list(Category.objects.order_by('name').values('id','name')), 'filters':{'q':query,'type':item_type,'status':status_filter,'category':category_filter}}
    if path.endswith('/claims'):
        rows = Claim.objects.select_related('item','claimant','reviewed_by').order_by('-created_at')
        query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', '').strip().upper()
        handoff_filter = request.GET.get('handoff', '').strip().lower()
        if query:
            rows = rows.filter(Q(item__title__icontains=query) | Q(claimant__username__icontains=query) | Q(claimant__email__icontains=query) | Q(message__icontains=query) | Q(proof_description__icontains=query))
        if status_filter in dict(Claim.STATUS_CHOICES):
            rows = rows.filter(status=status_filter)
        else:
            status_filter = ''
        if handoff_filter == 'needs_plan':
            rows = rows.filter(status=Claim.STATUS_APPROVED, handoff_at__isnull=True)
        elif handoff_filter == 'awaiting_claimant':
            rows = rows.filter(status=Claim.STATUS_APPROVED, handoff_at__isnull=False, handoff_confirmed_by_claimant_at__isnull=True)
        elif handoff_filter == 'awaiting_handoff':
            rows = rows.filter(status=Claim.STATUS_APPROVED, handoff_confirmed_by_claimant_at__isnull=False, handoff_completed_at__isnull=True)
        elif handoff_filter == 'complete':
            rows = rows.filter(status=Claim.STATUS_APPROVED, handoff_completed_at__isnull=False)
        else:
            handoff_filter = ''
        page_obj = _paginate(rows, request)
        rows = page_obj.object_list
        return {**base, **_page_meta(page_obj), 'title':'Claim reviews', 'summary':'Transparent review ledger showing who filed each claim and how it was resolved.', 'records':[{
            'id':c.pk,'title':c.item.title,'subtitle':f'Claim filed by @{c.claimant.username} · {c.item.get_item_type_display()} report','badge':c.get_status_display(),'href':f'/claims/{c.pk}',
            'meta':[f'Submitted {timezone.localtime(c.created_at).strftime("%b %d, %Y · %I:%M %p")}', f'Reviewed by @{c.reviewed_by.username}' if c.reviewed_by_id else 'Awaiting reviewer', f'Reviewed {timezone.localtime(c.reviewed_at).strftime("%b %d, %Y · %I:%M %p")}' if c.reviewed_at else 'No decision recorded', f'Handoff: {"complete" if c.handoff_completed_at else "needs pickup plan" if not c.handoff_at else "awaiting claimant" if not c.handoff_confirmed_by_claimant_at else "awaiting return confirmation"}' if c.status == Claim.STATUS_APPROVED else 'Handoff starts after approval', f'Reviewer note: {c.reviewer_notes}' if c.reviewer_notes else 'No reviewer note'],
        } for c in rows], 'filters':{'q':query,'status':status_filter,'handoff':handoff_filter}}
    if path.endswith('/categories'):
        rows = Category.objects.annotate(report_total=Count('items'), lost_total=Count('items', filter=Q(items__item_type=Item.TYPE_LOST)), found_total=Count('items', filter=Q(items__item_type=Item.TYPE_FOUND))).order_by('name')
        page_obj = _paginate(rows, request)
        rows = page_obj.object_list
        return {**base, **_page_meta(page_obj), 'title':'Item categories', 'summary':'Category register with its report volume and creation date.', 'records':[{'id':c.pk,'title':c.name,'subtitle':c.description or 'No description','badge':f'{c.report_total} reports','href':f'/admin-dashboard/categories/{c.pk}/edit','meta':[f'{c.lost_total} lost reports',f'{c.found_total} found reports',f'Created {timezone.localtime(c.created_at).strftime("%b %d, %Y")}']} for c in rows], 'links':[{'label':'Add category','href':'/admin-dashboard/categories/add'}]}
    if path == '/admin-dashboard/locations':
        protected = _protected(request, admin=True)
        if protected:
            return protected
        rows = _paginate(ReportLocation.objects.order_by('kind','name'), request)
        return {**base, **_page_meta(rows), 'title':'Report locations', 'summary':'Manage the campus, buildings, rooms, and computer labs available in lost and found reports.', 'records':[{'id':row.pk,'title':row.name,'subtitle':row.get_kind_display(),'badge':'Active' if row.active else 'Inactive','href':f'/admin-dashboard/locations/{row.pk}/edit','meta':[f'Type: {row.get_kind_display()}',f'Status: {"Active" if row.active else "Inactive"}']} for row in rows.object_list], 'links':[{'label':'Add location field','href':'/admin-dashboard/locations/add'}]}
    if path.endswith('/matches'):
        rows = ItemMatch.objects.select_related('lost_item__reporter', 'found_item__reporter', 'lost_item__category', 'found_item__category').order_by('-created_at')
        page_obj = _paginate(rows, request)
        rows = page_obj.object_list
        return {**base, **_page_meta(page_obj), 'title':'Suggested matches', 'summary':'Potential lost and found pairs with match score, reporting users, and review status.', 'records':[{'id':m.pk,'title':f'{m.lost_item.title} ↔ {m.found_item.title}','subtitle':f'{m.score}% match · {m.lost_item.location}','badge':m.get_status_display(),'href':f'/matches/{m.pk}','meta':[f'Lost report by {m.lost_item.reporter.get_full_name() or m.lost_item.reporter.username} (@{m.lost_item.reporter.username})',f'Found report by {m.found_item.reporter.get_full_name() or m.found_item.reporter.username} (@{m.found_item.reporter.username})',f'Created {timezone.localtime(m.created_at).strftime("%b %d, %Y · %I:%M %p")}']} for m in rows]}
    if path.endswith('/notifications'):
        rows = Notification.objects.select_related('recipient', 'related_item', 'related_claim').order_by('-created_at')
        page_obj = _paginate(rows, request)
        rows = page_obj.object_list
        return {**base, **_page_meta(page_obj), 'title':'System notifications', 'summary':'Notification ledger with recipient, related record, and read status.', 'records':[{'id':n.pk,'title':n.title,'subtitle':n.message,'badge':'Read' if n.is_read else 'Unread','href':f'/admin-dashboard/notifications/{n.pk}','meta':[f'To {n.recipient.get_full_name() or n.recipient.username} (@{n.recipient.username})',f'Type {n.get_notification_type_display()}',f'Created {timezone.localtime(n.created_at).strftime("%b %d, %Y · %I:%M %p")}',f'Related item: {n.related_item.title}' if n.related_item_id else (f'Related claim #{n.related_claim_id}' if n.related_claim_id else 'No related record')]} for n in rows]}
    return {**base, 'mode':'dashboard', 'title':'Admin workspace', 'summary':'Manage your community’s lost and found activity.', 'links':[{'label':'Admin overview','href':'/admin-dashboard'},{'label':'Users','href':'/admin-dashboard/users'},{'label':'Items','href':'/admin-dashboard/items'},{'label':'Claims','href':'/admin-dashboard/claims'},{'label':'Categories','href':'/admin-dashboard/categories'},{'label':'Matches','href':'/admin-dashboard/matches'},{'label':'Reports','href':'/reports'}]}


@require_GET
def frontend_page_data(request):
    """Return the data needed by a React page without rendering a Django template."""
    path = '/' + request.GET.get('path', '').strip('/')
    if path == '/':
        return JsonResponse({'mode':'dashboard','title':'Find your way back to what matters.','summary':'Browse community reports and help lost things find their way home.','links':[{'label':'Explore items','href':'/browse'},{'label':'How it works','href':'/how-it-works'},{'label':'Our community','href':'/community'}]})

    if path in ['/items', '/items/lost', '/items/found', '/browse']:
        items = Item.objects.filter(status=Item.STATUS_ACTIVE).select_related('category', 'reporter__profile').order_by('-created_at')
        kind = {'/items/lost':'LOST','/items/found':'FOUND'}.get(path) or request.GET.get('type','').upper()
        if kind in (Item.TYPE_LOST, Item.TYPE_FOUND):
            items = items.filter(item_type=kind)
        category_id = request.GET.get('category', '').strip()
        if category_id.isdigit():
            items = items.filter(category_id=int(category_id))
        query = request.GET.get('q','').strip()
        if query:
            items = items.filter(Q(title__icontains=query)|Q(description__icontains=query)|Q(location__icontains=query)|Q(category__name__icontains=query))
        paginator = Paginator(items, 24)
        page_obj = paginator.get_page(request.GET.get('page'))
        records = [_item_card(item, request) for item in page_obj.object_list]
        return JsonResponse({'mode':'list','eyebrow':'Community board','title':'Explore items','summary':f'{paginator.count} active reports from your community.','records':records,'categories':list(Category.objects.order_by('name').values('id','name')),'page':page_obj.number,'num_pages':paginator.num_pages,'has_previous':page_obj.has_previous(),'has_next':page_obj.has_next()})

    item_match = re.fullmatch(r'/items/(\d+)', path)
    item_report = re.fullmatch(r'/items/(\d+)/report', path)
    if item_report:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        item = Item.objects.filter(pk=item_report.group(1), status=Item.STATUS_ACTIVE).first()
        if not item or item.reporter_id == request.user.pk:
            return JsonResponse({'detail':'Report form is not available.'}, status=404)
        return JsonResponse({'mode':'form','title':f'Report a concern about {item.title}','summary':'Send this concern to the moderation queue. An administrator will review it.','action':f'/items/{item.pk}/report','actionLabel':'Submit report','links':[{'label':'Back to item','href':f'/items/{item.pk}'}],'fields':[{'name':'reason','label':'Reason','type':'select','required':True,'options':[{'value':key,'label':label} for key,label in AbuseReport.REASON_CHOICES]},{'name':'details','label':'Details','type':'textarea','required':True}]})

    if item_match:
        item = Item.objects.select_related('category','reporter').filter(pk=item_match.group(1)).first()
        if not item:
            return JsonResponse({'detail':'Item not found.'}, status=404)
        is_admin = request.user.is_authenticated and (request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN)
        links = [{'label': 'Back to Explore', 'href': '/browse'}]
        is_owner = request.user.is_authenticated and item.reporter_id == request.user.pk
        if is_admin or is_owner:
            links.extend([
                {'label': 'Edit report', 'href': f'/items/{item.pk}/edit'},
                {'label': 'Archive report' if item.status == Item.STATUS_ACTIVE else 'Restore report', 'href': f'/items/{item.pk}/archive' if item.status == Item.STATUS_ACTIVE else f'/items/{item.pk}/restore'},
            ])
            if item.item_type == Item.TYPE_FOUND:
                links.append({'label': 'View claims', 'href': f'/claims/item/{item.pk}'})
        elif item.item_type == Item.TYPE_FOUND and item.status == Item.STATUS_ACTIVE:
            links.append({'label': 'Submit a claim', 'href': f'/claims/item/{item.pk}/submit'})
        if request.user.is_authenticated and not is_owner and item.status == Item.STATUS_ACTIVE:
            links.append({'label': 'Report a concern', 'href': f'/items/{item.pk}/report'})
        is_approved_claimant = request.user.is_authenticated and Claim.objects.filter(item=item, claimant=request.user, status=Claim.STATUS_APPROVED).exists()
        detail_stats=[('Category',item.category.name if item.category else 'Uncategorized'),('Location',item.location),('Date',item.date_occurred.isoformat()),('Status',item.get_status_display())]
        if is_admin or is_owner or is_approved_claimant:
            detail_stats.extend([(label, value) for label, value in [('Building',item.building),('Room',item.room),('Nearby landmark',item.workstation)] if value])
        if is_admin:
            detail_stats.extend([('Reported by',f'{item.reporter.get_full_name() or item.reporter.username} (@{item.reporter.username})'),('Report submitted',timezone.localtime(item.created_at).strftime('%b %d, %Y · %I:%M %p')),('Last updated',timezone.localtime(item.updated_at).strftime('%b %d, %Y · %I:%M %p'))])
        summary = item.description
        if request.GET.get('reported') == '1':
            summary += ' Your concern was sent to the moderation queue.'
        return JsonResponse({'mode':'detail','title':item.title,'eyebrow':item.get_item_type_display(),'summary':summary,'image':item.image.url if item.image else None,'stats':_stats(detail_stats),'links':links})

    if path in ['/dashboard','/items/my-reports','/claims/my','/matches','/notifications','/profile']:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        user = request.user
        if path == '/dashboard':
            mine = Item.objects.filter(reporter=user)
            claims = Claim.objects.filter(claimant=user)
            community_items = Item.objects.filter(status=Item.STATUS_ACTIVE).select_related('category').order_by('-created_at')
            return JsonResponse({'mode':'dashboard','eyebrow':'Your space','userName':user.get_full_name() or user.username,'title':f"Welcome back, {user.first_name or user.username}.",'summary':'Here is what is happening with your reports.','stats':_stats([('Active reports',mine.filter(status=Item.STATUS_ACTIVE).count()),('Archived reports',mine.filter(status=Item.STATUS_ARCHIVED).count()),('My claims',claims.count()),('Possible matches',ItemMatch.objects.filter(Q(lost_item__reporter=user)|Q(found_item__reporter=user),status=ItemMatch.STATUS_PENDING).count())]),'links':[{'label':'Report lost','href':'/items/report/lost'},{'label':'Report found','href':'/items/report/found'},{'label':'My reports','href':'/items/my-reports'},{'label':'My claims','href':'/claims/my'},{'label':'Matches','href':'/matches'},{'label':'Notifications','href':'/notifications'},{'label':'My profile','href':'/profile'}],'records':[_item_card(i,request) for i in mine.order_by('-created_at')[:6]],'exploreItems':{'lost':[_item_card(i,request) for i in community_items.filter(item_type=Item.TYPE_LOST)[:6]],'found':[_item_card(i,request) for i in community_items.filter(item_type=Item.TYPE_FOUND)[:6]]}})
        if path == '/items/my-reports':
            return JsonResponse({'mode':'list','title':'My reports','summary':'Items you have reported.','records':[_item_card(i,request) for i in Item.objects.filter(reporter=user).select_related('category').order_by('-created_at')[:100]]})
        if path == '/claims/my':
            rows=Claim.objects.filter(claimant=user).select_related('item').order_by('-created_at')[:100]
            return JsonResponse({'mode':'list','title':'My claims','summary':'Updates about items you have claimed.','records':[{'id':c.pk,'title':c.item.title,'subtitle':f'{c.item.get_item_type_display()} report · {c.item.location}','badge':c.get_status_display(),'href':f'/claims/{c.pk}','meta':[f'Filed {timezone.localtime(c.created_at).strftime("%b %d, %Y")}',f'Your reason: {c.message}',f'Identifying details: {c.proof_description}']} for c in rows]})
        if path == '/matches':
            rows=ItemMatch.objects.filter(Q(lost_item__reporter=user)|Q(found_item__reporter=user)).select_related('lost_item','found_item').order_by('-created_at')[:100]
            return JsonResponse({'mode':'list','title':'Possible matches','summary':'Items that may be connected to your reports.','records':[{'id':m.pk,'title':f'{m.lost_item.title} ↔ {m.found_item.title}','subtitle':f'{m.score}% match','badge':m.get_status_display(),'href':f'/matches/{m.pk}','meta':[f'Lost report: {m.lost_item.location}',f'Found report: {m.found_item.location}',f'Suggested {timezone.localtime(m.created_at).strftime("%b %d, %Y")}']} for m in rows]})
        if path == '/notifications':
            rows=Notification.objects.filter(recipient=user).order_by('-created_at')[:100]
            return JsonResponse({'mode':'notifications','title':'Notifications','summary':'Recent updates from your community.','records':[{'id':n.pk,'title':n.title,'subtitle':n.message,'badge':'Read' if n.is_read else 'Unread','href':f'/notifications/{n.pk}','isRead':n.is_read,'meta':[f'Received {timezone.localtime(n.created_at).strftime("%b %d, %Y · %I:%M %p")}']} for n in rows], 'unreadCount':Notification.objects.filter(recipient=user,is_read=False).count()})
        profile = getattr(user, 'profile', None)
        return JsonResponse({'mode':'form','title':'Account settings','summary':'Update your personal details, contact number, and profile photo.','action':'/profile','actionLabel':'Save changes','links':[{'label':'Change password','href':'/password-change'}],'fields':[
            {'name':'first_name','label':'First name','type':'text','required':True,'value':user.first_name},
            {'name':'last_name','label':'Last name','type':'text','required':True,'value':user.last_name},
            {'name':'email','label':'Email','type':'email','required':True,'value':user.email},
            {'name':'phone','label':'Phone','type':'tel','value':getattr(getattr(user,'profile',None),'phone','')},
            {'name':'profile_image','label':'Profile photo','type':'file'},
        ], 'image':profile.profile_image.url if profile and profile.profile_image else None})

    if path == '/password-change':
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        return JsonResponse({'mode':'form','title':'Change password','summary':'Enter your current password and choose a new one.','action':'/password-change','actionLabel':'Update password','fields':[
            {'name':'old_password','label':'Current password','type':'password','required':True},
            {'name':'new_password1','label':'New password','type':'password','required':True},
            {'name':'new_password2','label':'Confirm new password','type':'password','required':True},
        ]})

    if path == '/password-change/done':
        protected = _protected(request)
        return protected or JsonResponse({'mode':'detail','title':'Password updated','summary':'Your account password was changed successfully.','links':[{'label':'Account settings','href':'/profile'}]})

    if path == '/claims/manage':
        protected=_protected(request,admin=True)
        if protected:
            return JsonResponse(protected)
        page_obj = _paginate(Claim.objects.select_related('item','claimant').order_by('-created_at'), request)
        return JsonResponse({'mode':'list','title':'Manage claims','summary':'Review ownership claims submitted by the community.','records':[{'id':c.pk,'title':c.item.title,'subtitle':f'Claim from {c.claimant.username}','badge':c.get_status_display(),'href':f'/claims/{c.pk}'} for c in page_obj.object_list], **_page_meta(page_obj)})

    claim_review=re.fullmatch(r'/claims/(\d+)/review',path)
    if claim_review:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        claim=Claim.objects.select_related('item').filter(pk=claim_review.group(1)).first()
        is_admin=request.user.is_superuser or getattr(getattr(request.user,'profile',None),'role',None)==Profile.ROLE_ADMIN
        if not claim or (claim.item.reporter_id != request.user.pk and not is_admin):
            return JsonResponse({'detail':'Claim not found.'},status=404)
        return JsonResponse({'mode':'form','title':f'Review claim for {claim.item.title}','summary':'Record your decision. The claimant will be notified.','action':path,'actionLabel':'Save claim decision','fields':[
            {'name':'reviewer_notes','label':'Reviewer notes','type':'textarea'},
            {'name':'action','label':'Decision','type':'select','required':True,'options':[{'value':'approve','label':'Approve claim'},{'value':'reject','label':'Reject claim'}]},
        ]})

    claim_handoff = re.fullmatch(r'/claims/(\d+)/handoff', path)
    if claim_handoff:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        claim = Claim.objects.select_related('item').filter(pk=claim_handoff.group(1)).first()
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        if not claim or claim.status != Claim.STATUS_APPROVED or (claim.item.reporter_id != request.user.pk and not is_admin):
            return JsonResponse({'detail': 'Pickup plan not found.'}, status=404)
        return JsonResponse({'mode':'form','title':f'Pickup plan for {claim.item.title}','summary':'Set a future time and a public campus pickup location. The claimant must confirm the plan.','action':path,'actionLabel':'Save pickup plan','fields':[
            {'name':'handoff_location','label':'Public pickup location','type':'text','required':True,'value':claim.handoff_location},
            {'name':'handoff_at','label':'Date and time','type':'datetime-local','required':True,'value':timezone.localtime(claim.handoff_at).strftime('%Y-%m-%dT%H:%M') if claim.handoff_at else ''},
            {'name':'handoff_instructions','label':'Meeting instructions','type':'textarea','value':claim.handoff_instructions},
        ]})

    claim_handoff_response = re.fullmatch(r'/claims/(\d+)/handoff/respond', path)
    if claim_handoff_response:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        claim = Claim.objects.select_related('item').filter(pk=claim_handoff_response.group(1), claimant=request.user, status=Claim.STATUS_APPROVED).first()
        if not claim or not claim.handoff_at:
            return JsonResponse({'detail':'There is no active pickup plan to respond to.'}, status=404)
        return JsonResponse({'mode':'form','title':'Respond to pickup plan','summary':f'{claim.handoff_location} · {timezone.localtime(claim.handoff_at).strftime("%b %d, %Y at %I:%M %p")}. Confirm the plan or request a change.','action':path,'actionLabel':'Send response','fields':[
            {'name':'action','label':'Your response','type':'select','required':True,'options':[{'value':'confirm','label':'Confirm this pickup plan'},{'value':'request_change','label':'Request a different time or place'}]},
            {'name':'handoff_change_request','label':'Suggested change','type':'textarea'},
        ]})

    claim_handoff_complete = re.fullmatch(r'/claims/(\d+)/handoff/confirm', path)
    if claim_handoff_complete:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        claim = Claim.objects.select_related('item').filter(pk=claim_handoff_complete.group(1), status=Claim.STATUS_APPROVED).first()
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        if not claim or not claim.handoff_at or (claim.item.reporter_id != request.user.pk and claim.claimant_id != request.user.pk and not is_admin):
            return JsonResponse({'detail':'Handoff confirmation is not available.'}, status=404)
        return JsonResponse({'mode':'action','title':'Confirm item handoff?','summary':'Only confirm after the item has physically changed hands. Both the claimant and reporter must confirm before the claim is marked complete.','action':path,'actionLabel':'Confirm item received','fields':[]})

    admin_user_detail = re.fullmatch(r'/admin-dashboard/users/(\d+)', path)
    if admin_user_detail:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        target = User.objects.select_related('profile').filter(pk=admin_user_detail.group(1)).first()
        if not target:
            return JsonResponse({'detail': 'User not found.'}, status=404)
        reported = Item.objects.filter(reporter=target)
        user_claims = Claim.objects.filter(claimant=target)
        return JsonResponse({'mode': 'detail', 'title': target.get_full_name() or target.username,
            'eyebrow': f'@{target.username} · {target.profile.get_role_display()}',
            'summary': target.email or 'No email provided',
            'stats': _stats([('Account status', 'Active' if target.is_active else 'Inactive'), ('Reports', reported.count()), ('Claims', user_claims.count()), ('Member since', target.date_joined.strftime('%b %d, %Y'))]),
            'links': [{'label': 'Change account status', 'href': f'/admin-dashboard/users/{target.pk}/toggle-status'}, {'label': 'Change role', 'href': f'/admin-dashboard/users/{target.pk}/change-role'}, {'label': 'Back to users', 'href': '/admin-dashboard/users'}]})

    user_toggle = re.fullmatch(r'/admin-dashboard/users/(\d+)/toggle-status', path)
    if user_toggle:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        target = User.objects.filter(pk=user_toggle.group(1)).first()
        if not target:
            return JsonResponse({'detail': 'User not found.'}, status=404)
        if target.pk == request.user.pk:
            return JsonResponse({'detail': 'You cannot change your own account status.'}, status=403)
        return JsonResponse({'mode': 'form', 'title': f"{'Deactivate' if target.is_active else 'Reactivate'} @{target.username}?", 'summary': 'Confirm the account status change.', 'action': f'/api/admin/users/{target.pk}/toggle-status', 'actionLabel': 'Confirm status change', 'fields': []})

    user_role = re.fullmatch(r'/admin-dashboard/users/(\d+)/change-role', path)
    if user_role:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        target = User.objects.select_related('profile').filter(pk=user_role.group(1)).first()
        if not target:
            return JsonResponse({'detail': 'User not found.'}, status=404)
        if target.pk == request.user.pk or target.is_superuser:
            return JsonResponse({'detail': 'This administrator role cannot be changed here.'}, status=403)
        return JsonResponse({'mode': 'form', 'title': f'Change role for @{target.username}', 'summary': 'Select the account role.', 'action': f'/api/admin/users/{target.pk}/change-role', 'actionLabel': 'Save role', 'fields': [
            {'name': 'role', 'label': 'Role', 'type': 'select', 'required': True, 'value': target.profile.role, 'options': [{'value': Profile.ROLE_USER, 'label': 'User'}, {'value': Profile.ROLE_ADMIN, 'label': 'Administrator'}]},
        ]})

    admin_item_action = re.fullmatch(r'/items/(\d+)/(archive|restore)', path)
    if admin_item_action:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        item_query = Item.objects.filter(pk=admin_item_action.group(1))
        if not is_admin:
            item_query = item_query.filter(reporter=request.user)
        item = item_query.first()
        if not item:
            return JsonResponse({'detail': 'Item not found.'}, status=404)
        action = admin_item_action.group(2)
        if (action == 'archive' and item.status != Item.STATUS_ACTIVE) or (action == 'restore' and item.status != Item.STATUS_ARCHIVED):
            return JsonResponse({'detail': 'This report has already changed status.'}, status=409)
        return JsonResponse({'mode': 'form', 'title': f'{action.title()} {item.title}?', 'summary': 'Confirm the report status change.', 'action': path, 'actionLabel': f'Confirm {action}', 'fields': []})

    match_action = re.fullmatch(r'/(?:admin-dashboard/)?matches/(\d+)/(confirm|dismiss)', path)
    if match_action:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        match = ItemMatch.objects.filter(pk=match_action.group(1)).first()
        if not match:
            return JsonResponse({'detail': 'Match not found.'}, status=404)
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        is_involved = request.user.pk in (match.lost_item.reporter_id, match.found_item.reporter_id)
        if not is_admin and not is_involved:
            return JsonResponse({'detail':'Match not found.'}, status=404)
        if match.status != ItemMatch.STATUS_PENDING:
            return JsonResponse({'detail':'This match has already been reviewed.'}, status=409)
        action = match_action.group(2)
        action_path = f'/matches/{match.pk}/{action}'
        return JsonResponse({'mode': 'action', 'title': f'{action.title()} this match?', 'summary': f'Confirm that you want to {action} this suggested match.', 'action': action_path, 'actionLabel': 'Confirm match' if action == 'confirm' else 'Dismiss match', 'fields': []})

    item_claims=re.fullmatch(r'/claims/item/(\d+)',path)
    if item_claims:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        item=Item.objects.filter(pk=item_claims.group(1)).first()
        if not item or (item.reporter_id != request.user.pk and not (request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN)):
            return JsonResponse({'detail':'Claims not found.'},status=404)
        page_obj = _paginate(item.claims.select_related('claimant').order_by('-created_at'), request)
        return JsonResponse({'mode':'list','title':f'Claims for {item.title}','summary':'Ownership claims submitted for this report.','records':[{'id':c.pk,'title':c.claimant.get_full_name() or c.claimant.username,'subtitle':c.message,'badge':c.get_status_display(),'href':f'/claims/{c.pk}'} for c in page_obj.object_list], **_page_meta(page_obj)})

    if path in ['/items/report/lost','/items/report/found']:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        return JsonResponse({'mode':'form','title':'Report a '+('lost' if path.endswith('lost') else 'found')+' item','summary':'A few clear details help your community recognize it.','action':path,'actionLabel':'Submit lost report' if path.endswith('lost') else 'Submit found report','fields':[
            {'name':'title','label':'Item name','type':'text','required':True},{'name':'description','label':'Description','type':'textarea','required':True},
            {'name':'category','label':'Category','type':'select','required':True,'options':[{'value':c.pk,'label':c.name} for c in Category.objects.order_by('name')]},
            {'name':'location','label':'Location','type':'select','required':True,'placeholder':'Select a campus','options':_location_options(ReportLocation.CAMPUS, LOCATION_CHOICES)},
            {'name':'building','label':'Building','type':'select','placeholder':'Select a building','options':_location_options(ReportLocation.BUILDING, BUILDING_CHOICES)},
            {'name':'room','label':'Room / Computer Lab','type':'select','placeholder':'Select a room or computer lab','options':_location_options(ReportLocation.ROOM, ROOM_CHOICES)},
            {'name':'workstation','label':'Nearby landmark or workstation (optional)','type':'text'},
            {'name':'date_occurred','label':'Date','type':'date','required':True},{'name':'approximate_time','label':'Approximate time','type':'time'},
            {'name':'image','label':'Photo','type':'file'},
        ]})

    category_form = re.fullmatch(r'/(?:admin-dashboard/)?categories/(?:add|new|\d+/edit)', path) or re.fullmatch(r'/items/categories/(?:add|\d+/edit)', path)
    if category_form:
        protected=_protected(request,admin=True)
        if protected:
            return JsonResponse(protected)
        category_id=re.search(r'/(\d+)/edit$',path)
        category=Category.objects.filter(pk=category_id.group(1)).first() if category_id else None
        links = [{'label': 'Delete category', 'href': f'/admin-dashboard/categories/{category.pk}/delete'}] if category else []
        category_action = f'/api/admin/categories/{category.pk}/edit' if category else '/api/admin/categories/add'
        return JsonResponse({'mode':'form','title':'Edit category' if category else 'Add a category','summary':'Use a clear name so people can find reports quickly.','action':category_action,'links':links,'actionLabel':'Save category','fields':[
            {'name':'name','label':'Category name','type':'text','required':True,'value':category.name if category else ''},
            {'name':'description','label':'Description','type':'textarea','value':category.description if category else ''},
        ]})

    location_form = re.fullmatch(r'/admin-dashboard/locations/(?:add|\d+/edit)', path)
    if location_form:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        match = re.search(r'/locations/(\d+)/edit$', path)
        location = ReportLocation.objects.filter(pk=match.group(1)).first() if match else None
        location_action = f'/api/admin/locations/{location.pk}/edit' if location else '/api/admin/locations/add'
        return JsonResponse({'mode':'form','title':'Edit report location' if location else 'Add report location','summary':'Add a campus, building, room, or computer lab option to the report form.','action':location_action,'actionLabel':'Save location','fields':[
            {'name':'name','label':'Location name','type':'text','required':True,'value':location.name if location else ''},
            {'name':'kind','label':'Field type','type':'select','required':True,'value':location.kind if location else '', 'options':[{'value':kind,'label':label} for kind,label in ReportLocation.KIND_CHOICES]},
            {'name':'active','label':'Active (1 = available, 0 = hidden)','type':'select','required':True,'value':'1' if not location or location.active else '0','options':[{'value':'1','label':'Active'}, {'value':'0','label':'Inactive'}]},
        ]})

    category_delete = re.fullmatch(r'/admin-dashboard/categories/(\d+)/delete', path)
    if category_delete:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        category = Category.objects.filter(pk=category_delete.group(1)).first()
        if not category:
            return JsonResponse({'detail': 'Category not found.'}, status=404)
        if category.items.exists():
            return JsonResponse({'mode': 'detail', 'title': 'Category is still in use', 'summary': 'This category still contains reports and cannot be deleted. Reassign or remove those reports first.', 'links': [{'label': 'Back to categories', 'href': '/admin-dashboard/categories'}]})
        return JsonResponse({'mode': 'form', 'title': f'Delete {category.name}?', 'summary': 'This action cannot be undone.', 'action': f'/api/admin/categories/{category.pk}/delete', 'actionLabel': 'Delete category', 'fields': [], 'links': [{'label': 'Cancel', 'href': '/admin-dashboard/categories'}]})

    if path in ['/items/categories','/admin-dashboard/categories']:
        protected=_protected(request,admin=True)
        if protected:
            return JsonResponse(protected)
        rows=Category.objects.annotate(report_total=Count('items'),lost_total=Count('items',filter=Q(items__item_type=Item.TYPE_LOST)),found_total=Count('items',filter=Q(items__item_type=Item.TYPE_FOUND))).order_by('name')
        return JsonResponse({'mode':'list','title':'Item categories','summary':'Category register with report volume by type and the date each category was created.','records':[{'id':c.pk,'title':c.name,'subtitle':c.description or 'No description','badge':f'{c.report_total} reports','href':f'/admin-dashboard/categories/{c.pk}/edit','meta':[f'{c.lost_total} lost reports',f'{c.found_total} found reports',f'Created {timezone.localtime(c.created_at).strftime("%b %d, %Y")}']} for c in rows],'links':[{'label':'Add category','href':'/admin-dashboard/categories/add'}]})

    edit_item = re.fullmatch(r'/items/(\d+)/edit',path)
    if edit_item:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        item_query = Item.objects.filter(pk=edit_item.group(1))
        if not is_admin:
            item_query = item_query.filter(reporter=request.user)
        item=item_query.first()
        if not item:
            return JsonResponse({'detail':'Item not found.'},status=404)
        return JsonResponse({'mode':'form','title':'Edit report','summary':'Update the details for your item.','action':path,'actionLabel':'Save changes','fields':[
            {'name':'title','label':'Item name','type':'text','required':True,'value':item.title},
            {'name':'description','label':'Description','type':'textarea','required':True,'value':item.description},
            {'name':'category','label':'Category','type':'select','required':True,'value':item.category_id or '', 'options':[{'value':c.pk,'label':c.name} for c in Category.objects.order_by('name')]},
            {'name':'location','label':'Location','type':'select','required':True,'value':item.location,'placeholder':'Select a campus','options':_location_options(ReportLocation.CAMPUS, LOCATION_CHOICES)},
            {'name':'building','label':'Building','type':'select','value':item.building,'placeholder':'Select a building','options':_location_options(ReportLocation.BUILDING, BUILDING_CHOICES)},
            {'name':'room','label':'Room / Computer Lab','type':'select','value':item.room,'placeholder':'Select a room or computer lab','options':_location_options(ReportLocation.ROOM, ROOM_CHOICES)},
            {'name':'workstation','label':'Nearby landmark','type':'text','value':item.workstation},
            {'name':'date_occurred','label':'Date','type':'date','required':True,'value':item.date_occurred.isoformat()},
            {'name':'approximate_time','label':'Approximate time','type':'time','value':item.approximate_time.strftime('%H:%M') if item.approximate_time else ''},
            {'name':'image','label':'Photo','type':'file'},
        ]})

    if path == '/logout':
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        return JsonResponse({'mode':'action','title':'Sign out of Findly?','summary':'You can sign back in any time.','action':'/logout','actionLabel':'Sign out'})

    match_detail=re.fullmatch(r'/matches/(\d+)',path)
    if match_detail:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        match=ItemMatch.objects.select_related('lost_item','found_item').filter(pk=match_detail.group(1)).first()
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        if not match or request.user.pk not in (match.lost_item.reporter_id,match.found_item.reporter_id) and not is_admin:
            return JsonResponse({'detail':'Match not found.'},status=404)
        links = [{'label':'Lost item','href':f'/items/{match.lost_item_id}'},{'label':'Found item','href':f'/items/{match.found_item_id}'}]
        is_involved = request.user.pk in (match.lost_item.reporter_id, match.found_item.reporter_id)
        if (is_admin or is_involved) and match.status == ItemMatch.STATUS_PENDING:
            links.extend([{'label':'Confirm match','href':f'/matches/{match.pk}/confirm'}, {'label':'Dismiss match','href':f'/matches/{match.pk}/dismiss'}])
        return JsonResponse({'mode':'detail','title':'Possible match','eyebrow':f'{match.score}% match · {match.get_status_display()}','summary':f'{match.lost_item.title} may be the same item as {match.found_item.title}. Photo similarity adds up to 20 points when both reports include photos.','stats':_stats([('Overall match',f'{match.score}%'),('Category',match.score_category),('Location',match.score_location),('Title',match.score_title),('Description',match.score_description),('Date',match.score_date),('Photo similarity',f'{match.score_image}/20')]),'links':links})

    admin_notification_detail = re.fullmatch(r'/admin-dashboard/notifications/(\d+)', path)
    if admin_notification_detail:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        notification = Notification.objects.select_related('recipient','related_item','related_claim').filter(pk=admin_notification_detail.group(1)).first()
        if not notification:
            return JsonResponse({'detail':'Notification not found.'}, status=404)
        details = [('Recipient', f'{notification.recipient.get_full_name() or notification.recipient.username} (@{notification.recipient.username})'), ('Type', notification.get_notification_type_display()), ('Status', 'Read' if notification.is_read else 'Unread'), ('Created', timezone.localtime(notification.created_at).strftime('%b %d, %Y · %I:%M %p'))]
        if notification.related_item_id:
            details.append(('Related item', notification.related_item.title))
        if notification.related_claim_id:
            details.append(('Related claim', f'#{notification.related_claim_id}'))
        return JsonResponse({'mode':'detail','title':notification.title,'summary':notification.message,'stats':_stats(details)})

    notification_detail=re.fullmatch(r'/notifications/(\d+)',path)
    if notification_detail:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        notification=Notification.objects.filter(pk=notification_detail.group(1),recipient=request.user).first()
        if not notification:
            return JsonResponse({'detail':'Notification not found.'},status=404)
        links = [{'label':'Notifications','href':'/notifications'}]
        if not notification.is_read:
            links.insert(0, {'label':'Mark as read','href':f'/notifications/{notification.pk}/read'})
        return JsonResponse({'mode':'detail','title':notification.title,'eyebrow':'Read' if notification.is_read else 'Unread','summary':notification.message,'links':links})

    notification_action = re.fullmatch(r'/notifications/(\d+)/(read|delete)', path)
    if notification_action:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        notification = Notification.objects.filter(pk=notification_action.group(1), recipient=request.user).first()
        if not notification:
            return JsonResponse({'detail': 'Notification not found.'}, status=404)
        action = notification_action.group(2)
        return JsonResponse({'mode':'action','title':f'{action.title()} notification','summary':notification.title,'action':path,'actionLabel':f'{action.title()} notification','fields':[]})

    if path == '/notifications/mark-all-read':
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        return JsonResponse({'mode':'action','title':'Mark all as read','summary':'Mark every unread notification in your account as read.','action':path,'actionLabel':'Mark all as read','fields':[]})

    claim_withdraw = re.fullmatch(r'/claims/(\d+)/withdraw', path)
    if claim_withdraw:
        protected = _protected(request)
        if protected:
            return JsonResponse(protected)
        claim = Claim.objects.select_related('item').filter(pk=claim_withdraw.group(1), claimant=request.user, status=Claim.STATUS_PENDING).first()
        if not claim:
            return JsonResponse({'detail':'Only your pending claims can be withdrawn.'}, status=404)
        return JsonResponse({'mode':'action','title':f'Withdraw claim for {claim.item.title}?','summary':'The item reporter will be notified that you withdrew this claim.','action':path,'actionLabel':'Withdraw claim','fields':[]})

    if path == '/password-reset':
        return JsonResponse({'mode':'form','title':'Reset your password','summary':'Enter the email address on your account. If it exists, Django will send password reset instructions.','action':'/password-reset','actionLabel':'Send reset instructions','fields':[{'name':'email','label':'Email address','type':'email','required':True}]})
    if path in ['/password-reset/done','/password-reset/complete']:
        return JsonResponse({'mode':'detail','title':'Password reset request received','summary':'If that email matches an account, password reset instructions have been sent. You can return to sign in.','links':[{'label':'Sign in','href':'/login'}]})
    reset_confirm = re.fullmatch(r'/password-reset/([^/]+)/([^/]+)', path)
    if reset_confirm:
        return JsonResponse({'mode':'form','title':'Choose a new password','summary':'Enter and confirm your new password.','action':path,'actionLabel':'Update password','fields':[{'name':'new_password1','label':'New password','type':'password','required':True},{'name':'new_password2','label':'Confirm new password','type':'password','required':True}]})

    if path == '/reports':
        protected=_protected(request,admin=True)
        if protected:
            return JsonResponse(protected)
        return JsonResponse({'mode':'dashboard','title':'Community reports','summary':'Live report volumes, category performance, and claim outcomes from your community data.','stats':_stats([('All reports',Item.objects.count()),('Lost reports',Item.objects.filter(item_type=Item.TYPE_LOST).count()),('Found reports',Item.objects.filter(item_type=Item.TYPE_FOUND).count()),('Claims filed',Claim.objects.count()),('Claims resolved',Claim.objects.filter(status__in=[Claim.STATUS_APPROVED, Claim.STATUS_REJECTED]).count()),('Community members',User.objects.count())]),'trends':_admin_report_trends(),'categoryBreakdown':_admin_category_breakdown(8),'claimStatusCounts':_admin_claim_status_counts(),'adminActivity':_admin_recent_activity(request, 8),'links':[{'label':'Export items CSV','href':'/api/django/reports/items/export/'},{'label':'Export claims CSV','href':'/api/django/reports/claims/export/'},{'label':'Export users CSV','href':'/api/django/reports/users/export/'},{'label':'Export categories CSV','href':'/api/django/reports/categories/export/'},{'label':'Export matches CSV','href':'/api/django/reports/matches/export/'},{'label':'Admin overview','href':'/admin-dashboard'}]})

    claim_submit = re.fullmatch(r'/claims/item/(\d+)/submit', path)
    if claim_submit:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        item=Item.objects.filter(pk=claim_submit.group(1),item_type=Item.TYPE_FOUND,status=Item.STATUS_ACTIVE).first()
        if not item:
            return JsonResponse({'detail':'This found item is not available for claims.'},status=404)
        return JsonResponse({'mode':'form','title':f'Claim {item.title}','summary':'Share details that help confirm this item belongs to you.','action':path,'actionLabel':'Submit claim','fields':[
            {'name':'message','label':'Why do you believe this item belongs to you?','type':'textarea','required':True},
            {'name':'proof_description','label':'Describe identifying details','type':'textarea','required':True},
        ]})

    claim_detail=re.fullmatch(r'/claims/(\d+)',path)
    if claim_detail:
        protected=_protected(request)
        if protected:
            return JsonResponse(protected)
        claim=Claim.objects.select_related('item','claimant').filter(pk=claim_detail.group(1)).first()
        if not claim or (claim.claimant_id != request.user.pk and claim.item.reporter_id != request.user.pk and not (request.user.is_superuser or getattr(getattr(request.user,'profile',None),'role',None)==Profile.ROLE_ADMIN)):
            return JsonResponse({'detail':'Claim not found.'},status=404)
        links = []
        if claim.status == Claim.STATUS_PENDING and (request.user.is_superuser or getattr(getattr(request.user,'profile',None),'role',None)==Profile.ROLE_ADMIN or claim.item.reporter_id == request.user.pk):
            links.append({'label':'Review claim','href':f'/claims/{claim.pk}/review'})
        if claim.status == Claim.STATUS_PENDING and claim.claimant_id == request.user.pk:
            links.append({'label':'Withdraw claim','href':f'/claims/{claim.pk}/withdraw'})
        is_reporter = claim.item.reporter_id == request.user.pk
        is_claimant = claim.claimant_id == request.user.pk
        is_admin = request.user.is_superuser or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
        if claim.status == Claim.STATUS_APPROVED:
            if not claim.handoff_completed_at and (is_reporter or is_admin):
                links.append({'label':'Set or update pickup plan','href':f'/claims/{claim.pk}/handoff'})
            if not claim.handoff_completed_at and claim.handoff_at and is_claimant and not claim.handoff_confirmed_by_claimant_at:
                links.append({'label':'Confirm or request a change','href':f'/claims/{claim.pk}/handoff/respond'})
            if not claim.handoff_completed_at and claim.handoff_at and claim.handoff_confirmed_by_claimant_at and (is_reporter or is_claimant or is_admin):
                already_confirmed = claim.handoff_returned_by_claimant_at if is_claimant else claim.handoff_returned_by_reporter_at
                if not already_confirmed:
                    links.append({'label':'Confirm item handoff','href':f'/claims/{claim.pk}/handoff/confirm'})
        claim_stats=[('Claimant',f'{claim.claimant.get_full_name() or claim.claimant.username} (@{claim.claimant.username})'),('Status',claim.get_status_display()),('Proof',claim.proof_description),('Submitted',timezone.localtime(claim.created_at).strftime('%b %d, %Y · %I:%M %p'))]
        if claim.status == Claim.STATUS_APPROVED:
            if claim.handoff_completed_at:
                handoff_status = f'Complete · {timezone.localtime(claim.handoff_completed_at).strftime("%b %d, %Y %I:%M %p")}'
            elif not claim.handoff_at:
                handoff_status = 'Waiting for reporter to set a pickup plan'
            elif claim.handoff_change_request:
                handoff_status = 'Claimant requested a change'
            elif not claim.handoff_confirmed_by_claimant_at:
                handoff_status = 'Waiting for claimant to confirm the plan'
            elif claim.handoff_returned_by_claimant_at and not claim.handoff_returned_by_reporter_at:
                handoff_status = 'Claimant confirmed receipt · waiting for reporter'
            elif claim.handoff_returned_by_reporter_at and not claim.handoff_returned_by_claimant_at:
                handoff_status = 'Reporter confirmed handoff · waiting for claimant'
            else:
                handoff_status = 'Pickup plan confirmed · waiting for handoff'
            claim_stats.append(('Handoff status', handoff_status))
            if claim.handoff_at:
                claim_stats.extend([
                    ('Pickup location', claim.handoff_location),
                    ('Pickup time', timezone.localtime(claim.handoff_at).strftime('%b %d, %Y at %I:%M %p')),
                ])
                if claim.handoff_instructions:
                    claim_stats.append(('Meeting instructions', claim.handoff_instructions))
            if claim.handoff_change_request:
                claim_stats.append(('Requested change', claim.handoff_change_request))
            if claim.handoff_at:
                claim_stats.extend([
                    ('Claimant confirmed return', 'Yes' if claim.handoff_returned_by_claimant_at else 'No'),
                    ('Reporter confirmed return', 'Yes' if claim.handoff_returned_by_reporter_at else 'No'),
                ])
        if request.user.is_superuser or getattr(getattr(request.user,'profile',None),'role',None)==Profile.ROLE_ADMIN:
            claim_stats.extend([('Review decision',claim.get_status_display()),('Reviewed by',(claim.reviewed_by.get_full_name() or claim.reviewed_by.username) if claim.reviewed_by_id else 'Awaiting reviewer'),('Reviewed at',timezone.localtime(claim.reviewed_at).strftime('%b %d, %Y · %I:%M %p') if claim.reviewed_at else 'No decision recorded'),('Reviewer notes',claim.reviewer_notes or 'No reviewer note recorded'),('Related report',f'{claim.item.get_item_type_display()} · {claim.item.title} · reported by @{claim.item.reporter.username}')])
        return JsonResponse({'mode':'detail','title':f'Claim for {claim.item.title}','eyebrow':claim.get_status_display(),'summary':claim.message,'stats':_stats(claim_stats),'links':links})

    flag_detail = re.fullmatch(r'/admin-dashboard/flags/(\d+)', path)
    if flag_detail:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        flag = AbuseReport.objects.select_related('item', 'submitted_by', 'reviewed_by').filter(pk=flag_detail.group(1)).first()
        if not flag:
            return JsonResponse({'detail':'Report not found.'}, status=404)
        links = [{'label':'Open item report','href':f'/items/{flag.item_id}'}]
        if flag.status == AbuseReport.STATUS_OPEN:
            links.extend([{'label':'Mark reviewed','href':f'/admin-dashboard/flags/{flag.pk}/review'},{'label':'Dismiss report','href':f'/admin-dashboard/flags/{flag.pk}/dismiss'}])
        stats = _stats([('Reason',flag.get_reason_display()),('Status',flag.get_status_display()),('Submitted by',f'@{flag.submitted_by.username}'),('Item',f'#{flag.item_id} · {flag.item.title}'),('Submitted',timezone.localtime(flag.created_at).strftime('%b %d, %Y · %I:%M %p')),('Reviewed by',f'@{flag.reviewed_by.username}' if flag.reviewed_by_id else 'Not reviewed'),('Moderator notes',flag.reviewer_notes or 'None')])
        return JsonResponse({'mode':'detail','title':f'Report about {flag.item.title}','eyebrow':flag.get_status_display(),'summary':flag.details,'stats':stats,'links':links})

    flag_action = re.fullmatch(r'/admin-dashboard/flags/(\d+)/(review|dismiss)', path)
    if flag_action:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        flag = AbuseReport.objects.filter(pk=flag_action.group(1)).first()
        if not flag:
            return JsonResponse({'detail':'Report not found.'}, status=404)
        operation = flag_action.group(2)
        title = 'Mark report reviewed' if operation == 'review' else 'Dismiss report'
        summary = 'Record that the concern was reviewed.' if operation == 'review' else 'Close this report without further action.'
        return JsonResponse({'mode':'action','title':title,'summary':summary,'action':f'/api/admin/flags/{flag.pk}/{operation}','actionLabel':'Confirm','fields':[]})

    audit_detail = re.fullmatch(r'/admin-dashboard/audit/(\d+)', path)
    if audit_detail:
        protected = _protected(request, admin=True)
        if protected:
            return JsonResponse(protected)
        event = AuditEvent.objects.select_related('actor').filter(pk=audit_detail.group(1)).first()
        if not event:
            return JsonResponse({'detail': 'Activity record not found.'}, status=404)
        stats = [
            ('Action', event.action),
            ('Target type', event.object_type),
            ('Target ID', event.object_id or 'Not recorded'),
            ('Actor', (event.actor.get_full_name() or event.actor.username) if event.actor_id else 'System'),
            ('Recorded', timezone.localtime(event.created_at).strftime('%b %d, %Y ? %I:%M %p')),
        ]
        return JsonResponse({'mode':'detail','title':event.action.replace('.', ' ').title(),'eyebrow':'Activity log','summary':event.summary,'stats':_stats(stats),'links':[{'label':'Back to activity log','href':'/admin-dashboard/activity'}]})

    if path.startswith('/admin-dashboard'):
        protected=_protected(request,admin=True)
        if protected:
            return JsonResponse(protected)
        return JsonResponse(_admin_payload(path, request))

    return JsonResponse({'detail':'No React page data is available for this route yet.'}, status=404)
