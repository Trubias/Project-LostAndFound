"""Authenticated live suggestions for either report type."""
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from items.models import Category, Item
from accounts.models import Profile
from claims.models import Claim
from matches.engine import MATCH_THRESHOLD, calculate_score
from matches.image_similarity import image_similarity
from config.validators import validate_image_upload


@require_POST
def match_suggestions(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Sign in to see possible matches.'}, status=401)

    uploaded_image = request.FILES.get('image')
    if uploaded_image:
        try:
            validate_image_upload(uploaded_image)
        except ValidationError as exc:
            return JsonResponse({'detail': exc.messages[0]}, status=400)
    report_type = request.POST.get('item_type', Item.TYPE_FOUND).upper()
    if report_type not in (Item.TYPE_LOST, Item.TYPE_FOUND):
        report_type = Item.TYPE_FOUND
    candidate_type = Item.TYPE_LOST if report_type == Item.TYPE_FOUND else Item.TYPE_FOUND
    category_id = request.POST.get('category')
    category = Category.objects.filter(pk=category_id).first() if category_id else None
    report = Item(
        title=request.POST.get('title', ''),
        description=request.POST.get('description', ''),
        item_type=report_type,
        category=category,
        location=request.POST.get('location', ''),
        building=request.POST.get('building', ''),
        room=request.POST.get('room', ''),
        workstation=request.POST.get('workstation', ''),
        date_occurred=parse_date(request.POST.get('date_occurred', '')),
        reporter=request.user,
    )
    if uploaded_image:
        report.image = uploaded_image

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or bool(profile and profile.role == Profile.ROLE_ADMIN)
    candidates = Item.objects.filter(
        item_type=candidate_type,
        status=Item.STATUS_ACTIVE,
    ).select_related('category').order_by('-created_at')
    if not is_admin:
        candidates = candidates.annotate(_has_approved_claim=Exists(Claim.objects.filter(
            item_id=OuterRef('pk'), claimant=request.user, status=Claim.STATUS_APPROVED,
        )))
    candidates = candidates[:200]
    suggestions = []
    for lost in candidates:
        breakdown = calculate_score(lost, report)
        photo_similarity = image_similarity(lost.image, uploaded_image) if lost.image and uploaded_image else 0
        if breakdown['total'] < MATCH_THRESHOLD and photo_similarity < 75:
            continue
        suggestions.append({
            'id': lost.pk,
            'title': lost.title,
            'description': lost.description,
            'location': lost.location,
            'room': lost.room if (
                is_admin or lost.reporter_id == request.user.pk
                or getattr(lost, '_has_approved_claim', False)
            ) else '',
            'category': lost.category.name if lost.category else 'Uncategorized',
            'image': lost.image.url if lost.image else None,
            'href': f'/items/{lost.pk}',
            'score': breakdown['total'],
            'photoSimilarity': photo_similarity,
            'photoMatch': photo_similarity >= 75,
        })
    suggestions.sort(key=lambda item: (item['photoMatch'], item['score'], item['photoSimilarity']), reverse=True)
    return JsonResponse({'results': suggestions[:4]})
