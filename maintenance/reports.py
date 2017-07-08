import redis

from django.conf import settings

from productions.models import Production
from maintenance.models import Exclusion


def write_set(pipe, key, values):
	# Write a set to the given redis key, with expiry of 10 minutes
	pipe.delete(key)
	if values:
		pipe.sadd(key, *values)
		pipe.expire(key, 600)


def productions_without_screenshots(limit=100, platform_ids=None, production_type_ids=None):
	# compile a list of all the redis keys we're going to use, so that we can
	# construct a transaction that watches them
	used_keys = ['demozoo:productions:without_screenshots']

	filtered_result_key = 'demozoo:productions:without_screenshots'
	if platform_ids:
		id_list = ','.join([str(id) for id in platform_ids])
		platforms_filter_key = 'demozoo:productions:by_platforms:%s' % id_list
		used_keys.append(platforms_filter_key)
		filtered_result_key += ':by_platforms:%s' % id_list

	if production_type_ids:
		id_list = ','.join([str(id) for id in production_type_ids])
		prod_types_filter_key = 'demozoo:productions:by_types:%s' % id_list
		used_keys.append(prod_types_filter_key)
		filtered_result_key += ':by_types:%s' % id_list

	if platform_ids or production_type_ids:
		used_keys.append(filtered_result_key)

	def _transaction(pipe):
		must_update_master_screenshot_list = not pipe.exists('demozoo:productions:without_screenshots')
		must_update_platforms_filter = platform_ids and not pipe.exists(platforms_filter_key)
		must_update_prod_types_filter = production_type_ids and not pipe.exists(prod_types_filter_key)

		filter_keys = []
		if platform_ids:
			filter_keys.append(platforms_filter_key)
		if production_type_ids:
			filter_keys.append(prod_types_filter_key)

		pipe.multi()

		if must_update_master_screenshot_list:
			excluded_ids = Exclusion.objects.filter(report_name='prods_without_screenshots').values_list('record_id', flat=True)

			production_ids = (
				Production.objects
				.filter(default_screenshot__isnull=True)
				.filter(links__is_download_link=True)
				.exclude(supertype='music')
				.exclude(id__in=excluded_ids)
				.values_list('id', flat=True)
			)

			write_set(pipe, 'demozoo:productions:without_screenshots', production_ids)

		if must_update_platforms_filter:
			production_ids = (
				Production.objects
				.filter(platforms__id__in=platform_ids)
				.values_list('id', flat=True)
			)
			write_set(pipe, platforms_filter_key, production_ids)

		if must_update_prod_types_filter:
			production_ids = (
				Production.objects
				.filter(types__id__in=production_type_ids)
				.values_list('id', flat=True)
			)
			write_set(pipe, prod_types_filter_key, production_ids)

		if filter_keys:
			# create a resultset in filtered_result_key consisting of the intersection
			# of the master productions:without_screenshots and the filters
			pipe.sinterstore(filtered_result_key, 'demozoo:productions:without_screenshots', *filter_keys)
			pipe.expire(filtered_result_key, 600)

			# get randomised list of production IDs
			pipe.srandmember(filtered_result_key, number=limit)
			# get total count of prods after filtering
			pipe.scard(filtered_result_key)

		else:
			# use productions:without_screenshots set directly

			# get randomised list of production IDs
			pipe.srandmember('demozoo:productions:without_screenshots', number=limit)
			# get total count of prods
			pipe.scard('demozoo:productions:without_screenshots')

	r = redis.StrictRedis.from_url(settings.REDIS_URL)
	production_ids, count = r.transaction(_transaction, *used_keys)[-2:]

	productions = (
		Production.objects.filter(id__in=production_ids)
		.prefetch_related('author_nicks__releaser', 'author_affiliation_nicks__releaser', 'platforms', 'types')
		.defer('notes')
	)

	return (productions, count)
