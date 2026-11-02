"""
Lost/Found item matching engine.

Scoring rules (maximum 100 points):
┌─────────────────────┬───────────────────────────────────────────┐
│ Component           │ Max points                                │
├─────────────────────┼───────────────────────────────────────────┤
│ Category match      │ 30                                        │
│ Location match      │ 25                                        │
│ Title similarity    │ 20                                        │
│ Description sim.    │ 15                                        │
│ Date closeness      │ 10                                        │
└─────────────────────┴───────────────────────────────────────────┘

Date scoring (within score_date):
    Same day        → 10 pts
    1 day apart     →  8 pts
    2 days apart    →  5 pts
    3 days apart    →  3 pts
    > 3 days apart  →  0 pts
    Either date None→  0 pts

Only item pairs where:
    • one is TYPE_LOST and the other is TYPE_FOUND
    • both are STATUS_ACTIVE
    • total score >= MATCH_THRESHOLD (see settings)
are stored as ItemMatch records.
"""

import re
import unicodedata
from difflib import SequenceMatcher
from datetime import date
from django.db.models import Q

from django.conf import settings

from .models import ItemMatch
from .image_similarity import image_similarity

MATCH_THRESHOLD = getattr(settings, 'MATCH_THRESHOLD', 50)

# ── Scoring constants ─────────────────────────────────────────────────────────
MAX_CATEGORY    = 30
MAX_LOCATION    = 25
MAX_TITLE       = 20
MAX_DESCRIPTION = 15
MAX_DATE        = 10

# Common short words to exclude from similarity comparison (stopwords).
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'is', 'it', 'my', 'i', 'me', 'was', 'by', 'with', 'that', 'this',
    'have', 'had', 'has', 'be', 'been', 'are', 'were', 'not', 'no', 'so',
}

# Small, deterministic English/Filipino vocabulary normalization. These only
# affect candidate ranking; every match still requires human review.
TOKEN_SYNONYMS = {
    'cellphone': 'phone', 'cellphones': 'phone', 'celphone': 'phone',
    'smartphone': 'phone', 'mobile': 'phone', 'selpon': 'phone',
    'backpack': 'bag', 'backpacks': 'bag', 'knapsack': 'bag',
    'bagpack': 'bag', 'slingbag': 'bag', 'shoulderbag': 'bag',
    'pitaka': 'wallet', 'purse': 'wallet', 'wallets': 'wallet',
    'payong': 'umbrella', 'umbrellas': 'umbrella',
    'tumbler': 'bottle', 'waterbottle': 'bottle', 'bote': 'bottle',
    'susi': 'key', 'keys': 'key', 'sapatos': 'shoe', 'shoes': 'shoe',
    'itim': 'black', 'puti': 'white', 'pula': 'red', 'asul': 'blue',
    'bughaw': 'blue', 'berde': 'green', 'dilaw': 'yellow',
}


# ── Text utilities ────────────────────────────────────────────────────────────

def _tokenize(text):
    """Normalize accents and common synonyms into non-stopword tokens."""
    if not text:
        return set()
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r'[^\w\s]', ' ', text)
    words = {
        TOKEN_SYNONYMS.get(word, word) for word in text.split()
        if word and word not in STOPWORDS and (len(word) > 1 or word.isdigit())
    }
    return words


def _jaccard(set_a, set_b):
    """Weighted Jaccard with one-to-one typo tolerance for longer tokens."""
    if not set_a and not set_b:
        return 0.0
    remaining_a = set(set_a)
    remaining_b = set(set_b)
    overlap = len(remaining_a & remaining_b)
    remaining_a -= remaining_b
    remaining_b -= set(set_a)

    fuzzy_pairs = []
    for token_a in remaining_a:
        if len(token_a) < 4:
            continue
        for token_b in remaining_b:
            if len(token_b) < 4:
                continue
            similarity = SequenceMatcher(None, token_a, token_b, autojunk=False).ratio()
            if similarity >= 0.86:
                fuzzy_pairs.append((similarity, token_a, token_b))

    matched_a = set()
    matched_b = set()
    for similarity, token_a, token_b in sorted(fuzzy_pairs, reverse=True):
        if token_a not in matched_a and token_b not in matched_b:
            overlap += similarity
            matched_a.add(token_a)
            matched_b.add(token_b)

    union = len(set_a) + len(set_b) - overlap
    return overlap / union if union else 0.0


