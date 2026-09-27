from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date

from accounts.models import Profile
from items.models import Category, Item
from items.forms import ItemForm, CategoryForm


class ItemsSprint2Tests(TestCase):
    def setUp(self):
        self.client = Client()

        # Regular user 1
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123'
        )
        self.profile1, _ = Profile.objects.get_or_create(user=self.user1, defaults={'role': Profile.ROLE_USER})
        self.profile1.role = Profile.ROLE_USER
        self.profile1.save()

        # Regular user 2
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123'
        )
        self.profile2, _ = Profile.objects.get_or_create(user=self.user2, defaults={'role': Profile.ROLE_USER})
        self.profile2.role = Profile.ROLE_USER
        self.profile2.save()

        # Admin user
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='password123'
        )
        self.admin_profile, _ = Profile.objects.get_or_create(user=self.admin, defaults={'role': Profile.ROLE_ADMIN})
        self.admin_profile.role = Profile.ROLE_ADMIN
        self.admin_profile.save()

        # Category
        self.category = Category.objects.create(name='Electronics', description='Electronic gadgets')

        # Items
        self.item_lost = Item.objects.create(
            title='Blue Backpack',
            description='A blue nylon backpack with laptop inside',
            item_type=Item.TYPE_LOST,
            category=self.category,
            location='Library 2nd floor',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.user1
        )

        self.item_found = Item.objects.create(
            title='Silver Watch',
            description='Stainless steel wrist watch found on bench',
            item_type=Item.TYPE_FOUND,
            category=self.category,
            location='Cafeteria bench',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.user2
        )

    # ─────────────────────────────────────────────
    # Model Tests
    # ─────────────────────────────────────────────
    def test_category_model_str(self):
        self.assertEqual(str(self.category), 'Electronics')

    def test_item_model_methods(self):
        self.assertTrue(self.item_lost.is_lost())
        self.assertFalse(self.item_lost.is_found())
        self.assertTrue(self.item_lost.is_active())
        self.assertFalse(self.item_lost.is_archived())
        self.assertIn('Blue Backpack', str(self.item_lost))

        self.assertTrue(self.item_found.is_found())
        self.assertFalse(self.item_found.is_lost())

    # ─────────────────────────────────────────────
    # Form Validation Tests
    # ─────────────────────────────────────────────
    def test_item_form_valid(self):
        form_data = {
            'title': 'Lost Keys Set',
            'description': 'A bunch of house keys on a red lanyard',
            'category': self.category.id,
            'location': 'Gym Locker Room',
            'date_occurred': date.today(),
        }
        form = ItemForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_item_form_invalid_short_title(self):
        form_data = {
            'title': 'ab',
            'description': 'Valid description with enough characters',
            'location': 'Somewhere',
            'date_occurred': date.today(),
        }
        form = ItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_category_form_unique_name(self):
        form = CategoryForm(data={'name': 'electronics'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    # ─────────────────────────────────────────────
    # View & Workflow Tests
    # ─────────────────────────────────────────────
    def test_report_lost_item(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('items:report_lost'), {
            'title': 'Black Leather Wallet',
            'description': 'Contains driver license and some cash',
            'category': self.category.id,
            'location': 'Main Hallway',
            'date_occurred': str(date.today()),
        })
        self.assertEqual(response.status_code, 302)
        item = Item.objects.get(title='Black Leather Wallet')
        self.assertEqual(item.reporter, self.user1)
        self.assertEqual(item.item_type, Item.TYPE_LOST)
        self.assertEqual(item.status, Item.STATUS_ACTIVE)

    def test_report_found_item(self):
        self.client.login(username='user2', password='password123')
        response = self.client.post(reverse('items:report_found'), {
            'title': 'AirPods Pro Case',
            'description': 'White wireless case with small scratch',
            'category': self.category.id,
            'location': 'Student Lounge',
            'date_occurred': str(date.today()),
        })
        self.assertEqual(response.status_code, 302)
        item = Item.objects.get(title='AirPods Pro Case')
        self.assertEqual(item.reporter, self.user2)
        self.assertEqual(item.item_type, Item.TYPE_FOUND)

    def test_browse_items_and_filtering(self):
        # Browse list should show both active items
        response = self.client.get(reverse('items:item_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blue Backpack')
        self.assertContains(response, 'Silver Watch')

        # Filter by LOST
        response_lost = self.client.get(reverse('items:item_list') + '?type=LOST')
        self.assertContains(response_lost, 'Blue Backpack')
        self.assertNotContains(response_lost, 'Silver Watch')

        # Filter by FOUND
        response_found = self.client.get(reverse('items:item_list') + '?type=FOUND')
        self.assertContains(response_found, 'Silver Watch')
        self.assertNotContains(response_found, 'Blue Backpack')

        # Search query
        response_search = self.client.get(reverse('items:item_list') + '?q=Backpack')
        self.assertContains(response_search, 'Blue Backpack')
        self.assertNotContains(response_search, 'Silver Watch')

    def test_my_items_view(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('items:my_items'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blue Backpack')
        self.assertNotContains(response, 'Silver Watch')

    def test_edit_item_by_owner(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('items:edit_item', kwargs={'pk': self.item_lost.pk}), {
            'title': 'Blue Backpack Updated',
            'description': 'A blue nylon backpack with laptop inside - updated',
            'category': self.category.id,
            'location': 'Library 3rd floor',
            'date_occurred': str(date.today()),
        })
        self.assertEqual(response.status_code, 302)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.title, 'Blue Backpack Updated')
        self.assertEqual(self.item_lost.reporter, self.user1)

    def test_edit_item_forbidden_for_other_user(self):
        # user2 attempts to edit user1's item
        self.client.login(username='user2', password='password123')
        response = self.client.post(reverse('items:edit_item', kwargs={'pk': self.item_lost.pk}), {
            'title': 'Hacked Title',
            'description': 'Trying to modify an item not owned by me',
            'location': 'Anywhere',
            'date_occurred': str(date.today()),
        })
        self.assertEqual(response.status_code, 403)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.title, 'Blue Backpack')

    def test_edit_item_by_admin(self):
        # Admin can edit any item
        self.client.login(username='adminuser', password='password123')
        response = self.client.post(reverse('items:edit_item', kwargs={'pk': self.item_lost.pk}), {
            'title': 'Admin Corrected Backpack',
            'description': 'A blue nylon backpack with laptop inside',
            'category': self.category.id,
            'location': 'Library 2nd floor',
            'date_occurred': str(date.today()),
        })
        self.assertEqual(response.status_code, 302)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.title, 'Admin Corrected Backpack')

    def test_archive_and_restore_by_owner(self):
        self.client.login(username='user1', password='password123')
        # Archive
        response = self.client.post(reverse('items:archive_item', kwargs={'pk': self.item_lost.pk}))
        self.assertEqual(response.status_code, 302)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.status, Item.STATUS_ARCHIVED)

        # Restore
        response = self.client.post(reverse('items:restore_item', kwargs={'pk': self.item_lost.pk}))
        self.assertEqual(response.status_code, 302)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.status, Item.STATUS_ACTIVE)

    def test_archive_forbidden_for_other_user(self):
        self.client.login(username='user2', password='password123')
        response = self.client.post(reverse('items:archive_item', kwargs={'pk': self.item_lost.pk}))
        self.assertEqual(response.status_code, 403)
        self.item_lost.refresh_from_db()
        self.assertEqual(self.item_lost.status, Item.STATUS_ACTIVE)

    # ─────────────────────────────────────────────
    # Category Management Tests (Admin only)
    # ─────────────────────────────────────────────
    def test_category_list_forbidden_for_regular_user(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('items:category_list'))
        self.assertEqual(response.status_code, 403)

    def test_category_list_accessible_by_admin(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.get(reverse('items:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Electronics')

    def test_category_create_by_admin(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.post(reverse('items:category_create'), {
            'name': 'Musical Instruments',
            'description': 'Guitars, flutes, keyboards',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='Musical Instruments').exists())


class ItemsSprint3SearchAndDiscoveryTests(TestCase):
    """Exhaustive tests covering all 20 Sprint 3 Search, Filtering & Discovery requirements."""

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username='discovery_user',
            email='discovery@example.com',
            password='password123'
        )
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={'role': Profile.ROLE_USER})

        self.cat_electronics = Category.objects.create(name='Electronics', description='Gadgets')
        self.cat_books = Category.objects.create(name='Books', description='Textbooks and notes')
        self.cat_clothing = Category.objects.create(name='Clothing', description='Apparel')

        # Item 1: Lost Phone (Electronics, Library, 2026-09-05)
        self.item1 = Item.objects.create(
            title='iPhone 13 Midnight Black',
            description='Lost inside the quiet reading room with a clear silicone case',
            item_type=Item.TYPE_LOST,
            category=self.cat_electronics,
            location='Main Campus Library 2nd Floor',
            date_occurred=date(2026, 9, 5),
            status=Item.STATUS_ACTIVE,
            reporter=self.user
        )

        # Item 2: Found Calculator (Electronics, Cafeteria, 2026-09-12)
        self.item2 = Item.objects.create(
            title='Casio Scientific Calculator FX',
            description='Scientific graphing calculator left on the cafeteria table',
            item_type=Item.TYPE_FOUND,
            category=self.cat_electronics,
            location='Student Cafeteria Table 4',
            date_occurred=date(2026, 9, 12),
            status=Item.STATUS_ACTIVE,
            reporter=self.user
        )

        # Item 3: Lost Textbook (Books, Gym, 2026-09-20)
        self.item3 = Item.objects.create(
            title='Calculus Early Transcendentals',
            description='Hardcover mathematics textbook with yellow highlighter marks',
            item_type=Item.TYPE_LOST,
            category=self.cat_books,
            location='University Sports Gym',
            date_occurred=date(2026, 9, 20),
            status=Item.STATUS_ACTIVE,
            reporter=self.user
        )

        # Item 4: Archived Item (Should NEVER appear in public search)
        self.archived_item = Item.objects.create(
            title='Archived Lost Leather Jacket',
            description='Brown vintage leather jacket that was resolved and archived',
            item_type=Item.TYPE_LOST,
            category=self.cat_clothing,
            location='Auditorium Hall',
            date_occurred=date(2026, 9, 1),
            status=Item.STATUS_ARCHIVED,
            reporter=self.user
        )

    # 1. Search by title
    def test_01_search_by_title(self):
        response = self.client.get(reverse('items:item_list') + '?q=iPhone')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Casio Scientific Calculator')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 2. Search by description
    def test_02_search_by_description(self):
        response = self.client.get(reverse('items:item_list') + '?q=graphing')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')

    # 3. Search by location
    def test_03_search_by_location(self):
        response = self.client.get(reverse('items:item_list') + '?q=Gym')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calculus Early Transcendentals')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')

    # 4. Search by category name
    def test_04_search_by_category_name(self):
        response = self.client.get(reverse('items:item_list') + '?q=Books')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calculus Early Transcendentals')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')

    # 5. Lost filter
    def test_05_lost_filter(self):
        response = self.client.get(reverse('items:item_list') + '?type=LOST')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertContains(response, 'Calculus Early Transcendentals')
        self.assertNotContains(response, 'Casio Scientific Calculator FX')

    # 6. Found filter
    def test_06_found_filter(self):
        response = self.client.get(reverse('items:item_list') + '?type=FOUND')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 7. Category filter
    def test_07_category_filter(self):
        response = self.client.get(reverse('items:item_list') + f'?category={self.cat_electronics.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 8. Location filter
    def test_08_location_filter(self):
        response = self.client.get(reverse('items:item_list') + '?location=Library')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Casio Scientific Calculator FX')

    # 9. Date From filter
    def test_09_date_from_filter(self):
        # Items occurred on or after 2026-09-10
        response = self.client.get(reverse('items:item_list') + '?date_from=2026-09-10')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertContains(response, 'Calculus Early Transcendentals')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')

    # 10. Date To filter
    def test_10_date_to_filter(self):
        # Items occurred on or before 2026-09-10
        response = self.client.get(reverse('items:item_list') + '?date_to=2026-09-10')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 11. Sorting
    def test_11_sorting(self):
        # Title A-Z
        response = self.client.get(reverse('items:item_list') + '?sort=title_asc')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        pos_calc = content.find('Calculus Early Transcendentals')
        pos_casio = content.find('Casio Scientific Calculator FX')
        pos_iphone = content.find('iPhone 13 Midnight Black')
        self.assertTrue(pos_calc < pos_casio < pos_iphone)

        # Title Z-A
        response_desc = self.client.get(reverse('items:item_list') + '?sort=title_desc')
        self.assertEqual(response_desc.status_code, 200)
        content_desc = response_desc.content.decode('utf-8')
        pos_calc = content_desc.find('Calculus Early Transcendentals')
        pos_iphone = content_desc.find('iPhone 13 Midnight Black')
        self.assertTrue(pos_iphone < pos_calc)

    # 12. Combined filters
    def test_12_combined_filters(self):
        # Search 'Black' + Type LOST + Category Electronics + Location Library
        url = reverse('items:item_list') + f'?q=Black&type=LOST&category={self.cat_electronics.id}&location=Library'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 13. Clear filters
    def test_13_clear_filters(self):
        response = self.client.get(reverse('items:item_list'))
        self.assertEqual(response.status_code, 200)
        # Without filters, all active items are rendered
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertContains(response, 'Calculus Early Transcendentals')

    # 14. No results
    def test_14_no_results(self):
        response = self.client.get(reverse('items:item_list') + '?q=NonExistentKeywordXYZ')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No items found.')
        self.assertContains(response, 'Try changing your search or filters.')
        self.assertContains(response, 'Clear Filters')

    # 15. Pagination (10 items per page)
    def test_15_pagination(self):
        # Create 12 additional active items (total 15 active items)
        for i in range(12):
            Item.objects.create(
                title=f'Extra Item {i+1}',
                description=f'Description for extra item {i+1}',
                item_type=Item.TYPE_LOST,
                location='Somewhere on campus',
                date_occurred=date.today(),
                status=Item.STATUS_ACTIVE,
                reporter=self.user
            )

        response = self.client.get(reverse('items:item_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 10)
        self.assertTrue(response.context['page_obj'].has_next())

        # Page 2
        response_p2 = self.client.get(reverse('items:item_list') + '?page=2')
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(len(response_p2.context['items']), 5)

    # 16. Pagination preserves filters
    def test_16_pagination_preserves_filters(self):
        for i in range(12):
            Item.objects.create(
                title=f'Extra Lost Gadget {i+1}',
                description=f'A unique gadget {i+1}',
                item_type=Item.TYPE_LOST,
                category=self.cat_electronics,
                location='Campus Center',
                date_occurred=date.today(),
                status=Item.STATUS_ACTIVE,
                reporter=self.user
            )

        response = self.client.get(reverse('items:item_list') + '?type=LOST&category=' + str(self.cat_electronics.id) + '&page=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type=LOST')
        self.assertContains(response, f'category={self.cat_electronics.id}')

    # 17. Archived items do not appear in public search
    def test_17_archived_items_excluded_from_public_search(self):
        response = self.client.get(reverse('items:item_list') + '?q=Leather')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Archived Lost Leather Jacket')

    # 18. /items/lost/ works
    def test_18_lost_items_view(self):
        response = self.client.get(reverse('items:lost_items'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lost Items')
        self.assertContains(response, 'iPhone 13 Midnight Black')
        self.assertContains(response, 'Calculus Early Transcendentals')
        self.assertNotContains(response, 'Casio Scientific Calculator FX')

    # 19. /items/found/ works
    def test_19_found_items_view(self):
        response = self.client.get(reverse('items:found_items'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Found Items')
        self.assertContains(response, 'Casio Scientific Calculator FX')
        self.assertNotContains(response, 'iPhone 13 Midnight Black')
        self.assertNotContains(response, 'Calculus Early Transcendentals')

    # 20. Unauthenticated users cannot access protected features
    def test_20_unauthenticated_users_redirected(self):
        # Reporting lost requires login
        resp_lost = self.client.get(reverse('items:report_lost'))
        self.assertEqual(resp_lost.status_code, 302)
        self.assertIn('/login/', resp_lost.url)

        # Reporting found requires login
        resp_found = self.client.get(reverse('items:report_found'))
        self.assertEqual(resp_found.status_code, 302)
        self.assertIn('/login/', resp_found.url)

        # My reports requires login
        resp_my = self.client.get(reverse('items:my_items'))
        self.assertEqual(resp_my.status_code, 302)
        self.assertIn('/login/', resp_my.url)

