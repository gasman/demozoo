from collections import defaultdict
import itertools

from django.db import connection
from django.db.models import Q

from demoscene.models import Releaser, ReleaserExternalLink
from demoscene.utils.text import generate_search_title, strip_music_extensions
from janeway.importing import import_release
from janeway.models import AuthorMatchInfo, Release as JanewayRelease
from platforms.models import Platform
from productions.models import Production, ProductionLink, ProductionType


def get_dz_releaser_ids_matching_by_name_and_type(janeway_author):
    """
    Return a list of Demozoo releaser IDs which match this Janeway author by at least one name,
    and are the same type (scener or group)
    """
    names = [generate_search_title(name.name) for name in janeway_author.names.all()]
    return list(Releaser.objects.filter(
        is_group=janeway_author.is_group,
        nicks__variants__search_title__in=names,
    ).distinct().values_list('id', flat=True))


def exclude_dz_releasers_with_crosslink(releaser_ids, janeway_author):
    """
    Given a list of Demozoo releaser IDs, filter out the ones that have an existing
    cross-link to the given Janeway author
    """
    already_linked_releasers = list(ReleaserExternalLink.objects.filter(
        link_class='KestraBitworldAuthor', parameter=janeway_author.janeway_id,
        releaser_id__in=releaser_ids
    ).values_list('releaser_id', flat=True))

    return [i for i in releaser_ids if i not in already_linked_releasers]


def get_production_match_data(releaser):
    amiga_platform_ids = list(Platform.objects.filter(name__startswith='Amiga').values_list('id', flat=True))
    tracked_music_prodtype = ProductionType.objects.get(internal_name='tracked-music')

    releaser_janeway_ids = [
        int(param)
        for param in releaser.external_links.filter(link_class='KestraBitworldAuthor').values_list('parameter', flat=True)
    ]

    q_match_by_author = (Q(author_nicks__releaser=releaser) | Q(author_affiliation_nicks__releaser=releaser))
    q_match_amiga_platform = Q(platforms__in=amiga_platform_ids)
    q_match_platformless_tracked_music = Q(platforms__isnull=True, types=tracked_music_prodtype)

    dz_prod_candidates = list(Production.objects.filter(
        q_match_by_author &
        (q_match_amiga_platform | q_match_platformless_tracked_music)
    ).distinct().only('id', 'title', 'supertype'))

    janeway_release_candidates = list(
        JanewayRelease.objects.filter(author_names__author__janeway_id__in=releaser_janeway_ids).order_by('title')
    )

    matched_links = list(ProductionLink.objects.filter(
        Q(link_class='KestraBitworldRelease') &
        (
            Q(production__id__in=[prod.id for prod in dz_prod_candidates]) |
            Q(parameter__in=[prod.janeway_id for prod in janeway_release_candidates])
        )
    ).select_related('production').order_by('production__title'))
    matched_janeway_ids = {int(link.parameter) for link in matched_links}
    matched_dz_ids = {link.production_id for link in matched_links}

    matched_janeway_release_names_by_id = {
        prod.janeway_id: prod.title
        for prod in JanewayRelease.objects.filter(janeway_id__in=matched_janeway_ids)
    }

    matched_prods = [
        (
            link.production_id,  # demozoo ID
            link.production.title,  # demozoo title
            link.production.get_absolute_url(),  # demozoo URL
            link.parameter,  # janeway ID
            matched_janeway_release_names_by_id.get(int(link.parameter), "(Janeway release #%s)" % link.parameter),  # Janeway title with fallback
            "http://janeway.exotica.org.uk/release.php?id=%s" % link.parameter,
            link.production.supertype,
        )
        for link in matched_links
    ]

    unmatched_demozoo_prods = [
        (prod.id, prod.title, prod.get_absolute_url(), prod.supertype) for prod in dz_prod_candidates
        if prod.id not in matched_dz_ids
    ]

    unmatched_janeway_releases = [
        (prod.janeway_id, prod.title, "http://janeway.exotica.org.uk/release.php?id=%d" % prod.janeway_id, prod.supertype) for prod in janeway_release_candidates
        if prod.janeway_id not in matched_janeway_ids
    ]

    return unmatched_demozoo_prods, unmatched_janeway_releases, matched_prods


