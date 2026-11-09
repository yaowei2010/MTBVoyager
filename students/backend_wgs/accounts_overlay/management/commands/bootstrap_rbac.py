from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Ensure one existing account has the MTB admin role after the first RBAC deployment."

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", required=True)

    def handle(self, *args, **options):
        username = options["admin_username"].strip()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"Bootstrap admin account does not exist: {username}") from exc
        UserProfile.objects.update_or_create(user=user, defaults={"role": UserProfile.Role.ADMIN})
        self.stdout.write(self.style.SUCCESS(f"MTB admin role confirmed for {username}"))
