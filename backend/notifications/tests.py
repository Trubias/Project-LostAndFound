from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Profile
from items.models import Item, Category
from claims.models import Claim
from notifications.models import Notification
from notifications import services as notif_svc
from matches.models import ItemMatch
from matches import engine as match_engine


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        self.user2 = User.objects.create_user('bob', 'bob@test.com', 'pass123')
        self.category = Category.objects.create(name='Electronics')
        self.item = Item.objects.create(
            title='Blue Backpack',
            description='Contains notebooks',
            item_type=Item.TYPE_LOST,
            category=self.category,
            location='Library',
            date_occurred=date(2026, 9, 20),
            reporter=self.user1,
        )

    def test_notification_creation(self):
        notif, created = notif_svc.create_notification(
            recipient=self.user1,
            notification_type=Notification.TYPE_SYSTEM,
            title='Test Title',
            message='Test message',
            related_item=self.item,
        )
        self.assertTrue(created)
        self.assertEqual(notif.recipient, self.user1)
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.related_item, self.item)

    def test_notification_belongs_to_recipient(self):
        notif, _ = notif_svc.create_notification(
            recipient=self.user1,
            notification_type=Notification.TYPE_SYSTEM,
            title='User 1 Only',
            message='Message',
        )
        self.assertEqual(self.user1.notifications.count(), 1)
        self.assertEqual(self.user2.notifications.count(), 0)

    def test_notification_deduplication(self):
        # Multiple calls with identical parameters should not create duplicates
        n1, c1 = notif_svc.create_notification(
            recipient=self.user1,
            notification_type=Notification.TYPE_ITEM_ARCHIVED,
            title='Item Archived',
            message='Msg',
            related_item=self.item,
        )
        n2, c2 = notif_svc.create_notification(
            recipient=self.user1,
            notification_type=Notification.TYPE_ITEM_ARCHIVED,
            title='Item Archived',
            message='Msg',
            related_item=self.item,
        )
        self.assertTrue(c1)
        self.assertFalse(c2)
        self.assertEqual(n1.pk, n2.pk)
        self.assertEqual(Notification.objects.filter(recipient=self.user1).count(), 1)


class NotificationViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        self.user2 = User.objects.create_user('bob', 'bob@test.com', 'pass123')
        self.notif1 = Notification.objects.create(
            recipient=self.user1,
            title='Notif for Alice',
            message='Hello Alice',
            notification_type=Notification.TYPE_SYSTEM,
        )
        self.notif2 = Notification.objects.create(
            recipient=self.user2,
            title='Notif for Bob',
            message='Hello Bob',
            notification_type=Notification.TYPE_SYSTEM,
        )

    def test_user_sees_only_own_notifications(self):
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notif for Alice')
        self.assertNotContains(response, 'Notif for Bob')

    def test_user_can_mark_own_notification_as_read(self):
        self.client.login(username='alice', password='pass123')
        response = self.client.post(reverse('notifications:mark_read', args=[self.notif1.pk]))
        self.assertEqual(response.status_code, 302)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_user_cannot_modify_another_users_notification(self):
        self.client.login(username='alice', password='pass123')
        # Try to mark Bob's notification as read
        response = self.client.post(reverse('notifications:mark_read', args=[self.notif2.pk]))
        self.assertEqual(response.status_code, 404)
        self.notif2.refresh_from_db()
        self.assertFalse(self.notif2.is_read)

    def test_user_cannot_delete_another_users_notification(self):
        self.client.login(username='alice', password='pass123')
        response = self.client.post(reverse('notifications:delete', args=[self.notif2.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Notification.objects.filter(pk=self.notif2.pk).exists())

    def test_mark_all_as_read(self):
        # Create second unread for alice
        Notification.objects.create(
            recipient=self.user1,
            title='Second Notif',
            message='Hello again',
            notification_type=Notification.TYPE_SYSTEM,
        )
        self.client.login(username='alice', password='pass123')
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 0)
        # Bob's notification remains unread
        self.notif2.refresh_from_db()
        self.assertFalse(self.notif2.is_read)

    def test_unread_count_in_context(self):
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['unread_notifications_count'], 1)


class ClaimNotificationWorkflowTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', 'alice@test.com', 'pass123')
        self.bob = User.objects.create_user('bob', 'bob@test.com', 'pass123')
        self.category = Category.objects.create(name='Electronics')
        self.found_item = Item.objects.create(
            title='Lost iPhone',
            description='Black color found in cafeteria',
            item_type=Item.TYPE_FOUND,
            category=self.category,
            location='Cafeteria',
            date_occurred=date(2026, 9, 21),
            reporter=self.alice,
        )

    def test_claim_submission_creates_notification(self):
        self.client.login(username='bob', password='pass123')
        response = self.client.post(reverse('claims:submit_claim', args=[self.found_item.pk]), {
            'message': 'This is my lost phone that I dropped in cafeteria',
            'proof_description': 'Serial number ending in 123456789 and black case',
        })
        self.assertEqual(response.status_code, 302)
        # Alice (the item reporter) should have received a notification
        notif = Notification.objects.filter(recipient=self.alice).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, Notification.TYPE_CLAIM_SUBMITTED)

    def test_claim_approval_creates_notification(self):
        claim = Claim.objects.create(
            item=self.found_item,
            claimant=self.bob,
            message='My item',
            proof_description='Proof',
        )
        self.client.login(username='alice', password='pass123')
        response = self.client.post(reverse('claims:review_claim', args=[claim.pk]), {
            'action': 'approve',
            'reviewer_notes': 'Verified',
        })
        self.assertEqual(response.status_code, 302)
        # Bob (claimant) should have received an approval notification
        bob_notif = Notification.objects.filter(
            recipient=self.bob,
            notification_type=Notification.TYPE_CLAIM_APPROVED
        ).first()
        self.assertIsNotNone(bob_notif)

    def test_claim_rejection_creates_notification(self):
        claim = Claim.objects.create(
            item=self.found_item,
            claimant=self.bob,
            message='My item',
            proof_description='Proof',
        )
        self.client.login(username='alice', password='pass123')
        response = self.client.post(reverse('claims:review_claim', args=[claim.pk]), {
            'action': 'reject',
            'reviewer_notes': 'Wrong color',
        })
        self.assertEqual(response.status_code, 302)
        # Bob (claimant) should have received a rejection notification
        bob_notif = Notification.objects.filter(
            recipient=self.bob,
            notification_type=Notification.TYPE_CLAIM_REJECTED
        ).first()
        self.assertIsNotNone(bob_notif)
