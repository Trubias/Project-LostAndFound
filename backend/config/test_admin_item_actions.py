from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

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
            {'found_description': 'Found near the library entrance.'},
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
        reports_page = self.get_frontend_page('/reports')
        found_reports = next(stat['value'] for stat in reports_page['stats'] if stat['label'] == 'Found reports')
        self.assertEqual(found_reports, 1)

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
        self.assertEqual(action['fields'][0]['name'], 'found_description')

        response = self.client.post(
            f'/items/{self.item.pk}/mark-unclaimed/',
            {'found_description': 'Found beside the library entrance.'},
        )

        self.assertRedirects(response, '/claims/my', fetch_redirect_response=False)
        self.item.refresh_from_db()
        self.assertEqual(self.item.item_type, Item.TYPE_FOUND)
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)
        self.assertEqual(self.item.found_by, self.claimant)
        self.assertIsNotNone(self.item.found_at)
        self.assertEqual(self.item.found_description, 'Found beside the library entrance.')
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
