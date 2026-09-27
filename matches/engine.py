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
from datetime import date

from django.conf import settings

from .models import ItemMatch

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


# ── Text utilities ────────────────────────────────────────────────────────────

def _tokenize(text):
    """Lowercase, remove punctuation, split into non-stopword words."""
    if not text:
        return set()
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = {w for w in text.split() if w and w not in STOPWORDS and len(w) > 1}
    return words


def _jaccard(set_a, set_b):
    """Jaccard similarity coefficient in [0, 1]."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


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
    25 pts for case-insensitive location match.
    Partial credit (13 pts) if one location is wholly contained in the other.
    """
    if not item_a.location or not item_b.location:
        return 0
    loc_a = item_a.location.strip().lower()
    loc_b = item_b.location.strip().lower()
    if loc_a == loc_b:
        return MAX_LOCATION
    # Partial: one string contains the other
    if loc_a in loc_b or loc_b in loc_a:
        return MAX_LOCATION // 2
    # Word-level overlap
    return _word_overlap_score(item_a.location, item_b.location, MAX_LOCATION)


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
    total  = s_cat + s_loc + s_ttl + s_desc + s_date

    return {
        'total':       total,
        'category':    s_cat,
        'location':    s_loc,
        'title':       s_ttl,
        'description': s_desc,
        'date':        s_date,
    }


# ── Match generation ──────────────────────────────────────────────────────────

def generate_matches_for_item(new_item):
    """
    Given a newly created (or re-activated) ACTIVE item, find all ACTIVE items
    of the *opposite* type, calculate scores, and create ItemMatch records for
    pairs that meet MATCH_THRESHOLD.

    Returns a list of (ItemMatch, created) tuples for all qualifying pairs.
    """
    from items.models import Item  # local import to avoid circular imports

    if not new_item.is_active():
        return []

    if new_item.is_lost():
        candidates = Item.objects.filter(
            item_type=Item.TYPE_FOUND,
            status=Item.STATUS_ACTIVE,
        ).exclude(pk=new_item.pk)
        lost_item  = new_item

        results = []
        for found_item in candidates:
            breakdown = calculate_score(lost_item, found_item)
            if breakdown['total'] >= MATCH_THRESHOLD:
                match, created = _save_match(lost_item, found_item, breakdown)
                results.append((match, created))
        return results

    else:  # FOUND
        candidates = Item.objects.filter(
            item_type=Item.TYPE_LOST,
            status=Item.STATUS_ACTIVE,
        ).exclude(pk=new_item.pk)
        found_item = new_item

        results = []
        for lost_item in candidates:
            breakdown = calculate_score(lost_item, found_item)
            if breakdown['total'] >= MATCH_THRESHOLD:
                match, created = _save_match(lost_item, found_item, breakdown)
                results.append((match, created))
        return results


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
        },
    )
    if not created:
        # Update score if the item was edited
        match.score             = breakdown['total']
        match.score_category    = breakdown['category']
        match.score_location    = breakdown['location']
        match.score_title       = breakdown['title']
        match.score_description = breakdown['description']
        match.score_date        = breakdown['date']
        match.save()
    return match, created
