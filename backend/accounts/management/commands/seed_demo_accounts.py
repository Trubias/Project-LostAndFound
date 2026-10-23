import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Profile


class Command(BaseCommand):
    help = 'Create local demo user and admin accounts; prints generated passwords once.'

    def handle(self, *args, **options):
        if not settings.DEBUG or getattr(settings, 'IS_PRODUCTION', False):
            raise CommandError('Demo accounts can only be created with DJANGO_DEBUG=True outside production.')

        account_specs = (
            ('comlab_demo_user', 'demo.user@local.test', 'Community', 'Member', Profile.ROLE_USER, False),
            ('comlab_demo_admin', 'demo.admin@local.test', 'ComLab', 'Administrator', Profile.ROLE_ADMIN, True),
        )
        existing = [username for username, *_ in account_specs if User.objects.filter(username=username).exists()]
        if existing:
            raise CommandError(
                'A demo account already exists ({}). No accounts or passwords were changed. '
                'Use those credentials if you saved them, or remove the local demo account before reseeding.'.format(
                    ', '.join(existing)
                )
            )

        credentials = []
        with transaction.atomic():
            for username, email, first_name, last_name, role, is_staff in account_specs:
                password = secrets.token_urlsafe(24)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_staff=is_staff,
                )
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.role = role
                profile.save(update_fields=['role'])
                credentials.append((username, password, role))

        self.stdout.write(self.style.SUCCESS('Local demo accounts created. Save these generated passwords now:'))
        for username, password, role in credentials:
            self.stdout.write(f'{role.lower():5}  username: {username}  password: {password}')
