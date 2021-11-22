# Generated by Django 1.11.8 on 2018-03-05 00:47
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productions', '0007_add_production_search_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='production',
            name='search_title',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
    ]
