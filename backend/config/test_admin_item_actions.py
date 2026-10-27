from io import BytesIO
from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from auditlog.models import AuditEvent
from items.models import Item
from notifications.models import Notification


class AdminMarkFoundTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password-123',
        )
        self.reporter = User.objects.create_user(
            username='reporter',
            email='reporter@example.com',
            password='test-password-123',
        )
        self.claimant = User.objects.create_user(
            username='claimant',
            email='claimant@example.com',
            password='test-password-123',
        )
        self.item = Item.objects.create(
            title='Lost backpack',
            description='Blue backpack with a stitched name tag.',
            item_type=Item.TYPE_LOST,
            location='Library',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.reporter,
        )

    def get_frontend_page(self, path):
        return self.client.get('/api/frontend-page/', {'path': path}).json()

    def test_admin_dashboard_and_modules_return_page_data(self):
        self.client.force_login(self.admin)

        overview = self.client.get('/api/frontend-page/', {'path': '/admin-dashboard'})
        self.assertEqual(overview.status_code, 200, overview.content)
        self.assertEqual(overview.json()['mode'], 'dashboard')

        for path in (
            '/admin-dashboard/users',
            '/admin-dashboard/items',
            '/admin-dashboard/claims',
            '/admin-dashboard/handoffs',
            '/admin-dashboard/activity',
            '/admin-dashboard/flags',
            '/admin-dashboard/categories',
            '/admin-dashboard/locations',
            '/admin-dashboard/matches',
            '/admin-dashboard/notifications',
        ):
            with self.subTest(path=path):
                response = self.client.get('/api/frontend-page/', {'path': path})
                self.assertEqual(response.status_code, 200, response.content)

    @staticmethod
    def evidence_photo():
        contents = BytesIO()
        Image.new('RGB', (8, 8), color='blue').save(contents, format='PNG')
        return SimpleUploadedFile('found.png', contents.getvalue(), content_type='image/png')

    def test_admin_item_drawer_offers_mark_found_and_concern(self):
        self.client.force_login(self.admin)

        details = self.get_frontend_page(f'/items/{self.item.pk}')

        self.assertEqual(
            [link['label'] for link in details['links']],
            ['Claim', 'Report a concern'],
        )
        action = self.get_frontend_page(f'/items/{self.item.pk}/mark-found')
        self.assertEqual(action['mode'], 'form')
        self.assertEqual(action['action'], f'/api/admin/items/{self.item.pk}/mark-found')

    def test_mark_found_updates_reports_audit_and_claims_module(self):
        self.client.force_login(self.admin)

        action = self.get_frontend_page(f'/items/{self.item.pk}/mark-found')
        self.assertEqual(action['mode'], 'form')
        self.assertEqual(action['actionLabel'], 'Confirm')
        self.assertEqual(action['fields'][0]['name'], 'found_description')

        response = self.client.post(
            f'/api/admin/items/{self.item.pk}/mark-found/',
            {
                'found_description': 'Found near the library entrance.',
                'found_image': self.evidence_photo(),
            },
        )

        self.assertRedirects(
            response,
            '/admin-dashboard/claims?updated=1',
            fetch_redirect_response=False,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_type, Item.TYPE_FOUND)
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)
        self.assertEqual(self.item.get_status_display_label(), 'Found')
        self.assertEqual(self.item.get_status_display(), 'Found')
        self.assertEqual(self.item.get_status_badge_class(), 'success')
        self.assertEqual(self.item.found_by, self.admin)
        self.assertEqual(self.item.found_description, 'Found near the library entrance.')
        self.assertTrue(self.item.found_image)
        self.assertTrue(
            AuditEvent.objects.filter(
                action='item.found_reported',
                object_id=str(self.item.pk),
            ).exists()
        )
        owner_notifications = Notification.objects.filter(
            recipient=self.reporter,
            related_item=self.item,
        )
        self.assertEqual(owner_notifications.count(), 1)
        self.assertEqual(owner_notifications.get().title, 'Your lost item has been found')
        self.assertIn('found by Admin', owner_notifications.get().message)

        claims_page = self.get_frontend_page('/admin-dashboard/claims')
        self.assertEqual(claims_page['availableFoundCount'], 1)
        self.assertEqual(claims_page['availableFoundItems'][0]['title'], self.item.title)
        self.assertEqual(claims_page['availableFoundItems'][0]['badge'], 'Available to Claim')
        reports_page = self.get_frontend_page('/reports')
        found_reports = next(stat['value'] for stat in reports_page['stats'] if stat['label'] == 'Found reports')
        self.assertEqual(found_reports, 1)

    def test_owner_can_claim_found_report_and_admin_state_updates(self):
        self.item.item_type = Item.TYPE_FOUND
        self.item.found_by = self.admin
        self.item.found_description = 'Found at the library entrance.'
        self.item.save()
        self.client.force_login(self.reporter)

        reports = self.get_frontend_page('/items/my-reports')
        self.assertIn(f'/items/{self.item.pk}', [record['href'] for record in reports['records']])
        explore_before_claim = self.client.get(
            '/api/frontend-page/',
            {'path': '/browse', 'type': 'FOUND'},
        ).json()
        self.assertIn(
            self.item.pk,
            [record['id'] for record in explore_before_claim['records']],
        )
        dashboard_before_claim = self.get_frontend_page('/dashboard')
        self.assertIn(
            self.item.pk,
            [record['id'] for record in dashboard_before_claim['exploreItems']['found']],
        )
        details = self.get_frontend_page(f'/items/{self.item.pk}')
        self.assertEqual([link['label'] for link in details['links']], ['Back', 'Claim'])

        action = self.get_frontend_page(f'/items/{self.item.pk}/mark-claimed')
        self.assertEqual(action['mode'], 'action')
        self.assertEqual(action['action'], f'/items/{self.item.pk}/mark-claimed')
        edit_action = self.client.get(
            '/api/frontend-page/',
            {'path': f'/items/{self.item.pk}/edit'},
        )
        self.assertEqual(edit_action.status_code, 403)

        self.client.force_login(self.claimant)
        denied = self.client.get('/api/frontend-page/', {'path': f'/items/{self.item.pk}/mark-claimed'})
        self.assertEqual(denied.status_code, 404)
        denied = self.client.post(f'/items/{self.item.pk}/mark-claimed/')
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(self.reporter)
        response = self.client.post(f'/items/{self.item.pk}/mark-claimed/')
        self.assertRedirects(
            response,
            f'/items/{self.item.pk}/',
            fetch_redirect_response=False,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_CLAIMED)

        explore_after_claim = self.client.get(
            '/api/frontend-page/',
            {'path': '/browse', 'type': 'FOUND'},
        ).json()
        self.assertNotIn(
            self.item.pk,
            [record['id'] for record in explore_after_claim['records']],
        )
        dashboard_after_claim = self.get_frontend_page('/dashboard')
        self.assertNotIn(
            self.item.pk,
            [record['id'] for record in dashboard_after_claim['exploreItems']['found']],
        )
        self.assertNotIn(
            self.item.pk,
            [record['id'] for record in self.client.get('/api/items/', {'type': 'FOUND'}).json()['results']],
        )

        details = self.get_frontend_page(f'/items/{self.item.pk}')
        self.assertEqual([link['label'] for link in details['links']], ['Back'])
        self.client.force_login(self.admin)
        claims_page = self.get_frontend_page('/admin-dashboard/claims')
        self.assertEqual(claims_page['availableFoundCount'], 0)
        found_record = next(record for record in claims_page['availableFoundItems'] if record['id'] == self.item.pk)
        self.assertEqual(found_record['badge'], 'Claimed')

    def test_only_owner_can_open_claim_action_for_found_report(self):
        self.item.item_type = Item.TYPE_FOUND
        self.item.found_by = self.admin
        self.item.save()
        self.client.force_login(self.claimant)

        response = self.client.get(
            '/api/frontend-page/',
            {'path': f'/items/{self.item.pk}/mark-claimed'},
        )

        self.assertEqual(response.status_code, 404)

    def test_non_admin_cannot_mark_a_report_found(self):
        self.client.force_login(self.reporter)

        response = self.client.post(
            f'/api/admin/items/{self.item.pk}/mark-found/',
            {'found_description': 'Found beside the library.'},
        )

        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_type, Item.TYPE_LOST)

    def test_admin_can_mark_notification_as_read(self):
        notification = Notification.objects.create(
            recipient=self.reporter,
            related_item=self.item,
            title='Item found',
            message='Your lost item was found.',
        )
        self.client.force_login(self.admin)

        response = self.client.post(f'/api/admin/notifications/{notification.pk}/read/')

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_non_admin_cannot_mark_notification_as_read_from_admin_ledger(self):
        notification = Notification.objects.create(
            recipient=self.reporter,
            related_item=self.item,
            title='Item found',
            message='Your lost item was found.',
        )
        self.client.force_login(self.reporter)

        response = self.client.post(f'/api/admin/notifications/{notification.pk}/read/')

        self.assertEqual(response.status_code, 403)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_found_rejects_already_converted_items(self):
        self.client.force_login(self.admin)
        self.item.item_type = Item.TYPE_FOUND
        self.item.save(update_fields=['item_type'])

        response = self.client.post(f'/api/admin/items/{self.item.pk}/mark-found/')

        self.assertEqual(response.status_code, 409)

    def test_user_can_claim_item_after_admin_marks_it_found(self):
        self.client.force_login(self.admin)
        self.client.post(
            f'/api/admin/items/{self.item.pk}/mark-found/',
            {'found_description': 'Found near the library entrance.'},
        )
        self.client.force_login(self.claimant)

        response = self.client.post(
            f'/claims/item/{self.item.pk}/submit/',
            {
                'message': 'This is my backpack.',
                'proof_description': 'It has my initials on the inside label.',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.item.claims.filter(claimant=self.claimant).exists())

    def test_lost_items_module_requires_sign_in_and_lists_only_active_lost_items(self):
        found_item = Item.objects.create(
            title='Found keys',
            description='Keys found outside the library.',
            item_type=Item.TYPE_FOUND,
            location='Library',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.reporter,
        )
        archived_lost_item = Item.objects.create(
            title='Archived lost phone',
            description='An old lost phone report.',
            item_type=Item.TYPE_LOST,
            location='Gym',
            date_occurred=date.today(),
            status=Item.STATUS_ARCHIVED,
            reporter=self.reporter,
        )

        anonymous_page = self.get_frontend_page('/lost-items')
        self.assertEqual(anonymous_page['mode'], 'protected')

        self.client.force_login(self.claimant)
        lost_page = self.get_frontend_page('/lost-items')

        self.assertEqual(lost_page['title'], 'Lost items')
        self.assertEqual([row['title'] for row in lost_page['records']], [self.item.title])
        self.assertNotIn(found_item.title, [row['title'] for row in lost_page['records']])
        self.assertNotIn(archived_lost_item.title, [row['title'] for row in lost_page['records']])

    def test_lost_items_module_hides_current_users_own_lost_reports(self):
        own_item = Item.objects.create(
            title='My lost wallet',
            description='A brown wallet I reported lost.',
            item_type=Item.TYPE_LOST,
            location='Cafeteria',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=self.claimant,
        )
        self.client.force_login(self.claimant)

        lost_page = self.get_frontend_page('/lost-items')
        my_reports_page = self.get_frontend_page('/items/my-reports')

        self.assertNotIn(own_item.title, [row['title'] for row in lost_page['records']])
        self.assertIn(own_item.title, [row['title'] for row in my_reports_page['records']])

    def test_found_item_detail_offers_back_to_explore_without_submit_claim(self):
        self.item.item_type = Item.TYPE_FOUND
        self.item.save(update_fields=['item_type'])

        details = self.get_frontend_page(f'/items/{self.item.pk}')

        self.assertEqual(
            details['links'],
            [{'label': 'Back to Explore', 'href': '/browse'}],
        )

    def test_reporter_item_detail_has_back_to_reports_and_no_archive_action(self):
        self.client.force_login(self.reporter)

        details = self.get_frontend_page(f'/items/{self.item.pk}')

        self.assertEqual(
            details['links'],
            [
                {'label': 'Back', 'href': '/items/my-reports'},
                {'label': 'Edit report', 'href': f'/items/{self.item.pk}/edit'},
            ],
        )

    def test_dashboard_found_report_link_opens_lost_items_module(self):
        self.client.force_login(self.claimant)

        dashboard = self.get_frontend_page('/dashboard')

        found_report_link = next(link for link in dashboard['links'] if link['label'] == 'Report found')
        self.assertEqual(found_report_link['href'], '/lost-items')

    def test_finder_can_report_lost_item_and_owner_is_notified(self):
        self.client.force_login(self.claimant)

        details = self.get_frontend_page(f'/items/{self.item.pk}')
        self.assertEqual([link['label'] for link in details['links']], ['Claim'])

        action = self.get_frontend_page(f'/items/{self.item.pk}/mark-unclaimed')
        self.assertEqual(action['mode'], 'form')
        self.assertIn(self.item.title, action['summary'])
        self.assertEqual(action['actionLabel'], 'Confirm')
        self.assertEqual(action['action'], f'/items/{self.item.pk}/mark-unclaimed')
        self.assertEqual(
            [field['name'] for field in action['fields']],
            ['found_description', 'found_image'],
        )

        response = self.client.post(
            f'/items/{self.item.pk}/mark-unclaimed/',
            {
                'found_description': 'Found beside the library entrance.',
                'found_image': self.evidence_photo(),
            },
        )

        self.assertRedirects(response, '/claims/my', fetch_redirect_response=False)
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_type, Item.TYPE_FOUND)
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)
        self.assertEqual(self.item.found_by, self.claimant)
        self.assertIsNotNone(self.item.found_at)
        self.assertEqual(self.item.found_description, 'Found beside the library entrance.')
        self.assertTrue(self.item.found_image)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.reporter,
                related_item=self.item,
                title='Your lost item has been found',
                message__contains='found by claimant',
            ).exists()
        )
        self.assertFalse(Notification.objects.filter(recipient=self.claimant).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                action='item.found_reported',
                object_id=str(self.item.pk),
            ).exists()
        )

        found_details = self.get_frontend_page(f'/items/{self.item.pk}')
        self.assertEqual(found_details['links'], [])

        claims_page = self.get_frontend_page('/claims/my')
        found_record = next(record for record in claims_page['records'] if record['title'] == self.item.title)
        self.assertEqual(found_record['badge'], 'Found')
        self.assertIn('Found beside the library entrance.', found_record['meta'][0])
        old_found_items_url = self.get_frontend_page('/items/my-found-items')
        self.assertEqual(old_found_items_url['title'], 'My claims')

        notification = Notification.objects.get(recipient=self.reporter, related_item=self.item)
        self.client.force_login(self.reporter)
        owner_details = self.get_frontend_page(f'/notifications/{notification.pk}')
        self.assertEqual(owner_details['title'], 'Your lost item has been found')
        self.assertTrue(owner_details['image'].endswith('.png'))
        self.assertIn('Finding description', [stat['label'] for stat in owner_details['stats']])
        legacy_owner_details = self.client.get(f'/notifications/{notification.pk}/')
        self.assertContains(legacy_owner_details, 'Finding report')
        self.assertContains(legacy_owner_details, 'Found beside the library entrance.')

        self.client.force_login(self.admin)
        admin_notifications = self.get_frontend_page('/admin-dashboard/notifications')
        admin_record = next(record for record in admin_notifications['records'] if record['id'] == notification.pk)
        self.assertEqual(admin_record['title'], 'This item has been Found')
        self.assertNotIn('Your lost item', admin_record['subtitle'])
        admin_details = self.get_frontend_page(admin_record['href'])
        self.assertEqual(admin_details['title'], 'This item has been Found')
        self.assertTrue(admin_details['image'].endswith('.png'))
        self.assertIn('Finding description', [stat['label'] for stat in admin_details['stats']])
        legacy_admin_notifications = self.client.get('/django-admin/notifications/')
        self.assertContains(legacy_admin_notifications, 'This item has been Found')
        self.assertNotContains(legacy_admin_notifications, 'Your lost item has been found')

    def test_lost_report_form_offers_optional_cell_phone(self):
        self.client.force_login(self.claimant)

        page = self.get_frontend_page('/items/report/lost')

        phone_field = next(field for field in page['fields'] if field['name'] == 'contact_phone')
        self.assertEqual(phone_field['label'], 'Cell phone number (optional)')
        self.assertNotIn('required', phone_field)

    def test_finding_lost_item_requires_a_description(self):
        self.client.force_login(self.claimant)

        self.client.post(f'/items/{self.item.pk}/mark-unclaimed/')

        self.item.refresh_from_db()
        self.assertEqual(self.item.item_type, Item.TYPE_LOST)
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)
        self.assertIsNone(self.item.found_by)
        self.assertFalse(Notification.objects.filter(related_item=self.item).exists())

    def test_reporter_cannot_report_own_item_as_found(self):
        self.client.force_login(self.reporter)

        action = self.get_frontend_page(f'/items/{self.item.pk}/mark-unclaimed')
        self.assertEqual(action['detail'], 'This lost item is not available to report as found.')

        response = self.client.post(f'/items/{self.item.pk}/mark-unclaimed/')

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)
        self.assertIsNone(self.item.found_by)
