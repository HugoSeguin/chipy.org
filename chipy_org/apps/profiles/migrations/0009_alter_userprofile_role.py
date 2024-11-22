# Generated by Django 5.1.3 on 2024-11-21 19:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0008_auto_20220324_2110"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("MEMBER", "Member"),
                    ("ORGANIZER", "Organizer"),
                    ("BOARD", "Board Member"),
                    ("SECRETARY", "Secretary"),
                    ("TREASURER", "Treasurer"),
                    ("CHAIR", "Chair"),
                ],
                default="MEMBER",
                max_length=16,
                verbose_name="Organizational role",
            ),
        ),
    ]
