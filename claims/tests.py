"""
Sprint 4 — Claims & Verification Tests
======================================
Tests cover all 21 required scenarios plus additional edge cases.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Profile
from items.models import Item, Category
from claims.models import Claim


class ClaimsBaseTestCase(TestCase):
    """Base test case that sets up common fixtures for all claim tests."""

    def setUp(self):
        self.client = Client()

        # Create a category
        self.category = Category.objects.create(name='Electronics', description='Electronic items')

        # Create users
        self.user_a = User.objects.create_user(
            username='user_a', email='a@test.com', password='testpass123',
            first_name='Alice', last_name='A'
        )
        self.user_b = User.objects.create_user(
            username='user_b', email='b@test.com', password='testpass123',
            first_name='Bob', last_name='B'
        )
        self.user_c = User.objects.create_user(
            username='user_c', email='c@test.com', password='testpass123',
            first_name='Carol', last_name='C'
        )

        # Create admin
        self.admin_user = User.objects.create_user(
            username='admin_test', email='admin@test.com', password='adminpass123'
        )
        admin_profile = self.admin_user.profile
        admin_profile.role = Profile.ROLE_ADMIN
        admin_profile.save()

        # Create an active item reported by user_a
        self.active_item = Item.objects.create(
            title='Blue Backpack',
            description='A blue backpack with white stripes',
            item_type=Item.TYPE_LOST,
            category=self.category,
            location='Library',
            date_occurred='2024-01-15',
            status=Item.STATUS_ACTIVE,
            reporter=self.user_a,
        )

        # Create an archived item
        self.archived_item = Item.objects.create(
            title='Old Laptop',
            description='Old grey laptop',
            item_type=Item.TYPE_LOST,
            category=self.category,
            location='Cafeteria',
            date_occurred='2024-01-10',
            status=Item.STATUS_ARCHIVED,
            reporter=self.user_a,
        )

    def login_as(self, user):
        self.client.force_login(user)

    def make_claim(self, user, item=None, status=Claim.STATUS_PENDING):
        """Helper to create a claim directly in the database."""
        if item is None:
            item = self.active_item
        return Claim.objects.create(
            item=item,
            claimant=user,
            message='I lost this item last Monday near the library entrance.',
            proof_description='It has a small red key ring attached and my initials on the strap.',
            status=status,
        )


# ─────────────────────────────────────────────────────────────
# 1. SUBMIT CLAIM TESTS
# ─────────────────────────────────────────────────────────────

class SubmitClaimTests(ClaimsBaseTestCase):

    def test_authenticated_user_can_submit_claim(self):
        """Test 1: Authenticated user can submit a claim."""
        self.login_as(self.user_b)
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday near the library entrance.',
            'proof_description': 'It has a small red key ring and my initials on the strap.',
        })
        self.assertRedirects(response, reverse('claims:claim_detail', args=[1]))
        self.assertEqual(Claim.objects.count(), 1)
        claim = Claim.objects.first()
        self.assertEqual(claim.claimant, self.user_b)
        self.assertEqual(claim.item, self.active_item)
        self.assertEqual(claim.status, Claim.STATUS_PENDING)

    def test_anonymous_user_cannot_submit_claim(self):
        """Test 2: Anonymous user cannot submit a claim."""
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday.',
            'proof_description': 'It has my initials on the strap.',
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(Claim.objects.count(), 0)

    def test_user_cannot_claim_own_item(self):
        """Test 3: User cannot claim their own item."""
        self.login_as(self.user_a)  # user_a is the reporter
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday.',
            'proof_description': 'It has my initials on the strap.',
        })
        # Should redirect back to item detail with error
        self.assertRedirects(response, reverse('items:item_detail', args=[self.active_item.pk]))
        self.assertEqual(Claim.objects.count(), 0)

    def test_user_cannot_claim_archived_item(self):
        """Test 4: User cannot claim an archived item."""
        self.login_as(self.user_b)
        url = reverse('claims:submit_claim', args=[self.archived_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday.',
            'proof_description': 'It has my initials on the strap.',
        })
        self.assertRedirects(response, reverse('items:item_detail', args=[self.archived_item.pk]))
        self.assertEqual(Claim.objects.count(), 0)

    def test_user_cannot_create_duplicate_pending_claims(self):
        """Test 5: User cannot create duplicate pending claims for the same item."""
        self.login_as(self.user_b)
        self.make_claim(self.user_b)  # Already has a pending claim

        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday.',
            'proof_description': 'It has my initials on the strap.',
        })
        # Should redirect to my_claims
        self.assertRedirects(response, reverse('claims:my_claims'))
        self.assertEqual(Claim.objects.count(), 1)  # Still only 1 claim

    def test_user_can_submit_after_previous_rejected_claim(self):
        """User can resubmit after a previous rejected claim."""
        self.make_claim(self.user_b, status=Claim.STATUS_REJECTED)
        self.login_as(self.user_b)
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday near the library entrance.',
            'proof_description': 'It has a small red key ring and my initials on the strap.',
        })
        self.assertEqual(Claim.objects.count(), 2)  # One rejected + one new

    def test_claim_status_is_always_pending_on_creation(self):
        """System always sets status to PENDING regardless of POST data."""
        self.login_as(self.user_b)
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'I lost this item last Monday near the library entrance.',
            'proof_description': 'It has a small red key ring and my initials on the strap.',
            'status': 'APPROVED',  # Trying to inject a status
            'reviewed_by': self.admin_user.pk,  # Trying to inject reviewer
        })
        claim = Claim.objects.first()
        if claim:
            self.assertEqual(claim.status, Claim.STATUS_PENDING)

    def test_short_message_is_rejected(self):
        """Form validation: message shorter than 20 chars is rejected."""
        self.login_as(self.user_b)
        url = reverse('claims:submit_claim', args=[self.active_item.pk])
        response = self.client.post(url, {
            'message': 'Short',
            'proof_description': 'It has a small red key ring and my initials on the strap.',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Claim.objects.count(), 0)


# ─────────────────────────────────────────────────────────────
# 2. VIEW CLAIM TESTS
# ─────────────────────────────────────────────────────────────

class ViewClaimTests(ClaimsBaseTestCase):

    def test_user_can_view_own_claims(self):
        """Test 6: User can view their own claims."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_b)
        url = reverse('claims:claim_detail', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, claim.message)

    def test_user_cannot_view_another_users_claim(self):
        """Test 7: User cannot view another user's private claim."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_c)  # Different user
        url = reverse('claims:claim_detail', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_item_reporter_can_view_claims_for_their_item(self):
        """Test 10: Item reporter can view claims for their item."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)  # user_a is the reporter
        url = reverse('claims:claim_detail', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_any_claim(self):
        """Test 12: Admin can view any claim."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.admin_user)
        url = reverse('claims:claim_detail', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_my_claims_view_shows_own_claims(self):
        """My Claims page shows only the logged-in user's claims."""
        claim_b = self.make_claim(self.user_b)
        claim_c = self.make_claim(self.user_c)
        self.login_as(self.user_b)
        url = reverse('claims:my_claims')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(claim_b, response.context['claims'])
        self.assertNotIn(claim_c, response.context['claims'])


# ─────────────────────────────────────────────────────────────
# 3. WITHDRAW CLAIM TESTS
# ─────────────────────────────────────────────────────────────

class WithdrawClaimTests(ClaimsBaseTestCase):

    def test_user_can_withdraw_pending_claim(self):
        """Test 8: User can withdraw a pending claim."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_b)
        url = reverse('claims:withdraw_claim', args=[claim.pk])
        response = self.client.post(url)
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_WITHDRAWN)

    def test_user_cannot_withdraw_approved_claim(self):
        """Test 9: User cannot withdraw an approved claim."""
        claim = self.make_claim(self.user_b, status=Claim.STATUS_APPROVED)
        self.login_as(self.user_b)
        url = reverse('claims:withdraw_claim', args=[claim.pk])
        response = self.client.post(url)
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_APPROVED)  # Unchanged

    def test_user_cannot_withdraw_another_users_claim(self):
        """User cannot withdraw claims they did not submit."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_c)
        url = reverse('claims:withdraw_claim', args=[claim.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_PENDING)  # Unchanged

    def test_withdrawn_claim_remains_in_database(self):
        """Test 18: Withdrawn claims remain in database."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_b)
        url = reverse('claims:withdraw_claim', args=[claim.pk])
        self.client.post(url)
        self.assertTrue(Claim.objects.filter(pk=claim.pk).exists())


# ─────────────────────────────────────────────────────────────
# 4. REVIEW / APPROVE / REJECT TESTS
# ─────────────────────────────────────────────────────────────

class ReviewClaimTests(ClaimsBaseTestCase):

    def test_item_reporter_can_access_review_page(self):
        """Test 10 (review access): Item reporter can view claims for their item."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unrelated_user_cannot_review_claim(self):
        """Test 11: Unrelated user cannot review the claim."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_c)  # Unrelated user
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_claimant_cannot_review_own_claim(self):
        """Claimant cannot review their own claim (they are not the item reporter)."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_b)
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_claim_can_be_approved(self):
        """Test 13: Claim can be approved."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)  # Reporter
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.post(url, {
            'action': 'approve',
            'reviewer_notes': 'Verified ownership.',
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_APPROVED)

    def test_claim_can_be_rejected(self):
        """Test 14: Claim can be rejected."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)  # Reporter
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.post(url, {
            'action': 'reject',
            'reviewer_notes': 'Proof insufficient.',
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_REJECTED)

    def test_approval_archives_item(self):
        """Test 15: Approval archives the related item."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)
        url = reverse('claims:review_claim', args=[claim.pk])
        self.client.post(url, {'action': 'approve', 'reviewer_notes': 'Verified.'})
        self.active_item.refresh_from_db()
        self.assertEqual(self.active_item.status, Item.STATUS_ARCHIVED)

    def test_approval_rejects_other_pending_claims(self):
        """Test 16: Approval rejects other pending claims for the same item."""
        claim_b = self.make_claim(self.user_b)
        claim_c = self.make_claim(self.user_c)
        self.login_as(self.user_a)
        url = reverse('claims:review_claim', args=[claim_b.pk])
        self.client.post(url, {'action': 'approve', 'reviewer_notes': 'Approved.'})
        claim_c.refresh_from_db()
        self.assertEqual(claim_c.status, Claim.STATUS_REJECTED)
        self.assertIn('already been resolved', claim_c.reviewer_notes)

    def test_admin_can_review_any_claim(self):
        """Test 12: Admin can review any claim."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.admin_user)
        url = reverse('claims:review_claim', args=[claim.pk])
        response = self.client.post(url, {
            'action': 'reject',
            'reviewer_notes': 'Admin rejected.',
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_REJECTED)

    def test_reviewer_information_is_saved_correctly(self):
        """Test 20: Reviewer information is saved correctly."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)
        url = reverse('claims:review_claim', args=[claim.pk])
        self.client.post(url, {'action': 'approve', 'reviewer_notes': 'Ownership confirmed.'})
        claim.refresh_from_db()
        self.assertEqual(claim.reviewed_by, self.user_a)
        self.assertIsNotNone(claim.reviewed_at)
        self.assertEqual(claim.reviewer_notes, 'Ownership confirmed.')

    def test_rejected_claims_remain_in_database(self):
        """Test 17: Rejected claims remain in database."""
        claim = self.make_claim(self.user_b)
        self.login_as(self.user_a)
        url = reverse('claims:review_claim', args=[claim.pk])
        self.client.post(url, {'action': 'reject', 'reviewer_notes': 'Denied.'})
        self.assertTrue(Claim.objects.filter(pk=claim.pk).exists())
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_REJECTED)


# ─────────────────────────────────────────────────────────────
# 5. CLAIM STATUS TESTS
# ─────────────────────────────────────────────────────────────

class ClaimStatusTests(ClaimsBaseTestCase):

    def test_claim_status_changes_correctly_on_approval(self):
        """Test 19: Claim status changes correctly on approval."""
        claim = self.make_claim(self.user_b)
        self.assertEqual(claim.status, Claim.STATUS_PENDING)
        claim.status = Claim.STATUS_APPROVED
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_APPROVED)

    def test_claim_status_changes_correctly_on_rejection(self):
        """Test 19b: Claim status changes correctly on rejection."""
        claim = self.make_claim(self.user_b)
        claim.status = Claim.STATUS_REJECTED
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_REJECTED)

    def test_claim_status_badge_classes(self):
        """Verify correct Bootstrap badge class returned per status."""
        claim = self.make_claim(self.user_b)

        claim.status = Claim.STATUS_PENDING
        self.assertEqual(claim.get_status_badge_class(), 'warning')

        claim.status = Claim.STATUS_APPROVED
        self.assertEqual(claim.get_status_badge_class(), 'success')

        claim.status = Claim.STATUS_REJECTED
        self.assertEqual(claim.get_status_badge_class(), 'danger')

        claim.status = Claim.STATUS_WITHDRAWN
        self.assertEqual(claim.get_status_badge_class(), 'secondary')


# ─────────────────────────────────────────────────────────────
# 6. ITEM CLAIMS VIEW (REPORTER / ADMIN)
# ─────────────────────────────────────────────────────────────

class ItemClaimsViewTests(ClaimsBaseTestCase):

    def test_item_reporter_can_view_item_claims_page(self):
        """Reporter can access the item claims page for their own item."""
        self.make_claim(self.user_b)
        self.login_as(self.user_a)
        url = reverse('claims:item_claims', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unrelated_user_cannot_view_item_claims_page(self):
        """Unrelated user cannot access item claims page."""
        self.make_claim(self.user_b)
        self.login_as(self.user_c)
        url = reverse('claims:item_claims', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_item_claims_page(self):
        """Admin can access the item claims page for any item."""
        self.make_claim(self.user_b)
        self.login_as(self.admin_user)
        url = reverse('claims:item_claims', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────────────────────
# 7. ADMIN CLAIM LIST VIEW TESTS
# ─────────────────────────────────────────────────────────────

class AdminClaimListTests(ClaimsBaseTestCase):

    def test_admin_can_access_claim_list(self):
        """Admin can access the manage claims page."""
        self.login_as(self.admin_user)
        url = reverse('claims:claim_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_access_claim_list(self):
        """Regular user cannot access the admin claim list."""
        self.login_as(self.user_b)
        url = reverse('claims:claim_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_claim_list_shows_all_claims(self):
        """Admin claim list shows all claims from all users."""
        claim_b = self.make_claim(self.user_b)
        claim_c = self.make_claim(self.user_c)
        self.login_as(self.admin_user)
        url = reverse('claims:claim_list')
        response = self.client.get(url)
        self.assertIn(claim_b, response.context['claims'])
        self.assertIn(claim_c, response.context['claims'])


# ─────────────────────────────────────────────────────────────
# 8. DASHBOARD CLAIM COUNTS TESTS
# ─────────────────────────────────────────────────────────────

class DashboardClaimCountTests(ClaimsBaseTestCase):

    def test_user_dashboard_claim_counts_are_correct(self):
        """Test 21: User dashboard claim counts are correct."""
        self.make_claim(self.user_b, status=Claim.STATUS_PENDING)
        self.make_claim(self.user_b, status=Claim.STATUS_APPROVED)

        # Need a second active item for a second claim by same user
        item2 = Item.objects.create(
            title='Laptop', description='Silver laptop', item_type=Item.TYPE_FOUND,
            category=self.category, location='Gym', date_occurred='2024-01-20',
            status=Item.STATUS_ACTIVE, reporter=self.user_a,
        )
        Claim.objects.create(
            item=item2, claimant=self.user_b,
            message='This is my laptop, I can identify it by serial.',
            proof_description='Serial number is XYZ-12345 and has a scratch on the lid.',
            status=Claim.STATUS_REJECTED,
        )

        self.login_as(self.user_b)
        url = reverse('accounts:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['my_claims_pending'], 1)
        self.assertEqual(response.context['my_claims_approved'], 1)
        self.assertEqual(response.context['my_claims_rejected'], 1)
        self.assertEqual(response.context['my_claims_total'], 3)

    def test_admin_dashboard_claim_counts_are_correct(self):
        """Test 21b: Admin dashboard shows correct total claim counts."""
        self.make_claim(self.user_b, status=Claim.STATUS_PENDING)
        self.make_claim(self.user_c, status=Claim.STATUS_APPROVED)

        self.login_as(self.admin_user)
        url = reverse('accounts:admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_claims'], 2)
        self.assertEqual(response.context['total_claims_pending'], 1)
        self.assertEqual(response.context['total_claims_approved'], 1)


# ─────────────────────────────────────────────────────────────
# 9. ITEM DETAIL CLAIM INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────

class ItemDetailClaimIntegrationTests(ClaimsBaseTestCase):

    def test_item_detail_shows_claim_button_for_non_reporter(self):
        """Non-reporter sees 'Claim This Item' button on active item."""
        self.login_as(self.user_b)
        url = reverse('items:item_detail', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_claim'])
        self.assertFalse(response.context['has_pending_claim'])

    def test_item_detail_hides_claim_button_for_reporter(self):
        """Reporter does not see claim button for their own item."""
        self.login_as(self.user_a)
        url = reverse('items:item_detail', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertFalse(response.context['can_claim'])

    def test_item_detail_shows_pending_notice_when_claim_exists(self):
        """'Pending Review' notice shown instead of claim button when pending."""
        self.make_claim(self.user_b)
        self.login_as(self.user_b)
        url = reverse('items:item_detail', args=[self.active_item.pk])
        response = self.client.get(url)
        self.assertTrue(response.context['has_pending_claim'])
        self.assertFalse(response.context['can_claim'])

    def test_item_detail_no_claim_for_archived_item(self):
        """Can_claim is False for archived items."""
        self.login_as(self.user_b)
        url = reverse('items:item_detail', args=[self.archived_item.pk])
        response = self.client.get(url)
        self.assertFalse(response.context['can_claim'])
