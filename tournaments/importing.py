from datetime import datetime
import re

from demoscene.models import Nick, Releaser
from parties.models import Party
from tournaments.models import Entry, Tournament


PARTY_SERIES_ALIASES = {
    'assembly summer': 'assembly',
    'assembly autumn': 'assembly',
    'tokyo demo fest': 'tokyodemofest',
    'chaos constructions winter': 'chaos constructions',
    'deadline': 'deadline (.de)',
    'omzg': 'molvania zscene gathering',
    'hogmanay party': 'hogmanay.party',
}

ROLES_LOOKUP = {
    'commentator': 'commentary',
    'commentators': 'commentary',
    'dj set': 'dj_set',
    'live music': 'live_music',
    'live set': 'live_music',
}


def find_party_from_tournament_data(tournament_data):
    try:
        party_id = int(tournament_data.get('demozoo_party_id') or '')
    except ValueError:
        return None

    return Party.objects.get(id=party_id)


def find_nick_from_handle_data(handle_data):
    if handle_data['demozoo_id'] is None:
        return (None, handle_data['name'])

    try:
        nick = Nick.objects.get(
            releaser_id=handle_data['demozoo_id'],
            variants__name__iexact = handle_data['name']
        )
    except Nick.DoesNotExist:
        print(
            "\tCannot find nick '%s' for releaser %d (%s)" % (
                handle_data['name'], handle_data['demozoo_id'],
                Releaser.objects.get(id=handle_data['demozoo_id']).name
            )
        )
        return (None, handle_data['name'])
    except Nick.MultipleObjectsReturned:
        raise Exception(
            "Multiple nicks found for %s (%s)" % (
                handle_data['name'], Releaser.objects.get(id=handle_data['demozoo_id']).name
            )
        )

    return (nick.id, '')


def import_tournament(filename, tournament_data, media_path):
    try:
        tournament = Tournament.objects.get(source_file_name=filename)
        created = False
        party = tournament.party
    except Tournament.DoesNotExist:
        party = find_party_from_tournament_data(tournament_data)
        if not party:
            print(
                "\tNo match for party: %s %s" % (
                    tournament_data['title'], tournament_data['started']
                )
            )
            return

        tournament, created = Tournament.objects.get_or_create(
            party=party, name=tournament_data['type'],
            defaults={'source_file_name': filename}
        )

        if not created:
            print(
                "\tMismatched source filename! Previously %s, now %s" % (
                    tournament.source_file_name, filename
                )
            )
            return

    phases_data = tournament_data['phases']

    if created:
        print("\tCreated tournament: %s" % tournament)
        create_phases = True
    else:
        # print("\tFound tournament: %s" % tournament)
        expected_party = find_party_from_tournament_data(tournament_data)
        if tournament.party != expected_party:
            print(
                "\tParty mismatch! Found %s, but data looks like %s" % (
                    tournament.party, expected_party
                )
            )

        if tournament.name != tournament_data['type']:
            print(
                "\tChanged name from %s to %s" % (
                    tournament.name, tournament_data['type']
                )
            )
            tournament.name = tournament_data['type']
            tournament.save()

        # if there are any discrepancies in phase counts or titles,
        # delete and reimport them
        phases = list(tournament.phases.all())
        if len(phases) != len(phases_data):
            create_phases = True
        elif any(
            phase.name != (phases_data[i]['title'] or '')
            or phase.position != i
            for i, phase in enumerate(phases)
        ):
            create_phases = True
        else:
            create_phases = False

        if create_phases:
            print("\tPhases don't match - recreating")
            tournament.phases.all().delete()

    if create_phases:
        for position, phase_data in enumerate(phases_data):
            phase = tournament.phases.create(
                name=phase_data['title'] or '', position=position
            )

            load_phase_data(phase, phase_data, media_path)

    else:
        # phases for this tournament are already defined and confirmed to match the
        # names in the file, and have consecutive 0-based positions
        for phase in phases:
            load_phase_data(phase, phases_data[phase.position], media_path)

    # Add organiser credit to party if there isn't one already
    for staff_member_data in tournament_data['staffs']:
        if staff_member_data['job'] != 'Organizers':
            continue

        releaser_id = staff_member_data['handle']['demozoo_id']
        if releaser_id is None:
            continue

        # check that the given demozoo_id is consistent with the name
        nick_id, name = find_nick_from_handle_data(staff_member_data['handle'])
        if nick_id is None:
            continue

        if party.organisers.filter(releaser_id=releaser_id).exists():
            continue

        print("\tAdding party organiser: %s" % staff_member_data['handle']['name'])
        party.organisers.create(releaser_id=releaser_id, role=tournament_data['type'])


def load_phase_data(phase, phase_data, media_path):
    entries = list(phase.entries.all())
    entries_data = phase_data['entries']

    # if length of entries list doesn't match, or positions are inconsistent,
    # recreate
    create_entries = (
        len(entries) != len(entries_data)
        or any(entry.position != i for i, entry in enumerate(entries))
    )

    if create_entries:
        phase.entries.all().delete()
        for position, entry_data in enumerate(entries_data):
            nick_id, name = find_nick_from_handle_data(entry_data['handle'])

            entry = Entry(
                phase=phase,
                position=position,
                nick_id=nick_id,
                name=name,
                ranking=entry_data['rank'] or '',
                score=entry_data.get('points') or '',
            )
            screenshot_filename = entry_data.get('preview_image')
            if screenshot_filename:
                screenshot_path = str(media_path / screenshot_filename)
                entry.set_screenshot(screenshot_path)
            entry.save()

    else:
        for i, entry_data in enumerate(entries_data):
            entry = entries[i]
            has_changed = False

            nick_id, name = find_nick_from_handle_data(entry_data['handle'])
            if nick_id != entry.nick_id or name != entry.name:
                entry.nick_id = nick_id
                entry.name = name
                has_changed = True

            rank = '' if entry_data['rank'] is None else str(entry_data['rank'])
            if rank != entry.ranking:
                entry.ranking = rank
                has_changed = True

            score = '' if entry_data.get('points') is None else str(entry_data['points'])
            if score != entry.score:
                entry.score = score
                has_changed = True

            screenshot_filename = entry_data.get('preview_image')
            if screenshot_filename:
                screenshot_path = str(media_path / screenshot_filename)
                if entry.set_screenshot(screenshot_path):
                    has_changed = True

            if has_changed:
                print("\tupdating entry %s" % entry)
                entry.save()

    staff_members = set()
    for staff_member_data in phase_data['staffs']:
        nick_id, name = find_nick_from_handle_data(staff_member_data['handle'])
        role = ROLES_LOOKUP[staff_member_data['job'].lower()]
        staff_members.add((nick_id, name, role))

    current_staff_members = set([
        (staff_member.nick_id, staff_member.name, staff_member.role)
        for staff_member in phase.staff.all()
    ])
    if staff_members != current_staff_members:
        if current_staff_members:
            print("\tupdating staff")
            phase.staff.all().delete()

        for nick_id, name, role in staff_members:
            phase.staff.create(nick_id=nick_id, name=name, role=role)
