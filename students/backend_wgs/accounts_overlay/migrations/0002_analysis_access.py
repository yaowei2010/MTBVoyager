from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_analysis_access(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Job = apps.get_model("hw1", "existJobs")
    AnalysisAccess = apps.get_model("accounts", "AnalysisAccess")
    users_by_username = {user.username: user for user in User.objects.all()}
    users_by_id = {str(user.pk): user for user in User.objects.all()}
    for job in Job.objects.all().iterator():
        raw_owner = str(job.user_id or "").strip()
        owner = users_by_id.get(raw_owner) or users_by_username.get(raw_owner)
        AnalysisAccess.objects.get_or_create(
            analysis_id=job.jobID,
            defaults={"owner_id": owner.pk if owner else None},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_rbac"),
        ("hw1", "0007_existjobs_genome_build"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="AnalysisAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("analysis_id", models.CharField(db_index=True, max_length=120, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_mtb_analyses", to=settings.AUTH_USER_MODEL)),
                ("assigned_users", models.ManyToManyField(blank=True, related_name="assigned_mtb_analyses", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(seed_analysis_access, migrations.RunPython.noop),
    ]
