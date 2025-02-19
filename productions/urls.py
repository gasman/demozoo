from django.conf.urls import patterns

urlpatterns = patterns('productions.views',
	(r'^productions/$', 'productions.index', {}, 'productions'),
	(r'^productions/(\d+)/$', 'productions.show', {}, 'production'),
	(r'^productions/(\d+)/history/$', 'productions.history', {}, 'production_history'),
	(r'^productions/(\d+)/carousel/$', 'productions.carousel', {}, 'production_carousel'),

	(r'^music/$', 'music.index', {}, 'musics'),
	(r'^music/(\d+)/$', 'music.show', {}, 'music'),
	(r'^music/(\d+)/edit_core_details/$', 'productions.edit_core_details', {}, 'music_edit_core_details'),
	(r'^music/new/$', 'music.create', {}, 'new_music'),
	(r'^music/(\d+)/history/$', 'music.history', {}, 'music_history'),

	(r'^graphics/$', 'graphics.index', {}, 'graphics'),
	(r'^graphics/(\d+)/$', 'graphics.show', {}, 'graphic'),
	(r'^graphics/(\d+)/edit_core_details/$', 'productions.edit_core_details', {}, 'graphics_edit_core_details'),
	(r'^graphics/new/$', 'graphics.create', {}, 'new_graphics'),
	(r'^graphics/(\d+)/history/$', 'graphics.history', {}, 'graphics_history'),

	(r'^productions/new/$', 'productions.create', {}, 'new_production'),
	(r'^productions/autocomplete/$', 'productions.autocomplete', {}),
	(r'^productions/autocomplete_tags/$', 'productions.autocomplete_tags', {}),
	(r'^productions/tagged/(.+)/$', 'productions.tagged', {}, 'productions_tagged'),
	(r'^productions/(\d+)/edit_core_details/$', 'productions.edit_core_details', {}, 'production_edit_core_details'),
	(r'^productions/(\d+)/add_credit/$', 'productions.add_credit', {}, 'production_add_credit'),
	(r'^productions/(\d+)/edit_credit/(\d+)/$', 'productions.edit_credit', {}, 'production_edit_credit'),
	(r'^productions/(\d+)/delete_credit/(\d+)/$', 'productions.delete_credit', {}, 'production_delete_credit'),
	(r'^productions/(\d+)/edit_notes/$', 'productions.edit_notes', {}, 'production_edit_notes'),
	(r'^productions/(\d+)/edit_external_links/$', 'productions.edit_external_links', {}, 'production_edit_external_links'),
	(r'^productions/(\d+)/edit_download_links/$', 'productions.edit_download_links', {}, 'production_edit_download_links'),
	(r'^productions/(\d+)/add_screenshot/$', 'productions.add_screenshot', {}, 'production_add_screenshot'),
	(r'^productions/(\d+)/add_artwork/$', 'productions.add_screenshot', {'is_artwork_view': True}, 'production_add_artwork'),
	(r'^productions/(\d+)/screenshots/$', 'productions.screenshots', {}, 'production_screenshots'),
	(r'^productions/(\d+)/artwork/$', 'productions.artwork', {}, 'production_artwork'),
	(r'^productions/(\d+)/screenshots/edit/$', 'productions.edit_screenshots', {}, 'production_edit_screenshots'),
	(r'^productions/(\d+)/artwork/edit/$', 'productions.edit_artwork', {}, 'production_edit_artwork'),
	(r'^productions/(\d+)/delete_screenshot/(\d+)/$', 'productions.delete_screenshot', {}, 'production_delete_screenshot'),
	(r'^productions/(\d+)/delete_artwork/(\d+)/$', 'productions.delete_screenshot', {'is_artwork_view': True}, 'production_delete_artwork'),
	(r'^productions/(\d+)/edit_soundtracks/$', 'productions.edit_soundtracks', {}, 'production_edit_soundtracks'),
	(r'^productions/(\d+)/edit_pack_contents/$', 'productions.edit_pack_contents', {}, 'production_edit_pack_contents'),
	(r'^productions/(\d+)/edit_tags/$', 'productions.edit_tags', {}, 'production_edit_tags'),
	(r'^productions/(\d+)/add_tag/$', 'productions.add_tag', {}, 'production_add_tag'),
	(r'^productions/(\d+)/remove_tag/$', 'productions.remove_tag', {}, 'production_remove_tag'),
	(r'^productions/(\d+)/delete/$', 'productions.delete', {}, 'delete_production'),
	(r'^productions/(\d+)/add_blurb/$', 'productions.add_blurb', {}, 'production_add_blurb'),
	(r'^productions/(\d+)/edit_blurb/(\d+)/$', 'productions.edit_blurb', {}, 'production_edit_blurb'),
	(r'^productions/(\d+)/delete_blurb/(\d+)/$', 'productions.delete_blurb', {}, 'production_delete_blurb'),
)
