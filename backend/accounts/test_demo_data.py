from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from claims.models import Claim
from items.models import Item, Category
from matches.models import ItemMatch
from notifications.models import Notification


class DemoDataCommandTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='demo_seed_admin', email='admin@example.test', password='test-pass-123',
        )

    def test_seed_populates_each_admin_section_and_is_idempotent(self):
        call_command('seed_demo_data', verbosity=0)
        call_command('seed_demo_data', verbosity=0)

        self.assertEqual(User.objects.filter(username__startswith='demo_member_').count(), 8)
        self.assertEqual(Item.objects.filter(title__startswith='DEMO:').count(), 20)
        self.assertEqual(ItemMatch.objects.filter(lost_item__title__startswith='DEMO:').count(), 10)
        self.assertEqual(Claim.objects.filter(item__title__startswith='DEMO:').count(), 6)
        self.assertEqual(Notification.objects.filter(title__startswith='DEMO:').count(), 6)
        self.assertEqual(Category.objects.count(), 10)

        self.client.force_login(self.admin)
        sections = [
            '/admin-dashboard/users', '/admin-dashboard/items', '/admin-dashboard/claims',
            '/admin-dashboard/categories', '/admin-dashboard/matches',
            '/admin-dashboard/notifications', '/reports',
        ]
        for path in sections:
            with self.subTest(path=path):
                response = self.client.get('/api/frontend-page/', {'path': path})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                if path.endswith('/users'):
                    self.assertTrue(any(row['username'].startswith('demo_member_') for row in payload['tableRows']))
                elif path == '/reports':
                    self.assertGreater(payload['stats'][0]['value'], 0)
                elif path.endswith('/categories'):
                    self.assertEqual(len(payload['records']), 10)
                    self.assertTrue(any(record['badge'] != '0 reports' for record in payload['records']))
                else:
                    self.assertTrue(any(record['title'].startswith('DEMO:') for record in payload['records']))

        public_items = self.client.get('/api/items/').json()['results']
        self.assertTrue(any(item['title'].startswith('DEMO:') and item['reporter_name'].startswith('Demo Member') for item in public_items))
