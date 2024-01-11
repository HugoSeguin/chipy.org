# Generated by Django 4.2.8 on 2024-01-10 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0002_alter_meeting_in_person_capacity'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='requested_reviewer',
            field=models.EmailField(blank=True, help_text='(Optional) If we record this video, we can include an emailaddress of a friend or other person to be included inour review process', max_length=254, null=True, verbose_name='Reviewer Email'),
        ),
    ]
