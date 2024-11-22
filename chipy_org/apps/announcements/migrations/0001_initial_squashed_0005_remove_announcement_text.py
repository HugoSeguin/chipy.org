# Generated by Django 5.1.3 on 2024-11-21 17:21

from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("announcements", "0001_initial"),
        ("announcements", "0002_announcement_end_date"),
        ("announcements", "0003_announcement_text2"),
        ("announcements", "0004_move_ckeditor_data_to_field"),
        ("announcements", "0005_remove_announcement_text"),
    ]

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("headline", models.TextField(max_length="100")),
                (
                    "active",
                    models.BooleanField(
                        default=True, help_text="Has this announcement been published yet?"
                    ),
                ),
                ("photo", models.ImageField(blank=True, null=True, upload_to="announcements")),
                ("link", models.URLField(blank=True, null=True)),
                ("end_date", models.DateTimeField(blank=True, null=True)),
                ("text2", models.TextField(blank=True, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
