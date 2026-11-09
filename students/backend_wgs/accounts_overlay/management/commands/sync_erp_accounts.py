from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.postgres_audit import sync_account
from accounts.roles import get_role


class Command(BaseCommand):
    help = "Synchronize Django account metadata and password hashes to the ERP PostgreSQL table."

    def handle(self, *args, **options):
        count = 0
        for user in User.objects.all().iterator():
            sync_account(user, get_role(user))
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synchronized {count} ERP accounts"))
