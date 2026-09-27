import csv
import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Profile
from items.models import Item, Category
from claims.models import Claim
from matches.models import ItemMatch


class ReportsAndHealthCheckTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Regular user
        self.regular_user = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='Password123!',
            first_name='John',
            last_name='Doe'
        )
        self.regular_profile, _ = Profile.objects.get_or_create(
            user=self.regular_user,
            defaults={'role': Profile.ROLE_USER}
        )

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username='admin1',
            email='admin1@example.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User'
        )
        self.admin_user.profile.role = Profile.ROLE_ADMIN
        self.admin_user.profile.save()

        # Sample data
        self.category = Category.objects.create(name='Electronics', description='Gadgets and devices')
        self.lost_item = Item.objects.create(
            title='Lost Blue Backpack',
            description='Blue Jansport backpack with laptop inside',
            item_type=Item.TYPE_LOST,
            category=self.category,
            location='Library 2nd Floor',
            date_occurred=timezone.now().date(),
            status=Item.STATUS_ACTIVE,
            reporter=self.regular_user
        )
        self.found_item = Item.objects.create(
            title='Found Blue Backpack',
            description='Blue backpack found near library desk',
            item_type=Item.TYPE_FOUND,
            category=self.category,
            location='Library 2nd Floor',
            date_occurred=timezone.now().date(),
            status=Item.STATUS_ACTIVE,
            reporter=self.admin_user
        )
        self.claim = Claim.objects.create(
            item=self.found_item,
            claimant=self.regular_user,
            message='This is my blue backpack.',
            proof_description='Contains a black Dell charger and notebooks.',
            status=Claim.STATUS_PENDING
        )
        self.match = ItemMatch.objects.create(
            lost_item=self.lost_item,
            found_item=self.found_item,
            score=85,
            status=ItemMatch.STATUS_PENDING,
            score_category=35,
            score_location=25,
            score_title=25
        )

    def test_health_check_endpoint(self):
        """Health check returns 200 OK and status 'ok'."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_reports_anonymous_access_denied(self):
        """Anonymous user redirected to login when accessing reports dashboard."""
        response = self.client.get(reverse('reports:index'))
        self.assertEqual(response.status_code, 302)

    def test_reports_regular_user_access_denied(self):
        """Regular non-admin user cannot access reports dashboard."""
        self.client.login(username='student1', password='Password123!')
        response = self.client.get(reverse('reports:index'))
        # admin_required renders 403.html with 403 status
        self.assertEqual(response.status_code, 403)

    def test_reports_admin_access_allowed(self):
        """Admin user can view reports dashboard with 200 OK and proper context."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Reports &amp; Analytics')
        self.assertIn('total_items', response.context)
        self.assertIn('total_lost', response.context)
        self.assertIn('total_found', response.context)
        self.assertIn('total_claims', response.context)
        self.assertIn('total_matches', response.context)
        self.assertEqual(response.context['total_items'], 2)
        self.assertEqual(response.context['total_lost'], 1)
        self.assertEqual(response.context['total_found'], 1)
        self.assertEqual(response.context['total_claims'], 1)
        self.assertEqual(response.context['total_matches'], 1)

    def test_export_items_csv(self):
        """Admin can export items CSV with proper headers and data."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:export_items'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="items_report_', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)  # Header + at least 1 item
        header = rows[0]
        self.assertEqual(header[0], 'ID')
        self.assertEqual(header[1], 'Title')
        self.assertEqual(header[2], 'Type')
        self.assertEqual(header[3], 'Category')

    def test_export_claims_csv(self):
        """Admin can export claims CSV with proper headers and data."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:export_claims'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="claims_report_', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)
        header = rows[0]
        self.assertEqual(header[0], 'Claim ID')
        self.assertEqual(header[2], 'Item Title')

    def test_export_users_csv_security(self):
        """Admin can export users CSV, verifying no passwords or hashes are included."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:export_users'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        content = response.content.decode('utf-8')
        self.assertNotIn('password', content.lower())
        self.assertNotIn('pbkdf2', content.lower())
        self.assertNotIn('argon2', content.lower())
        self.assertNotIn('bcrypt', content.lower())

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        header = rows[0]
        self.assertIn('Username', header)
        self.assertIn('Email', header)
        self.assertIn('Role', header)

    def test_export_categories_csv(self):
        """Admin can export categories CSV."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:export_categories'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_matches_csv(self):
        """Admin can export matches CSV."""
        self.client.login(username='admin1', password='AdminPassword123!')
        response = self.client.get(reverse('reports:export_matches'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_non_admin_cannot_export(self):
        """Regular user cannot access export endpoints."""
        self.client.login(username='student1', password='Password123!')
        urls = [
            reverse('reports:export_items'),
            reverse('reports:export_claims'),
            reverse('reports:export_users'),
            reverse('reports:export_categories'),
            reverse('reports:export_matches'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
