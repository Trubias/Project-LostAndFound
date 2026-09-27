"""
Sprint 5 — Admin Management & Admin Dashboard Tests
====================================================
Tests cover all 27 required scenarios and security checks:
1. Admin can access admin dashboard.
2. Normal user cannot access admin dashboard (403).
3. Anonymous user cannot access admin dashboard (redirect).
4. Admin can view users.
5. Admin can search users.
6. Admin can filter users.
7. Admin can view user details.
8. Admin can activate/deactivate users (and cannot deactivate self).
9. Admin can change application role (and cannot demote self).
10. User cannot change their own role or access admin URLs.
11. Admin can view all items.
12. Admin can search items.
13. Admin can filter items.
14. Admin can archive items.
15. Admin can restore items.
16. Admin can view all claims.
17. Admin can filter claims.
18. Admin can review claims.
19. Admin can approve claims.
20. Admin can reject claims.
21. Admin can create category.
22. Admin can edit category.
23. Admin can safely delete category (and deletion is blocked if items exist).
24. Dashboard user count is correct.
25. Dashboard item counts are correct.
26. Dashboard claim counts are correct.
27. Dashboard category count is correct.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date

from accounts.models import Profile
from items.models import Category, Item
from claims.models import Claim


class AdminAccessAndPermissionsTests(TestCase):
    """Tests 1-3 & 10: Access control and permission protection for the Admin area."""

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_user(
            username='admin_boss', email='admin@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        # Regular user
        self.regular_user = User.objects.create_user(
            username='normal_joe', email='joe@test.com', password='password123'
        )
        self.regular_user.profile.role = Profile.ROLE_USER
        self.regular_user.profile.save()

    def test_01_admin_can_access_admin_dashboard(self):
        """Test 1: Admin user can access the admin dashboard."""
        self.client.login(username='admin_boss', password='password123')
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator Dashboard')

    def test_02_normal_user_cannot_access_admin_dashboard(self):
        """Test 2: Normal user receives 403 Forbidden when accessing admin dashboard."""
        self.client.login(username='normal_joe', password='password123')
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_03_anonymous_user_cannot_access_admin_dashboard(self):
        """Test 3: Anonymous user is redirected to login when accessing admin dashboard."""
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_10_user_cannot_access_admin_subroutes_or_escalate_role(self):
        """Test 10: Normal user cannot access any admin management subroutes."""
        self.client.login(username='normal_joe', password='password123')

        protected_urls = [
            reverse('accounts:admin_users'),
            reverse('accounts:admin_items'),
            reverse('accounts:admin_claims'),
            reverse('accounts:admin_categories'),
            reverse('accounts:admin_category_create'),
            reverse('accounts:admin_user_detail', args=[self.regular_user.pk]),
            reverse('accounts:admin_user_toggle_status', args=[self.regular_user.pk]),
            reverse('accounts:admin_user_change_role', args=[self.regular_user.pk]),
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f"Expected 403 on {url} for normal user")

        # Ensure user profile role remains USER
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.profile.role, Profile.ROLE_USER)


class AdminUserManagementTests(TestCase):
    """Tests 4-9: User management (list, search, filter, details, activation, role change)."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_user', email='admin@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.user1 = User.objects.create_user(
            username='alice_wonder', first_name='Alice', last_name='Liddell',
            email='alice@example.com', password='password123'
        )
        self.user1.profile.role = Profile.ROLE_USER
        self.user1.profile.save()

        self.user2 = User.objects.create_user(
            username='bob_builder', first_name='Bob', last_name='Smith',
            email='bob@example.com', password='password123', is_active=False
        )
        self.user2.profile.role = Profile.ROLE_USER
        self.user2.profile.save()

        self.client.login(username='admin_user', password='password123')

    def test_04_admin_can_view_users(self):
        """Test 4: Admin can view user management page."""
        response = self.client.get(reverse('accounts:admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice_wonder')
        self.assertContains(response, 'bob_builder')

    def test_05_admin_can_search_users(self):
        """Test 5: Admin can search users by username, name, or email."""
        response = self.client.get(reverse('accounts:admin_users'), {'q': 'alice'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice_wonder')
        self.assertNotContains(response, 'bob_builder')

    def test_06_admin_can_filter_users(self):
        """Test 6: Admin can filter users by role and account status."""
        # Filter role=ADMIN
        resp_admin = self.client.get(reverse('accounts:admin_users'), {'role': 'ADMIN'})
        self.assertContains(resp_admin, 'admin_user')
        self.assertNotContains(resp_admin, 'alice_wonder')

        # Filter status=inactive
        resp_inactive = self.client.get(reverse('accounts:admin_users'), {'status': 'inactive'})
        self.assertContains(resp_inactive, 'bob_builder')
        self.assertNotContains(resp_inactive, 'alice_wonder')

    def test_07_admin_can_view_user_details(self):
        """Test 7: Admin can inspect a user's details and activity."""
        response = self.client.get(reverse('accounts:admin_user_detail', args=[self.user1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice_wonder')
        self.assertContains(response, 'Alice Liddell')
        self.assertContains(response, 'alice@example.com')

    def test_08_admin_can_activate_deactivate_users(self):
        """Test 8: Admin can toggle activation status of a user (and cannot deactivate self)."""
        # Deactivate Alice
        self.assertTrue(self.user1.is_active)
        post_url = reverse('accounts:admin_user_toggle_status', args=[self.user1.pk])
        resp = self.client.post(post_url)
        self.assertEqual(resp.status_code, 302)
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_active)

        # Reactivate Alice
        resp2 = self.client.post(post_url)
        self.assertEqual(resp2.status_code, 302)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.is_active)

        # Self-deactivation prevention
        self_post_url = reverse('accounts:admin_user_toggle_status', args=[self.admin.pk])
        self.client.post(self_post_url)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_09_admin_can_change_application_role(self):
        """Test 9: Admin can change a user's application role between USER and ADMIN."""
        role_url = reverse('accounts:admin_user_change_role', args=[self.user1.pk])
        resp = self.client.post(role_url, {'role': 'ADMIN'})
        self.assertEqual(resp.status_code, 302)
        self.user1.profile.refresh_from_db()
        self.assertEqual(self.user1.profile.role, Profile.ROLE_ADMIN)

        # Self-demotion prevention
        self_role_url = reverse('accounts:admin_user_change_role', args=[self.admin.pk])
        self.client.post(self_role_url, {'role': 'USER'})
        self.admin.profile.refresh_from_db()
        self.assertEqual(self.admin.profile.role, Profile.ROLE_ADMIN)


class AdminItemManagementTests(TestCase):
    """Tests 11-15: Item management (view all, search, filter, archive, restore)."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_item_mgr', email='admin_items@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.reporter = User.objects.create_user(
            username='item_reporter', email='rep@test.com', password='password123'
        )
        self.cat1 = Category.objects.create(name='Electronics', description='Gadgets')
        self.cat2 = Category.objects.create(name='Jewelry', description='Rings and necklaces')

        self.item_lost = Item.objects.create(
            title='MacBook Pro 16 Inch',
            description='Silver laptop with sticker',
            item_type=Item.TYPE_LOST,
            category=self.cat1,
            location='Library Room 301',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.reporter
        )

        self.item_found = Item.objects.create(
            title='Gold Wedding Ring',
            description='Found near cafeteria benches',
            item_type=Item.TYPE_FOUND,
            category=self.cat2,
            location='Cafeteria Entrance',
            date_occurred=date.today(),
            status=Item.STATUS_ARCHIVED,
            reporter=self.reporter
        )

        self.client.login(username='admin_item_mgr', password='password123')

    def test_11_admin_can_view_all_items(self):
        """Test 11: Admin can view all items on the admin items page."""
        response = self.client.get(reverse('accounts:admin_items'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MacBook Pro 16 Inch')
        self.assertContains(response, 'Gold Wedding Ring')

    def test_12_admin_can_search_items(self):
        """Test 12: Admin can search items by title, description, location, or reporter."""
        resp = self.client.get(reverse('accounts:admin_items'), {'q': 'MacBook'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'MacBook Pro 16 Inch')
        self.assertNotContains(resp, 'Gold Wedding Ring')

    def test_13_admin_can_filter_items(self):
        """Test 13: Admin can filter items by type, status, and category."""
        # Filter type=LOST
        resp_type = self.client.get(reverse('accounts:admin_items'), {'type': 'LOST'})
        self.assertContains(resp_type, 'MacBook Pro 16 Inch')
        self.assertNotContains(resp_type, 'Gold Wedding Ring')

        # Filter status=ARCHIVED
        resp_stat = self.client.get(reverse('accounts:admin_items'), {'status': 'ARCHIVED'})
        self.assertContains(resp_stat, 'Gold Wedding Ring')
        self.assertNotContains(resp_stat, 'MacBook Pro 16 Inch')

        # Filter category=cat1
        resp_cat = self.client.get(reverse('accounts:admin_items'), {'category': str(self.cat1.id)})
        self.assertContains(resp_cat, 'MacBook Pro 16 Inch')
        self.assertNotContains(resp_cat, 'Gold Wedding Ring')

    def test_14_admin_can_archive_item(self):
        """Test 14: Admin can archive an item."""
        archive_url = reverse('items:archive_item', args=[self.item_lost.pk])
        resp = self.client.post(archive_url)
        self.assertEqual(resp.status_code, 302)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.status, Item.STATUS_ARCHIVED)

    def test_15_admin_can_restore_item(self):
        """Test 15: Admin can restore an archived item."""
        restore_url = reverse('items:restore_item', args=[self.item_found.pk])
        resp = self.client.post(restore_url)
        self.assertEqual(resp.status_code, 302)
        self.item_found.refresh_from_db()
        self.assertEqual(self.item_found.status, Item.STATUS_ACTIVE)


class AdminClaimManagementTests(TestCase):
    """Tests 16-20: Claim management (view all, filter, review, approve, reject)."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_claims_mgr', email='admin_cl@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.reporter = User.objects.create_user(
            username='reporter_bob', email='rep_bob@test.com', password='password123'
        )
        self.claimant1 = User.objects.create_user(
            username='claimant_cathy', email='cathy@test.com', password='password123'
        )
        self.claimant2 = User.objects.create_user(
            username='claimant_dave', email='dave@test.com', password='password123'
        )

        self.item = Item.objects.create(
            title='Wireless Bluetooth Headphones',
            description='Sony WH-1000XM4 in black case',
            item_type=Item.TYPE_FOUND,
            location='Library Silent Floor',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.reporter
        )

        self.claim1 = Claim.objects.create(
            item=self.item,
            claimant=self.claimant1,
            message='I lost these exact headphones yesterday afternoon.',
            proof_description='The case has a small scratch and a USB-C cable inside.',
            status=Claim.STATUS_PENDING
        )

        self.claim2 = Claim.objects.create(
            item=self.item,
            claimant=self.claimant2,
            message='I also believe these headphones belong to me.',
            proof_description='Black Sony headphones with original box receipt.',
            status=Claim.STATUS_PENDING
        )

        self.client.login(username='admin_claims_mgr', password='password123')

    def test_16_admin_can_view_all_claims(self):
        """Test 16: Admin can view all claims on admin claims page."""
        response = self.client.get(reverse('accounts:admin_claims'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'claimant_cathy')
        self.assertContains(response, 'claimant_dave')

    def test_17_admin_can_filter_claims(self):
        """Test 17: Admin can filter claims by status and search terms."""
        resp = self.client.get(reverse('accounts:admin_claims'), {'status': 'PENDING'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'claimant_cathy')

        resp_search = self.client.get(reverse('accounts:admin_claims'), {'q': 'cathy'})
        self.assertContains(resp_search, 'claimant_cathy')
        self.assertNotContains(resp_search, 'claimant_dave')

    def test_18_admin_can_access_review_claim(self):
        """Test 18: Admin can access the review page for any pending claim."""
        review_url = reverse('claims:review_claim', args=[self.claim1.pk])
        response = self.client.get(review_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review Claim')

    def test_19_admin_can_approve_claim(self):
        """Test 19: Admin can approve a claim, archiving item and rejecting other pending claims."""
        review_url = reverse('claims:review_claim', args=[self.claim1.pk])
        resp = self.client.post(review_url, {
            'action': 'approve',
            'reviewer_notes': 'Verified serial number matches owner documents.',
        })
        self.assertEqual(resp.status_code, 302)

        self.claim1.refresh_from_db()
        self.assertEqual(self.claim1.status, Claim.STATUS_APPROVED)
        self.assertEqual(self.claim1.reviewed_by, self.admin)

        # Related item archived
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_ARCHIVED)

        # Other pending claims for the same item are automatically rejected
        self.claim2.refresh_from_db()
        self.assertEqual(self.claim2.status, Claim.STATUS_REJECTED)

    def test_20_admin_can_reject_claim(self):
        """Test 20: Admin can reject a claim with reviewer notes."""
        review_url = reverse('claims:review_claim', args=[self.claim2.pk])
        resp = self.client.post(review_url, {
            'action': 'reject',
            'reviewer_notes': 'Proof provided does not match description.',
        })
        self.assertEqual(resp.status_code, 302)

        self.claim2.refresh_from_db()
        self.assertEqual(self.claim2.status, Claim.STATUS_REJECTED)
        self.assertEqual(self.claim2.reviewed_by, self.admin)


class AdminCategoryManagementTests(TestCase):
    """Tests 21-23: Category management (create, edit, safe delete)."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin_cat_mgr', email='admin_cat@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        self.cat_empty = Category.objects.create(name='Documents', description='Passports, IDs, papers')
        self.cat_with_items = Category.objects.create(name='Bags', description='Backpacks, purses')

        # Item attached to cat_with_items
        self.item = Item.objects.create(
            title='Leather Handbag',
            description='Brown leather shoulder bag',
            item_type=Item.TYPE_LOST,
            category=self.cat_with_items,
            location='Bus Station',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.admin
        )

        self.client.login(username='admin_cat_mgr', password='password123')

    def test_21_admin_can_create_category(self):
        """Test 21: Admin can create a new category via admin dashboard."""
        create_url = reverse('accounts:admin_category_create')
        resp = self.client.post(create_url, {
            'name': 'Umbrellas & Raincoats',
            'description': 'Weather accessories left behind',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Category.objects.filter(name='Umbrellas & Raincoats').exists())

    def test_22_admin_can_edit_category(self):
        """Test 22: Admin can edit an existing category."""
        edit_url = reverse('accounts:admin_category_edit', args=[self.cat_empty.pk])
        resp = self.client.post(edit_url, {
            'name': 'Legal Documents & IDs',
            'description': 'Official identity documents and certificates',
        })
        self.assertEqual(resp.status_code, 302)
        self.cat_empty.refresh_from_db()
        self.assertEqual(self.cat_empty.name, 'Legal Documents & IDs')

    def test_23_admin_safe_delete_category(self):
        """Test 23: Deletion of category with items is prevented; empty category can be deleted."""
        # Attempt to delete category that contains items -> should be prevented
        del_with_items_url = reverse('accounts:admin_category_delete', args=[self.cat_with_items.pk])
        resp = self.client.post(del_with_items_url)
        self.assertEqual(resp.status_code, 302)
        # Category must still exist
        self.assertTrue(Category.objects.filter(pk=self.cat_with_items.pk).exists())

        # Delete empty category -> should succeed
        del_empty_url = reverse('accounts:admin_category_delete', args=[self.cat_empty.pk])
        resp_empty = self.client.post(del_empty_url)
        self.assertEqual(resp_empty.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.cat_empty.pk).exists())


class AdminDashboardStatisticsTests(TestCase):
    """Tests 24-27: Dashboard user, item, claim, and category real counts."""

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='stat_admin', email='stat_admin@test.com', password='password123'
        )
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()

        # Regular active user
        self.user_active = User.objects.create_user(
            username='user_active', email='act@test.com', password='password123', is_active=True
        )

        # Inactive user
        self.user_inactive = User.objects.create_user(
            username='user_inactive', email='inact@test.com', password='password123', is_active=False
        )

        # Categories
        self.cat1 = Category.objects.create(name='Electronics')
        self.cat2 = Category.objects.create(name='Accessories')

        # Items
        self.item_lost = Item.objects.create(
            title='Lost Watch', description='Gold watch', item_type=Item.TYPE_LOST,
            category=self.cat1, location='Campus', date_occurred=date.today(),
            status=Item.STATUS_ACTIVE, reporter=self.user_active
        )
        self.item_found = Item.objects.create(
            title='Found Keys', description='Key ring', item_type=Item.TYPE_FOUND,
            category=self.cat2, location='Cafeteria', date_occurred=date.today(),
            status=Item.STATUS_ARCHIVED, reporter=self.user_active
        )

        # Claims
        self.claim1 = Claim.objects.create(
            item=self.item_lost, claimant=self.user_active,
            message='My lost watch from yesterday.', proof_description='Serial 123456.',
            status=Claim.STATUS_PENDING
        )
        self.claim2 = Claim.objects.create(
            item=self.item_found, claimant=self.admin,
            message='My office keys on red ring.', proof_description='Toyota key attached.',
            status=Claim.STATUS_APPROVED
        )

        self.client.login(username='stat_admin', password='password123')

    def test_24_dashboard_user_counts_are_correct(self):
        """Test 24: Dashboard user count and active count are accurate from DB."""
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_users'], 3)       # admin + user_active + user_inactive
        self.assertEqual(response.context['active_users'], 2)      # admin + user_active
        self.assertEqual(response.context['total_admins'], 1)      # stat_admin

    def test_25_dashboard_item_counts_are_correct(self):
        """Test 25: Dashboard item counts (active, archived, lost, found) are correct."""
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_items'], 2)
        self.assertEqual(response.context['total_active_items'], 1)
        self.assertEqual(response.context['total_archived_items'], 1)
        self.assertEqual(response.context['total_lost_items'], 1)
        self.assertEqual(response.context['total_found_items'], 1)

    def test_26_dashboard_claim_counts_are_correct(self):
        """Test 26: Dashboard claim counts (total, pending, approved, rejected) are correct."""
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_claims'], 2)
        self.assertEqual(response.context['total_claims_pending'], 1)
        self.assertEqual(response.context['total_claims_approved'], 1)
        self.assertEqual(response.context['total_claims_rejected'], 0)

    def test_27_dashboard_category_count_is_correct(self):
        """Test 27: Dashboard category count is accurate from DB."""
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_categories'], 2)