def automatch_productions(releaser):
    unmatched_demozoo_prods, unmatched_janeway_prods, matched_prods = get_production_match_data(releaser)

    matched_production_count = len(matched_prods)
    unmatched_demozoo_production_count = len(unmatched_demozoo_prods)
    unmatched_janeway_production_count = len(unmatched_janeway_prods)

    # mapping of lowercased prod title to a pair of lists of demozoo IDs and pouet IDs of
    # prods with that name
    prods_by_name_and_supertype = defaultdict(lambda: ([], []))

    for id, title, url, supertype in unmatched_demozoo_prods:
        prods_by_name_and_supertype[(generate_search_title(title), supertype)][0].append(id)

    for id, title, url, supertype in unmatched_janeway_prods:
        if supertype == 'music':
            title = strip_music_extensions(title)
        prods_by_name_and_supertype[(generate_search_title(title), supertype)][1].append(id)

    just_matched_janeway_ids = set()

    for (title, supertype), (demozoo_ids, janeway_ids) in prods_by_name_and_supertype.items():
        if len(demozoo_ids) == 1 and len(janeway_ids) == 1:
            ProductionLink.objects.create(
                production_id=demozoo_ids[0],
                link_class='KestraBitworldRelease',
                parameter=janeway_ids[0],
                is_download_link=False,
                source='janeway-automatch',
            )
            just_matched_janeway_ids.add(janeway_ids[0])
            matched_production_count += 1
            unmatched_demozoo_production_count -= 1
            unmatched_janeway_production_count -= 1

    if unmatched_demozoo_production_count == 0:
        # all matchable prods are accounted for, so let's go on and import the remaining ones from janeway
        for id, title, url, supertype in unmatched_janeway_prods:
            if id in just_matched_janeway_ids:
                continue

            import_release(JanewayRelease.objects.get(janeway_id=id))
            matched_production_count += 1
            unmatched_janeway_production_count -= 1

    AuthorMatchInfo.objects.update_or_create(
        releaser_id=releaser.id, defaults={
            'matched_production_count': matched_production_count,
            'unmatched_demozoo_production_count': unmatched_demozoo_production_count,
            'unmatched_janeway_production_count': unmatched_janeway_production_count,
        }
    )


def productions_with_missing_janeway_authors():
    """
    Return a list of production IDs that have Janeway cross-links mentioning authors that aren't
    represented in the Demozoo entry (typically because there are multiple releasers with the same
    Janeway ID and the auto-importer didn't know which one to use)
    """
    productions = {}

    # productions and the author IDs from their corresponding janeway records
    cursor = connection.cursor()
    cursor.execute("""
        SELECT productions_productionlink.production_id, janeway_author.janeway_id
        FROM productions_productionlink
        INNER JOIN janeway_release ON (
            CAST (productions_productionlink.parameter AS integer) = janeway_release.janeway_id
        )
        INNER JOIN janeway_release_author_names ON (
            janeway_release.id = janeway_release_author_names.release_id
        )
        INNER JOIN janeway_name ON (
            janeway_release_author_names.name_id = janeway_name.id
        )
        INNER JOIN janeway_author ON (
            janeway_name.author_id = janeway_author.id
        )
        WHERE productions_productionlink.link_class = 'KestraBitworldRelease'
        ORDER BY productions_productionlink.production_id
    """)

    for production_id, rows in itertools.groupby(cursor.fetchall(), lambda row: row[0]):
        productions[production_id] = {'janeway_authors': set(row[1] for row in rows), 'demozoo_authors': set()}

    production_ids = tuple(productions.keys())
    if production_ids:
        # from that list of productions, the janeway IDs of all releasers listed as authors
        cursor.execute("""
            SELECT productions_production_author_nicks.production_id, demoscene_releaserexternallink.parameter
            FROM productions_production_author_nicks
            INNER JOIN demoscene_nick ON (
                productions_production_author_nicks.nick_id = demoscene_nick.id
            )
            INNER JOIN demoscene_releaserexternallink ON (
                demoscene_nick.releaser_id = demoscene_releaserexternallink.releaser_id
                AND demoscene_releaserexternallink.link_class = 'KestraBitworldAuthor'
            )
            WHERE productions_production_author_nicks.production_id IN %s
        """, [production_ids])
        for production_id, rows in itertools.groupby(cursor.fetchall(), lambda row: row[0]):
            productions[production_id]['demozoo_authors'].update(int(row[1]) for row in rows)

        # ditto for author affiliations
        cursor.execute("""
            SELECT productions_production_author_affiliation_nicks.production_id, demoscene_releaserexternallink.parameter
            FROM productions_production_author_affiliation_nicks
            INNER JOIN demoscene_nick ON (
                productions_production_author_affiliation_nicks.nick_id = demoscene_nick.id
            )
            INNER JOIN demoscene_releaserexternallink ON (
                demoscene_nick.releaser_id = demoscene_releaserexternallink.releaser_id
                AND demoscene_releaserexternallink.link_class = 'KestraBitworldAuthor'
            )
            WHERE productions_production_author_affiliation_nicks.production_id IN %s
        """, [production_ids])
        for production_id, rows in itertools.groupby(cursor.fetchall(), lambda row: row[0]):
            productions[production_id]['demozoo_authors'].update(int(row[1]) for row in rows)

    # IDs of prods where janeway_authors contains IDs not in demozoo_authors
    prod_ids_with_missing_authors = []
    all_missing_authors = set()

    for prod_id, authors in productions.items():
        missing_authors = authors['janeway_authors'] - authors['demozoo_authors']
        if missing_authors:
            all_missing_authors.update(missing_authors)
            prod_ids_with_missing_authors.append(prod_id)

    return prod_ids_with_missing_authors, all_missing_authors
