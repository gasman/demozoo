# Generated by Django 4.0.8 on 2023-10-21 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0003_phasestaffmember_ordering'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='original_image_sha1',
            field=models.CharField(blank=True, editable=False, max_length=40),
        ),
        migrations.AddField(
            model_name='entry',
            name='thumbnail_height',
            field=models.IntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='entry',
            name='thumbnail_url',
            field=models.CharField(blank=True, editable=False, max_length=255),
        ),
        migrations.AddField(
            model_name='entry',
            name='thumbnail_width',
            field=models.IntegerField(blank=True, editable=False, null=True),
        ),
    ]
