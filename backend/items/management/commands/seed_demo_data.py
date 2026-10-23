from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from claims.models import Claim
from items.models import Category, Item
from matches.models import ItemMatch
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Add clearly marked, repeatable demo records for exercising every Findly workspace section.'

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()
        admin = User.objects.filter(is_superuser=True).first() or User.objects.filter(profile__role=Profile.ROLE_ADMIN).first()
        if not admin:
            self.stderr.write(self.style.ERROR('Create an administrator account before seeding demo records.'))
            return

        members = []
        for index in range(1, 9):
            username = f'demo_member_{index:02d}'
            member, created = User.objects.get_or_create(username=username, defaults={
                'first_name': 'Demo', 'last_name': f'Member {index:02d}',
                'email': f'{username}@example.test', 'is_active': True,
            })
            if created or not member.has_usable_password():
                member.set_password('FindlyDemo2026!')
                member.save(update_fields=['password'])
            member.profile.role = Profile.ROLE_USER
            member.profile.save(update_fields=['role'])
            members.append(member)

        category_names = [
            'Electronics', 'Keys & Keychains', 'Bags & Backpacks', 'Documents & IDs',
            'Clothing & Accessories', 'Wallets & Purses', 'Books & Stationery',
            'Jewelry & Watches', 'Sports Equipment', 'Others',
        ]
        categories = []
        for name in category_names:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={'description': f'Demo category for {name.lower()} reports.'},
            )
            categories.append(category)

        samples = [
            ('wireless earbuds', 'Electronics', 'LOST', 'College Building Main', 'Black case with a small blue sticker.'),
            ('wireless earbuds', 'Electronics', 'FOUND', 'College Building Main', 'Black charging case with a small blue sticker.'),
            ('silver key ring', 'Keys & Keychains', 'LOST', 'FSUU Main Campus', 'Three keys and a green fabric tag.'),
            ('silver key ring', 'Keys & Keychains', 'FOUND', 'FSUU Main Campus', 'Three keys attached to a green fabric tag.'),
            ('canvas backpack', 'Bags & Backpacks', 'LOST', 'College Building Main', 'Olive backpack with a stitched front pocket.'),
            ('canvas backpack', 'Bags & Backpacks', 'FOUND', 'College Building Main', 'Green canvas backpack with a front pocket.'),
            ('student ID holder', 'Documents & IDs', 'LOST', 'FSUU Main Campus', 'Clear holder with a blue lanyard.'),
            ('student ID holder', 'Documents & IDs', 'FOUND', 'FSUU Main Campus', 'Blue lanyard attached to a clear ID holder.'),
            ('checkered umbrella', 'Clothing & Accessories', 'LOST', 'College Building Main', 'Compact black and white checkered umbrella.'),
            ('checkered umbrella', 'Clothing & Accessories', 'FOUND', 'College Building Main', 'Folded black-and-white umbrella with a curved handle.'),
            ('brown card wallet', 'Wallets & Purses', 'LOST', 'FSUU Main Campus', 'Slim brown wallet with a snap closure.'),
            ('brown card wallet', 'Wallets & Purses', 'FOUND', 'FSUU Main Campus', 'Brown card wallet with a snap button.'),
            ('blue notebook', 'Books & Stationery', 'LOST', 'College Building Main', 'Ruled notebook with a handwritten label inside.'),
            ('blue notebook', 'Books & Stationery', 'FOUND', 'College Building Main', 'Blue ruled notebook left in a classroom.'),
            ('silver wristwatch', 'Jewelry & Watches', 'LOST', 'FSUU Main Campus', 'Silver watch with a dark face and metal strap.'),
            ('silver wristwatch', 'Jewelry & Watches', 'FOUND', 'FSUU Main Campus', 'Metal wristwatch with a dark round face.'),
            ('sports bottle', 'Sports Equipment', 'LOST', 'College Building Main', 'Matte red bottle with a black lid.'),
            ('sports bottle', 'Sports Equipment', 'FOUND', 'College Building Main', 'Red water bottle with a black cap.'),
            ('folding phone stand', 'Others', 'LOST', 'FSUU Main Campus', 'Small gray folding desk stand.'),
            ('folding phone stand', 'Others', 'FOUND', 'FSUU Main Campus', 'Compact gray phone holder found near the lobby.'),
        ]
        items = []
        for index, (label, category_name, item_type, location, description) in enumerate(samples):
            days_ago = (index // 2) * 11 + (index % 2)
            title = f'DEMO: {label.title()} ({"Lost" if item_type == Item.TYPE_LOST else "Found"})'
            item, _ = Item.objects.get_or_create(title=title, defaults={
                'description': f'[DEMO RECORD] {description}',
                'item_type': item_type,
                'category': next(category for category in categories if category.name == category_name),
                'location': location,
                'building': 'College Building Main',
                'date_occurred': today - timedelta(days=days_ago),
                'reporter': members[index % len(members)],
                'status': Item.STATUS_ACTIVE if index < 18 else Item.STATUS_ARCHIVED,
            })
            Item.objects.filter(pk=item.pk).update(created_at=now - timedelta(days=days_ago))
            items.append(item)

        lost_items = items[::2]
        found_items = items[1::2]
        matches_created = 0
        for index, (lost, found) in enumerate(zip(lost_items, found_items)):
            match, created = ItemMatch.objects.get_or_create(lost_item=lost, found_item=found, defaults={
                'score': 88 - index * 2,
                'status': [ItemMatch.STATUS_PENDING, ItemMatch.STATUS_CONFIRMED, ItemMatch.STATUS_PENDING, ItemMatch.STATUS_DISMISSED][index % 4],
                'score_category': 25, 'score_location': 20, 'score_title': 28 - index,
                'score_description': 15 - (index % 4), 'score_date': 10, 'score_image': 0,
            })
            if created:
                matches_created += 1
            ItemMatch.objects.filter(pk=match.pk).update(created_at=now - timedelta(days=index * 9 + 1))

        claims_created = 0
        claims = []
        statuses = [Claim.STATUS_PENDING, Claim.STATUS_PENDING, Claim.STATUS_APPROVED, Claim.STATUS_APPROVED, Claim.STATUS_REJECTED, Claim.STATUS_WITHDRAWN]
        for index, status in enumerate(statuses):
            item = found_items[index]
            claimant = members[(index + 2) % len(members)]
            claim, created = Claim.objects.get_or_create(item=item, claimant=claimant, defaults={
                'message': f'[DEMO] I believe this {item.title.removeprefix("DEMO: ")} belongs to me.',
                'proof_description': '[DEMO] I can identify a unique mark not shown in the public report.',
                'status': status,
                'reviewed_by': admin if status in (Claim.STATUS_APPROVED, Claim.STATUS_REJECTED) else None,
                'reviewed_at': now - timedelta(days=index + 1) if status in (Claim.STATUS_APPROVED, Claim.STATUS_REJECTED) else None,
                'reviewer_notes': '[DEMO] Sample review decision for testing.' if status in (Claim.STATUS_APPROVED, Claim.STATUS_REJECTED) else '',
            })
            if created:
                claims_created += 1
            Claim.objects.filter(pk=claim.pk).update(created_at=now - timedelta(days=index * 3 + 1))
            claims.append(claim)

        notifications_created = 0
        notification_samples = [
            (Notification.TYPE_POSSIBLE_MATCH, 'DEMO: Possible match found', 'A possible lost and found match is ready to review.', found_items[0], None),
            (Notification.TYPE_CLAIM_SUBMITTED, 'DEMO: New claim submitted', 'A sample ownership claim has been submitted.', found_items[1], claims[1]),
            (Notification.TYPE_CLAIM_APPROVED, 'DEMO: Claim approved', 'A sample claim was approved by the administrator.', found_items[2], claims[2]),
            (Notification.TYPE_CLAIM_REJECTED, 'DEMO: Claim needs review', 'A sample claim decision is available.', found_items[4], claims[4]),
            (Notification.TYPE_ITEM_RESTORED, 'DEMO: Report restored', 'A sample report was restored to the community board.', lost_items[0], None),
            (Notification.TYPE_SYSTEM, 'DEMO: Welcome to Findly', 'This is a sample notification for workspace testing.', None, None),
        ]
        for index, (notification_type, title, message, related_item, related_claim) in enumerate(notification_samples):
            notification, created = Notification.objects.get_or_create(
                recipient=members[index % len(members)], title=title,
                defaults={
                    'notification_type': notification_type, 'message': message,
                    'related_item': related_item, 'related_claim': related_claim,
                    'is_read': index % 2 == 0,
                },
            )
            notifications_created += int(created)

        self.stdout.write(self.style.SUCCESS(
            'Demo data ready. Added/available: 8 demo users, 20 demo reports, 10 categories, '
            f'{ItemMatch.objects.filter(lost_item__in=lost_items).count()} matches, '
            f'{Claim.objects.filter(item__in=found_items).count()} claims, {notifications_created} new notifications. '
            'All sample records are labeled DEMO and are safe to re-seed. '
            'Demo member login: demo_member_01 through demo_member_08 / FindlyDemo2026!'
        ))
