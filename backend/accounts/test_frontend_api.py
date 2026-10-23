from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Profile
from claims.models import Claim
from items.models import Category, Item, ReportLocation
from items.locations import LOCATION_CHOICES
from matches.models import ItemMatch
from notifications.models import Notification


class FrontendPageDataFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='page_admin', password='test-pass-123')
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save()
        self.member = User.objects.create_user(username='page_member', password='test-pass-123')
        self.category = Category.objects.create(name='Page data category')
        self.lost = Item.objects.create(
            title='Lost blue bag', description='Blue bag with a silver badge',
            item_type=Item.TYPE_LOST, category=self.category,
            location=LOCATION_CHOICES[0][0], date_occurred=date.today(), reporter=self.member,
        )
        self.found = Item.objects.create(
            title='Found blue bag', description='Blue bag with silver badge',
            item_type=Item.TYPE_FOUND, category=self.category,
            location=LOCATION_CHOICES[0][0], date_occurred=date.today(), reporter=self.member,
        )

    def get_page(self, path):
        return self.client.get('/api/frontend-page/', {'path': path})

    def test_admin_user_detail_and_role_form_are_available(self):
        self.client.force_login(self.admin)
        response = self.get_page(f'/admin-dashboard/users/{self.member.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'page_member')
        self.assertIn(f'/admin-dashboard/users/{self.member.pk}/change-role', [link['href'] for link in response.json()['links']])

        role_response = self.get_page(f'/admin-dashboard/users/{self.member.pk}/change-role')
        self.assertEqual(role_response.json()['mode'], 'form')
        self.assertEqual(role_response.json()['fields'][0]['name'], 'role')

    def test_admin_can_manage_report_location_fields_and_report_form_uses_them(self):
        self.client.force_login(self.admin)
        lab = ReportLocation.objects.create(name='Science Lab 4', kind=ReportLocation.ROOM)
        admin_page = self.get_page('/admin-dashboard/locations')
        self.assertEqual(admin_page.status_code, 200)
        self.assertIn('Science Lab 4', [record['title'] for record in admin_page.json()['records']])
        edit_page = self.get_page(f'/admin-dashboard/locations/{lab.pk}/edit')
        self.assertEqual(edit_page.json()['mode'], 'form')
        report_page = self.get_page('/items/report/found')
        room_field = next(field for field in report_page.json()['fields'] if field['name'] == 'room')
        self.assertIn({'value': 'Science Lab 4', 'label': 'Science Lab 4'}, room_field['options'])
        response = self.client.post(f'/api/admin/locations/{lab.pk}/edit/', {
            'name': 'Science Computer Lab 4', 'kind': ReportLocation.ROOM, 'active': '1',
        })
        self.assertEqual(response.status_code, 302)
        lab.refresh_from_db()
        self.assertEqual(lab.name, 'Science Computer Lab 4')

    def test_non_admin_cannot_open_location_catalog(self):
        self.client.force_login(self.member)
        response = self.get_page('/admin-dashboard/locations')
        self.assertEqual(response.json()['mode'], 'protected')

    def test_django_only_exposes_native_admin_screen_for_admin_ui(self):
        self.assertEqual(self.client.get('/admin-dashboard/').status_code, 404)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_admin_login_redirects_to_next_dashboard_and_session_is_shared(self):
        response = self.client.post('/login/', {'username':self.admin.username, 'password':'test-pass-123'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/admin-dashboard')
        session = self.client.get('/api/session/').json()
        self.assertTrue(session['authenticated'])
        self.assertTrue(session['isAdmin'])
        self.client.post('/logout/')
        self.assertFalse(self.client.get('/api/session/').json()['authenticated'])

    def test_every_admin_navigation_section_has_live_frontend_data(self):
        self.client.force_login(self.admin)
        sections = {
            '/admin-dashboard':'dashboard',
            '/admin-dashboard/users':'table',
            '/admin-dashboard/items':'list',
            '/admin-dashboard/claims':'list',
            '/admin-dashboard/categories':'list',
            '/admin-dashboard/locations':'list',
            '/admin-dashboard/matches':'list',
            '/admin-dashboard/notifications':'list',
            '/reports':'dashboard',
        }
        for path, mode in sections.items():
            with self.subTest(path=path):
                response = self.get_page(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['mode'], mode)

    def test_admin_filters_and_reporter_match_actions_are_connected(self):
        self.client.force_login(self.admin)
        filtered = self.client.get('/api/frontend-page/', {'path':'/admin-dashboard/items','q':'Lost blue','type':Item.TYPE_LOST})
        self.assertEqual([row['id'] for row in filtered.json()['records']], [self.lost.pk])
        match = ItemMatch.objects.create(lost_item=self.lost, found_item=self.found, score=86)
        self.client.force_login(self.member)
        action_page = self.get_page(f'/matches/{match.pk}/confirm')
        self.assertEqual(action_page.status_code, 200)
        self.assertEqual(action_page.json()['mode'], 'action')
        response = self.client.post(f'/matches/{match.pk}/confirm/')
        self.assertEqual(response.status_code, 302)
        match.refresh_from_db()
        self.assertEqual(match.status, ItemMatch.STATUS_CONFIRMED)

    def test_admin_can_open_item_edit_and_archive_forms(self):
        self.client.force_login(self.admin)
        edit_response = self.get_page(f'/items/{self.lost.pk}/edit')
        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(edit_response.json()['mode'], 'form')
        self.assertEqual(edit_response.json()['fields'][0]['value'], self.lost.title)

        archive_response = self.get_page(f'/items/{self.lost.pk}/archive')
        self.assertEqual(archive_response.json()['actionLabel'], 'Confirm archive')

        detail_response = self.get_page(f'/items/{self.lost.pk}')
        labels = [stat['label'] for stat in detail_response.json()['stats']]
        self.assertIn('Reported by', labels)
        self.assertIn('Report submitted', labels)

    def test_admin_match_detail_exposes_review_actions(self):
        match = ItemMatch.objects.create(lost_item=self.lost, found_item=self.found, score=75)
        self.client.force_login(self.admin)
        response = self.get_page(f'/matches/{match.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'/matches/{match.pk}/confirm', [link['href'] for link in response.json()['links']])

        action_response = self.get_page(f'/admin-dashboard/matches/{match.pk}/confirm')
        self.assertEqual(action_response.json()['actionLabel'], 'Confirm match')

    def test_claim_detail_offers_admin_review_for_pending_claim(self):
        claim = Claim.objects.create(
            item=self.found, claimant=self.admin,
            message='This is my bag', proof_description='It has a unique badge',
        )
        self.client.force_login(self.admin)
        response = self.get_page(f'/claims/{claim.pk}')
        self.assertIn(f'/claims/{claim.pk}/review', [link['href'] for link in response.json()['links']])
        audit = {stat['label']: stat['value'] for stat in response.json()['stats']}
        self.assertIn('@page_admin', audit['Claimant'])
        self.assertEqual(audit['Reviewed by'], 'Awaiting reviewer')
        self.assertEqual(audit['Review decision'], 'Pending')

    def test_admin_pages_remain_protected_from_signed_out_visitors(self):
        response = self.get_page('/admin-dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'protected')

    def test_every_admin_section_has_a_frontend_payload(self):
        self.client.force_login(self.admin)
        section_modes = {
            '/admin-dashboard': 'dashboard',
            '/admin-dashboard/users': 'table',
            '/admin-dashboard/items': 'list',
            '/admin-dashboard/claims': 'list',
            '/admin-dashboard/categories': 'list',
            '/admin-dashboard/matches': 'list',
            '/admin-dashboard/notifications': 'list',
            '/reports': 'dashboard',
        }
        for path, expected_mode in section_modes.items():
            with self.subTest(path=path):
                response = self.get_page(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['mode'], expected_mode)
                if path == '/dashboard':
                    explore = response.json()['exploreItems']
                    self.assertEqual([item['id'] for item in explore['lost']], [self.lost.pk])
                    self.assertEqual([item['id'] for item in explore['found']], [self.found.pk])
                if path == '/admin-dashboard':
                    payload = response.json()
                    self.assertEqual(len(payload['stats']), 5)
                    self.assertEqual(len(payload['trends']['7d']), 7)
                    self.assertEqual(len(payload['trends']['30d']), 5)
                    self.assertEqual(len(payload['trends']['6m']), 6)
                    self.assertEqual(len(payload['trends']['1y']), 12)
                    self.assertEqual(sum(point['lost'] for point in payload['trends']['7d']), 1)
                    self.assertEqual(sum(point['found'] for point in payload['trends']['7d']), 1)
                    self.assertNotIn('links', response.json())
                    self.assertEqual(payload['categoryBreakdown'][0]['total'], 2)
                    self.assertEqual(len(payload['claimStatusCounts']), len(Claim.STATUS_CHOICES))
                    self.assertTrue(payload['adminActivity'])

                if path == '/admin-dashboard/items':
                    self.assertTrue(any('@page_member' in value for value in response.json()['records'][0]['meta']))
                if path == '/admin-dashboard/categories':
                    self.assertTrue(any(value.endswith('lost reports') for value in response.json()['records'][0]['meta']))

    def test_explore_payload_identifies_the_reporter(self):
        self.client.force_login(self.member)
        response = self.get_page('/browse')
        record = response.json()['records'][0]
        self.assertEqual(record['reporterName'], self.member.username)
        self.assertEqual(record['reporterUsername'], self.member.username)
        self.assertIsNone(record['reporterAvatar'])

        catalog = self.client.get('/api/items/').json()['results'][0]
        self.assertEqual(catalog['reporter_username'], self.member.username)

    def test_every_user_workspace_section_has_a_frontend_payload(self):
        self.client.force_login(self.member)
        section_modes = {
            '/dashboard': 'dashboard',
            '/items/my-reports': 'list',
            '/claims/my': 'list',
            '/matches': 'list',
            '/notifications': 'notifications',
            '/profile': 'form',
        }
        for path, expected_mode in section_modes.items():
            with self.subTest(path=path):
                response = self.get_page(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['mode'], expected_mode)
                if path == '/profile':
                    self.assertTrue(any(field['name'] == 'profile_image' and field['type'] == 'file' for field in response.json()['fields']))

    def test_profile_settings_label_and_save_flow(self):
        self.client.force_login(self.member)
        page = self.get_page('/profile')
        self.assertEqual(page.json()['actionLabel'], 'Save changes')

        response = self.client.post('/profile/', {
            'first_name': 'Updated',
            'last_name': 'Reporter',
            'email': 'updated-reporter@example.com',
            'phone': '09171234567',
        })
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.member.profile.refresh_from_db()
        self.assertEqual(self.member.first_name, 'Updated')
        self.assertEqual(self.member.last_name, 'Reporter')
        self.assertEqual(self.member.email, 'updated-reporter@example.com')
        self.assertEqual(self.member.profile.phone, '09171234567')

    def test_reporting_pages_require_login(self):
        for path in ['/items/report/lost', '/items/report/found']:
            with self.subTest(path=path):
                response = self.get_page(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['mode'], 'protected')
                self.assertEqual(response.json()['href'], '/login')

    def test_frontend_notification_actions_use_the_signed_in_users_records(self):
        notification = Notification.objects.create(recipient=self.member, title='A new match', message='Check this possible match.')
        self.client.force_login(self.member)
        page = self.get_page('/notifications')
        self.assertEqual(page.json()['mode'], 'notifications')
        self.assertEqual(page.json()['unreadCount'], 1)
        self.assertEqual(page.json()['records'][0]['href'], f'/notifications/{notification.pk}')

        self.assertEqual(self.get_page(f'/notifications/{notification.pk}/read').json()['mode'], 'action')
        response = self.client.post(f'/notifications/{notification.pk}/read/')
        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_frontend_claim_withdraw_confirmation_is_owner_and_pending_only(self):
        claim = Claim.objects.create(item=self.found, claimant=self.admin, message='It belongs to me.', proof_description='Distinct mark on the back.')
        self.client.force_login(self.admin)
        page = self.get_page(f'/claims/{claim.pk}/withdraw')
        self.assertEqual(page.json()['mode'], 'action')
        response = self.client.post(f'/claims/{claim.pk}/withdraw/')
        self.assertEqual(response.status_code, 302)
        claim.refresh_from_db()
        self.assertEqual(claim.status, Claim.STATUS_WITHDRAWN)