def _word_overlap_score(text_a, text_b, max_points):
    """
    Return a score in [0, max_points] based on word-level Jaccard similarity
    between two text values, ignoring stopwords.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    similarity = _jaccard(tokens_a, tokens_b)
    return round(similarity * max_points)


# ── Scoring functions ─────────────────────────────────────────────────────────

def score_category(item_a, item_b):
    """30 pts if both items share the same non-null category."""
    if item_a.category_id and item_b.category_id:
        if item_a.category_id == item_b.category_id:
            return MAX_CATEGORY
    return 0


def score_location(item_a, item_b):
    """
    Compare free-text location and any structured building/room/workstation
    details together. Exact normalized detail matches receive full points;
    partial word overlap receives a proportional score.
    """
    location_fields = ('location', 'building', 'room', 'workstation')
    loc_a = ' '.join(
        str(getattr(item_a, field, '') or '').strip()
        for field in location_fields
    ).strip().lower()
    loc_b = ' '.join(
        str(getattr(item_b, field, '') or '').strip()
        for field in location_fields
    ).strip().lower()
    if not loc_a or not loc_b:
        return 0
    if loc_a == loc_b:
        return MAX_LOCATION
    # Partial: one string contains the other
    if loc_a in loc_b or loc_b in loc_a:
        return MAX_LOCATION // 2
    # Word-level overlap
    return _word_overlap_score(loc_a, loc_b, MAX_LOCATION)


def score_title(item_a, item_b):
    """Up to 20 pts based on word overlap between item titles."""
    return _word_overlap_score(item_a.title, item_b.title, MAX_TITLE)


def score_description(item_a, item_b):
    """Up to 15 pts based on word overlap between item descriptions."""
    return _word_overlap_score(item_a.description, item_b.description, MAX_DESCRIPTION)


def score_date(item_a, item_b):
    """
    Up to 10 pts based on how close the date_occurred values are.
        0 days  → 10 pts
        1 day   →  8 pts
        2 days  →  5 pts
        3 days  →  3 pts
        > 3 days→  0 pts
        Missing →  0 pts
    """
    d_a = item_a.date_occurred
    d_b = item_b.date_occurred
    if not d_a or not d_b:
        return 0
    diff = abs((d_a - d_b).days)
    if diff == 0:
        return 10
    if diff == 1:
        return 8
    if diff == 2:
        return 5
    if diff == 3:
        return 3
    return 0


# ── Main calculation ──────────────────────────────────────────────────────────

def calculate_score(lost_item, found_item):
    """
    Calculate the full match score for a (lost, found) pair.

    Returns a dict:
        {
            'total':        int,   # 0-100
            'category':     int,
            'location':     int,
            'title':        int,
            'description':  int,
            'date':         int,
        }
    """
    s_cat  = score_category(lost_item, found_item)
    s_loc  = score_location(lost_item, found_item)
    s_ttl  = score_title(lost_item, found_item)
    s_desc = score_description(lost_item, found_item)
    s_date = score_date(lost_item, found_item)
    s_image = 0
    if lost_item.image and found_item.image:
        similarity = image_similarity(lost_item.image, found_item.image)
        if similarity >= 65:
            s_image = round((similarity - 65) / 35 * 20)
        # Reserve 20% of the score for visual similarity when both reports
        # include a photo. Text-only reports keep the original score weights.
        s_cat = round(s_cat * .8)
        s_loc = round(s_loc * .8)
        s_ttl = round(s_ttl * .8)
        s_desc = round(s_desc * .8)
        s_date = round(s_date * .8)
    total = min(100, s_cat + s_loc + s_ttl + s_desc + s_date + s_image)

    return {
        'total':       total,
        'category':    s_cat,
        'location':    s_loc,
        'title':       s_ttl,
        'description': s_desc,
        'date':        s_date,
        'image':       s_image,
    }


# ── Match generation ──────────────────────────────────────────────────────────

def generate_matches_for_item(new_item):
    """
    Reconcile all matches involving an item against current active opposite-type
    reports. Stale pending suggestions are removed; decided matches are retained
    as history and their score is refreshed when both reports remain active.

    Returns a list of (ItemMatch, created) tuples for all qualifying pairs.
    """
    from items.models import Item  # local import to avoid circular imports

    existing_matches = ItemMatch.objects.filter(
        Q(lost_item=new_item) | Q(found_item=new_item)
    )
    existing_by_pair = {
        (match.lost_item_id, match.found_item_id): match
        for match in existing_matches
    }
    if not new_item.is_active():
        existing_matches.filter(status=ItemMatch.STATUS_PENDING).delete()
        return []

    if new_item.is_lost():
        candidates = Item.objects.filter(
            item_type=Item.TYPE_FOUND,
            status=Item.STATUS_ACTIVE,
        ).exclude(pk=new_item.pk)
        pairs = ((new_item, found_item) for found_item in candidates)
    else:
        candidates = Item.objects.filter(
            item_type=Item.TYPE_LOST,
            status=Item.STATUS_ACTIVE,
        ).exclude(pk=new_item.pk)
        pairs = ((lost_item, new_item) for lost_item in candidates)

    results = []
    qualifying_pairs = set()
    for lost_item, found_item in pairs:
        breakdown = calculate_score(lost_item, found_item)
        key = (lost_item.pk, found_item.pk)
        # A strong visual match is enough to create a suggestion on its own;
        # reporters still review and confirm every suggestion.
        if breakdown['total'] >= MATCH_THRESHOLD or breakdown.get('image', 0) >= 12:
            match, created = _save_match(lost_item, found_item, breakdown)
            results.append((match, created))
            qualifying_pairs.add(key)
        else:
            previous = existing_by_pair.get(key)
            if previous and previous.status == ItemMatch.STATUS_PENDING:
                previous.delete()
            elif previous:
                _update_match_score(previous, breakdown)

    # Pending suggestions pointing at archived reports are no longer actionable.
    for key, previous in existing_by_pair.items():
        if (
            key not in qualifying_pairs
            and previous.pk is not None
            and previous.status == ItemMatch.STATUS_PENDING
        ):
            previous.delete()
    return results


def _update_match_score(match, breakdown):
    match.score = breakdown['total']
    match.score_category = breakdown['category']
    match.score_location = breakdown['location']
    match.score_title = breakdown['title']
    match.score_description = breakdown['description']
    match.score_date = breakdown['date']
    match.score_image = breakdown.get('image', 0)
    match.save(update_fields=[
        'score', 'score_category', 'score_location', 'score_title',
        'score_description', 'score_date', 'score_image', 'updated_at',
    ])


def _save_match(lost_item, found_item, breakdown):
    """
    Create or update an ItemMatch for (lost_item, found_item).
    Returns (match, created).  Updates the score if the match already exists.
    """
    match, created = ItemMatch.objects.get_or_create(
        lost_item=lost_item,
        found_item=found_item,
        defaults={
            'score':             breakdown['total'],
            'score_category':    breakdown['category'],
            'score_location':    breakdown['location'],
            'score_title':       breakdown['title'],
            'score_description': breakdown['description'],
            'score_date':        breakdown['date'],
            'score_image':       breakdown.get('image', 0),
        },
    )
    if not created:
        _update_match_score(match, breakdown)
    return match, created
