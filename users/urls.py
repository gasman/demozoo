from django.conf.urls import url

from users.views import index, show


urlpatterns = [
    url(r'^$', index, {}, 'users_index'),
    url(r'^(\d+)/$', show, {}, 'user'),
]
