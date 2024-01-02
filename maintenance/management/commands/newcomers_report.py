from django.core.management.base import BaseCommand, CommandParser
from django.db import connection
from django.db.models import Min

from demoscene.models import Releaser


class Command(BaseCommand):
    help = "Generate a listing of candidates for the Meteoriks New Talent award"

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help="Year to generate report for")

    def handle(self, *args, **options):
        year = options['year']
        with connection.cursor() as cursor:
            cursor.execute("""
SELECT DISTINCT releaser_id FROM (
    SELECT DISTINCT demoscene_nick.releaser_id
    FROM productions_production
    INNER JOIN productions_production_author_nicks ON (
        productions_production.id = productions_production_author_nicks.production_id
    )
    INNER JOIN demoscene_nick ON (
        productions_production_author_nicks.nick_id = demoscene_nick.id
    )
    LEFT JOIN productions_production_types ON (
        productions_production.id = productions_production_types.production_id
    )
    WHERE
        EXTRACT(YEAR FROM release_date_date) = %(year)s
        AND (
            productions_production.supertype = 'production'
            OR productions_production_types.productiontype_id IN (27, 28, 56)
        )
    UNION
    SELECT DISTINCT demoscene_nick.releaser_id
    FROM productions_production
    INNER JOIN productions_production_author_affiliation_nicks ON (
        productions_production.id = productions_production_author_affiliation_nicks.production_id
    )
    INNER JOIN demoscene_nick ON (
        productions_production_author_affiliation_nicks.nick_id = demoscene_nick.id
    )
    LEFT JOIN productions_production_types ON (
        productions_production.id = productions_production_types.production_id
    )
    WHERE
        EXTRACT(YEAR FROM release_date_date) = %(year)s
        AND (
            productions_production.supertype = 'production'
            OR productions_production_types.productiontype_id IN (27, 28, 56)
        )
    UNION
    SELECT DISTINCT demoscene_nick.releaser_id
    FROM productions_production
    INNER JOIN productions_credit ON (
        productions_production.id = productions_credit.production_id
    )
    INNER JOIN demoscene_nick ON (
        productions_credit.nick_id = demoscene_nick.id
    )
    LEFT JOIN productions_production_types ON (
        productions_production.id = productions_production_types.production_id
    )
    WHERE
        EXTRACT(YEAR FROM release_date_date) = %(year)s
        AND (
            productions_production.supertype = 'production'
            OR productions_production_types.productiontype_id IN (27, 28, 56)
        )
) AS releasers_this_year;
            """, {'year': year})
            releasers_this_year = [
                releaser_id
                for releaser_id, in cursor.fetchall()
            ]

        for releaser_id in releasers_this_year:
            releaser = Releaser.objects.get(id=releaser_id)

            author_rel_date = releaser.productions().aggregate(rel_date=Min('release_date_date'))['rel_date']
            if author_rel_date and author_rel_date.year < year:
                continue

            affil_rel_date = releaser.member_productions().aggregate(rel_date=Min('release_date_date'))['rel_date']
            if affil_rel_date and affil_rel_date.year < year:
                continue

            credit_rel_date = releaser.credits().aggregate(rel_date=Min('production__release_date_date'))['rel_date']
            if credit_rel_date and credit_rel_date.year < year:
                continue

            print("%s,https://demozoo.org%s" % (releaser.name, releaser.get_absolute_url()))
