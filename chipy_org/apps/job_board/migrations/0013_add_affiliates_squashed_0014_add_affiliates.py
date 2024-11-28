# Generated by Django 2.2.20 on 2021-04-25 09:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('job_board', '0013_add_affiliates'), ('job_board', '0014_add_affiliates')]

    dependencies = [
        ('job_board', '0012_auto_20210111_1945'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Affiliation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('description', models.CharField(max_length=100)),
                ('url', models.URLField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='jobpost',
            name='affiliation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='job_board.Affiliation'),
        ),
    ]
