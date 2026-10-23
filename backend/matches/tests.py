from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Profile
from items.models import Item, Category
from matches.models import ItemMatch
from matches import engine as match_engine
from notifications.models import Notification


class MatchingEngineUnitTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        self.user2 = User.objects.create_user('bob', 'bob@test.com', 'pass123')
        self.cat_electronics = Category.objects.create(name='Electronics')
        self.cat_clothing = Category.objects.create(name='Clothing')

        self.lost_phone = Item.objects.create(
            title='Black Samsung Phone',
            description='Galaxy S21 with cracked screen protector',
            item_type=Item.TYPE_LOST,
            category=self.cat_electronics,
            location='Library 2nd Floor',
            date_occurred=date(2026, 9, 20),
            reporter=self.user1,
        )

        self.found_phone = Item.objects.create(
            title='Samsung Phone Black',
            description='Samsung Galaxy phone found near books',
            item_type=Item.TYPE_FOUND,
            category=self.cat_electronics,
            location='Library 2nd Floor',
            date_occurred=date(2026, 9, 21),
            reporter=self.user2,
        )

    def test_category_matching_points(self):
        pts = match_engine.score_category(self.lost_phone, self.found_phone)
        self.assertEqual(pts, 30)

        # Mismatched category
        diff_item = Item.objects.create(
            title='Black Jacket',
            description='Winter jacket',
            item_type=Item.TYPE_FOUND,
            category=self.cat_clothing,
            location='Library',
            date_occurred=date(2026, 9, 20),
            reporter=self.user2,
        )
        self.assertEqual(match_engine.score_category(self.lost_phone, diff_item), 0)

    def test_location_matching_points(self):
        pts = match_engine.score_location(self.lost_phone, self.found_phone)
        self.assertEqual(pts, 25)

    def test_filipino_and_english_item_terms_and_colors_normalize(self):
        self.assertEqual(match_engine._tokenize('selpon cellphone smartphone'), {'phone'})
        self.assertEqual(match_engine._tokenize('payong pula'), {'umbrella', 'red'})
        self.assertEqual(match_engine._tokenize('itim bag'), {'black', 'bag'})

    def test_title_score_tolerates_a_small_typo(self):
        self.lost_phone.title = 'Black Samsng Phone'
        self.found_phone.title = 'Black Samsung Phone'
        self.assertGreaterEqual(match_engine.score_title(self.lost_phone, self.found_phone), 17)

    def test_structured_room_details_change_location_similarity(self):
        self.lost_phone.location = 'Computer Lab'
        self.lost_phone.room = 'ComLab 1'
        self.found_phone.location = 'Computer Lab'
        self.found_phone.room = 'ComLab 2'
        self.lost_phone.save()
        self.found_phone.save()
        self.assertLess(match_engine.score_location(self.lost_phone, self.found_phone), 25)

        self.found_phone.room = 'ComLab 1'
        self.found_phone.save()
        self.assertEqual(match_engine.score_location(self.lost_phone, self.found_phone), 25)

    def test_title_similarity_points(self):
        pts = match_engine.score_title(self.lost_phone, self.found_phone)
        # Both contain 'black', 'samsung', 'phone' -> high overlap
        self.assertGreaterEqual(pts, 15)

    def test_date_matching_points(self):
        # 1 day difference -> 8 points
        pts = match_engine.score_date(self.lost_phone, self.found_phone)
        self.assertEqual(pts, 8)

    def test_full_score_calculation(self):
        score_data = match_engine.calculate_score(self.lost_phone, self.found_phone)
        self.assertGreaterEqual(score_data['total'], match_engine.MATCH_THRESHOLD)
        self.assertEqual(score_data['category'], 30)
        self.assertEqual(score_data['location'], 25)
        self.assertEqual(score_data['date'], 8)

    def test_live_suggestions_search_the_opposite_report_type(self):
        self.client.force_login(self.user1)
        common = {
            'title': 'Samsung Phone Black',
            'description': 'Samsung Galaxy phone found near books',
            'category': str(self.cat_electronics.pk),
            'location': 'Library 2nd Floor',
            'date_occurred': '2026-09-21',
        }

        lost_response = self.client.post(reverse('match_suggestions'), {**common, 'item_type': Item.TYPE_LOST})
        self.assertEqual(lost_response.status_code, 200)
        self.assertIn(self.found_phone.pk, [item['id'] for item in lost_response.json()['results']])

        found_response = self.client.post(reverse('match_suggestions'), {**common, 'item_type': Item.TYPE_FOUND})
        self.assertEqual(found_response.status_code, 200)
        self.assertIn(self.lost_phone.pk, [item['id'] for item in found_response.json()['results']])

    def test_lost_does_not_match_lost(self):
        # Matching engine only queries opposite type
        results = match_engine.generate_matches_for_item(self.lost_phone)
        for match, _ in results:
            self.assertEqual(match.lost_item.item_type, Item.TYPE_LOST)
            self.assertEqual(match.found_item.item_type, Item.TYPE_FOUND)

    def test_item_below_threshold_is_not_stored(self):
        # Completely unrelated item
        unrelated_found = Item.objects.create(
            title='Red Umbrella',
            description='Rain gear left behind',
            item_type=Item.TYPE_FOUND,
            category=self.cat_clothing,
            location='Gymnasium',
            date_occurred=date(2026, 8, 1),
            reporter=self.user2,
        )
        score = match_engine.calculate_score(self.lost_phone, unrelated_found)
        self.assertLess(score['total'], match_engine.MATCH_THRESHOLD)

    def test_reconcile_removes_pending_match_after_item_archive(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost_phone,
            found_item=self.found_phone,
            score=90,
        )
        self.found_phone.status = Item.STATUS_ARCHIVED
        self.found_phone.save(update_fields=['status', 'updated_at'])

        match_engine.generate_matches_for_item(self.found_phone)

        self.assertFalse(ItemMatch.objects.filter(pk=match.pk).exists())

    def test_reconcile_removes_pending_match_when_edit_drops_below_threshold(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost_phone,
            found_item=self.found_phone,
            score=90,
        )
        self.found_phone.title = 'Red umbrella'
        self.found_phone.description = 'Rain gear left in the gym.'
        self.found_phone.category = self.cat_clothing
        self.found_phone.location = 'Gymnasium'
        self.found_phone.date_occurred = date(2026, 8, 1)
        self.found_phone.save()

        match_engine.generate_matches_for_item(self.found_phone)

        self.assertLess(
            match_engine.calculate_score(self.lost_phone, self.found_phone)['total'],
            match_engine.MATCH_THRESHOLD,
        )
        self.assertFalse(ItemMatch.objects.filter(pk=match.pk).exists())

    def test_reconcile_preserves_decided_match_and_refreshes_score(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost_phone,
            found_item=self.found_phone,
            score=99,
            status=ItemMatch.STATUS_CONFIRMED,
        )
        self.found_phone.location = 'Computer Lab 3'
        self.found_phone.save(update_fields=['location', 'updated_at'])

        match_engine.generate_matches_for_item(self.found_phone)

        match.refresh_from_db()
        breakdown = match_engine.calculate_score(self.lost_phone, self.found_phone)
        self.assertEqual(match.status, ItemMatch.STATUS_CONFIRMED)
        self.assertEqual(match.score, breakdown['total'])


class MatchWorkflowTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user('usera', 'usera@test.com', 'pass123')
        self.user_b = User.objects.create_user('userb', 'userb@test.com', 'pass123')
        self.user_c = User.objects.create_user('userc', 'userc@test.com', 'pass123')
        self.cat = Category.objects.create(name='Electronics')

        self.lost = Item.objects.create(
            title='Black Samsung Phone',
            description='Lost in library',
            item_type=Item.TYPE_LOST,
            category=self.cat,
            location='Library',
            date_occurred=date(2026, 9, 20),
            reporter=self.user_a,
        )
        self.found = Item.objects.create(
            title='Black Samsung Phone',
            description='Found in library',
            item_type=Item.TYPE_FOUND,
            category=self.cat,
            location='Library',
            date_occurred=date(2026, 9, 20),
            reporter=self.user_b,
        )

    def test_match_generation_and_notification(self):
        # Trigger matching
        from items.views import _run_matching_for_item
        _run_matching_for_item(self.found)

        match = ItemMatch.objects.filter(lost_item=self.lost, found_item=self.found).first()
        self.assertIsNotNone(match)
        self.assertGreaterEqual(match.score, match_engine.MATCH_THRESHOLD)

        # Both user A and user B should have received match notifications
        notif_a = Notification.objects.filter(recipient=self.user_a, notification_type=Notification.TYPE_POSSIBLE_MATCH).first()
        notif_b = Notification.objects.filter(recipient=self.user_b, notification_type=Notification.TYPE_POSSIBLE_MATCH).first()
        self.assertIsNotNone(notif_a)
        self.assertIsNotNone(notif_b)

    def test_duplicate_match_not_created(self):
        from items.views import _run_matching_for_item
        _run_matching_for_item(self.found)
        _run_matching_for_item(self.found)
        self.assertEqual(ItemMatch.objects.filter(lost_item=self.lost, found_item=self.found).count(), 1)

    def test_user_can_view_own_match(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost,
            found_item=self.found,
            score=85,
        )
        self.client.login(username='usera', password='pass123')
        response = self.client.get(reverse('matches:detail', args=[match.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Black Samsung Phone')

    def test_unrelated_user_cannot_view_match(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost,
            found_item=self.found,
            score=85,
        )
        self.client.login(username='userc', password='pass123')
        response = self.client.get(reverse('matches:detail', args=[match.pk]))
        self.assertEqual(response.status_code, 404)

    def test_confirm_match(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost,
            found_item=self.found,
            score=85,
        )
        self.client.login(username='usera', password='pass123')
        response = self.client.post(reverse('matches:confirm', args=[match.pk]))
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, ItemMatch.STATUS_CONFIRMED)

        # User B should have received a confirmation notification
        b_notif = Notification.objects.filter(recipient=self.user_b, notification_type=Notification.TYPE_MATCH_CONFIRMED).first()
        self.assertIsNotNone(b_notif)

    def test_dismiss_match(self):
        match = ItemMatch.objects.create(
            lost_item=self.lost,
            found_item=self.found,
            score=85,
        )
        self.client.login(username='usera', password='pass123')
        response = self.client.post(reverse('matches:dismiss', args=[match.pk]))
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, ItemMatch.STATUS_DISMISSED)
        # Should not be deleted
        self.assertTrue(ItemMatch.objects.filter(pk=match.pk).exists())
