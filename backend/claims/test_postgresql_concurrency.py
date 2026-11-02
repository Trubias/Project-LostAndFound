"""PostgreSQL-only checks for claim-review row locking."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from django.utils import timezone

from claims.models import Claim
from claims.views import _approve_claim, _record_handoff_confirmation
from items.models import Category, Item


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL row-lock behavior requires PostgreSQL.')
class ConcurrentClaimApprovalTests(TransactionTestCase):
    reset_sequences = True

    def test_two_approvals_for_one_item_only_resolve_one_claim(self):
        category = Category.objects.create(name='Concurrency test category')
        reporter = User.objects.create_user(username='lock_reporter')
        claimant_a = User.objects.create_user(username='lock_claimant_a')
        claimant_b = User.objects.create_user(username='lock_claimant_b')
        reviewer = User.objects.create_user(username='lock_reviewer')
        item = Item.objects.create(
            title='Concurrent review test item',
            description='Used to verify item row locking during competing approvals.',
            item_type=Item.TYPE_FOUND,
            category=category,
            location='Test lab',
            date_occurred=date.today(),
            status=Item.STATUS_ACTIVE,
            reporter=reporter,
        )
        claims = [
            Claim.objects.create(
                item=item,
                claimant=claimant,
                message=f'I can identify this test item number {number}.',
                proof_description=f'Unique test detail number {number}.',
                status=Claim.STATUS_PENDING,
            )
            for number, claimant in enumerate((claimant_a, claimant_b), start=1)
        ]

        start_together = Barrier(2)

        def approve(claim_id):
            close_old_connections()
            try:
                claim = Claim.objects.get(pk=claim_id)
                current_reviewer = User.objects.get(pk=reviewer.pk)
                start_together.wait(timeout=10)
                return _approve_claim(claim, current_reviewer, 'PostgreSQL concurrency test')
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(approve, [claim.pk for claim in claims]))

        item.refresh_from_db()
        statuses = list(Claim.objects.filter(item=item).order_by('pk').values_list('status', flat=True))
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(statuses.count(Claim.STATUS_APPROVED), 1)
        self.assertEqual(statuses.count(Claim.STATUS_REJECTED), 1)
        self.assertEqual(item.status, Item.STATUS_ARCHIVED)

    def test_concurrent_party_confirmations_complete_handoff_without_lost_update(self):
        category = Category.objects.create(name='Handoff concurrency category')
        reporter = User.objects.create_user(username='handoff_reporter')
        claimant = User.objects.create_user(username='handoff_claimant')
        item = Item.objects.create(
            title='Concurrent handoff test item',
            description='Used to verify party confirmations are serialized.',
            item_type=Item.TYPE_FOUND,
            category=category,
            location='Test lab',
            date_occurred=date.today(),
            status=Item.STATUS_ARCHIVED,
            reporter=reporter,
        )
        claim = Claim.objects.create(
            item=item,
            claimant=claimant,
            message='This is my test item and I can identify it.',
            proof_description='It has an exact test-only identifying detail.',
            status=Claim.STATUS_APPROVED,
            handoff_location='Test desk',
            handoff_at=timezone.now() + timedelta(days=1),
            handoff_confirmed_by_claimant_at=timezone.now(),
        )
        start_together = Barrier(2)

        def confirm(user_id):
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                start_together.wait(timeout=10)
                return _record_handoff_confirmation(claim.pk, user)[1]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(confirm, [reporter.pk, claimant.pk]))

        claim.refresh_from_db()
        self.assertEqual(outcomes.count(True), 2)
        self.assertIsNotNone(claim.handoff_returned_by_claimant_at)
        self.assertIsNotNone(claim.handoff_returned_by_reporter_at)
        self.assertIsNotNone(claim.handoff_completed_at)
