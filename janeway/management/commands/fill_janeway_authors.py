import collections
from django.core.management.base import BaseCommand
from django.db import connection

from demoscene.models import Edit, Releaser
from productions.models import Production
from janeway.matching import productions_with_missing_janeway_authors
from janeway.models import Name, Release


class Command(BaseCommand):
    """Fill in authors from Janeway on productions that don't have the full set of them"""
    def handle(self, *args, **kwargs):
        prod_ids, all_missing_authors = productions_with_missing_janeway_authors()

        print("%d prods with missing authors known from Janeway" % len(prod_ids))
        print("%d different authors among them" % len(all_missing_authors))

        janeway_source_count = Production.objects.filter(id__in=prod_ids, data_source='janeway').count()
        print("%d originated from Janeway" % janeway_source_count)

        edited_count = Edit.objects.filter(focus_object_id__in=prod_ids, action_type='edit_production_core_details').distinct('focus_object_id').count()
        print("%d have had edits" % edited_count)

        authorless_count = Production.objects.filter(id__in=prod_ids, author_nicks__isnull=True, author_affiliation_nicks__isnull=True).count()
        print("%d have no Demozoo authors" % authorless_count)

        for prod in Production.objects.filter(id__in=prod_ids).only('title'):
            print("Checking prod %d: %s" % (prod.id, prod.title))
            if Edit.objects.filter(focus_object_id=prod.id, action_type='edit_production_core_details').exists():
                print("Has had edits - skipping")
                continue

            prod_janeway_ids = [
                int(param)
                for param in prod.links.filter(link_class='KestraBitworldRelease').values_list('parameter', flat=True)
            ]
            janeway_release_ids = Release.objects.filter(janeway_id__in=prod_janeway_ids).values_list('pk', flat=True)
            janeway_author_names = Name.objects.filter(authored_releases__in=janeway_release_ids).select_related('author')
            for name in janeway_author_names:
                janeway_author_id = name.author.janeway_id
                dz_authors = Releaser.objects.filter(external_links__link_class='KestraBitworldAuthor', external_links__parameter=janeway_author_id)
                dz_author_count = dz_authors.count()
                print("\t%s - %d dz releasers" % (name.name, dz_author_count))
