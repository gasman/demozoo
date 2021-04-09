from io import BytesIO

from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from bbs.models import BBS, Affiliation, Operator
from demoscene.models import Edit, Releaser
from demoscene.tests.utils import MediaTestMixin
from productions.models import Production


class TestIndex(TestCase):
    fixtures = ['tests/gasman.json']

    def test_get(self):
        response = self.client.get('/bbs/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "StarPort")


class TestShow(TestCase):
    fixtures = ['tests/gasman.json']

    def test_get(self):
        bbs = BBS.objects.get(name='StarPort')
        response = self.client.get('/bbs/%d/' % bbs.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "StarPort")


class TestCreate(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_get(self):
        response = self.client.get('/bbs/new/')
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/new/', {
            'name': 'Eclipse',
            'location': '',
        })
        self.assertRedirects(response, '/bbs/%d/' % BBS.objects.get(name='Eclipse').id)


class TestEdit(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')

    def test_get(self):
        response = self.client.get('/bbs/%d/edit/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/edit/' % self.bbs.id, {
            'name': 'StarWhisky',
            'location': 'Oxford',
        })
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)


class TestEditNotes(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_superuser(username='testsuperuser', email='testsuperuser@example.com', password='12345')
        self.client.login(username='testsuperuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')

    def test_non_superuser(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        response = self.client.get('/bbs/%d/edit_notes/' % self.bbs.id)
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)

    def test_get(self):
        response = self.client.get('/bbs/%d/edit_notes/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/edit_notes/' % self.bbs.id, {
            'notes': 'purple motion ad lib music etc',
        })
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)


class TestDelete(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_superuser(username='testsuperuser', email='testsuperuser@example.com', password='12345')
        self.client.login(username='testsuperuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')

    def test_non_superuser(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        response = self.client.get('/bbs/%d/delete/' % self.bbs.id)
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)

    def test_get(self):
        response = self.client.get('/bbs/%d/delete/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/delete/' % self.bbs.id, {
            'yes': 'yes'
        })
        self.assertRedirects(response, '/bbs/')
        self.assertFalse(BBS.objects.filter(name='StarPort').exists())

    def test_cancel(self):
        response = self.client.post('/bbs/%d/delete/' % self.bbs.id, {
            'no': 'no'
        })
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)
        self.assertTrue(BBS.objects.filter(name='StarPort').exists())


class TestEditBBStros(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_superuser(username='testsuperuser', email='testsuperuser@example.com', password='12345')
        self.client.login(username='testsuperuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.pondlife = Production.objects.get(title='Pondlife')

    def test_get(self):
        response = self.client.get('/bbs/%d/edit_bbstros/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/edit_bbstros/' % self.bbs.id, {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 0,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000,
            'form-0-production_id': self.pondlife.id,
            'form-0-production_title': 'Pondlife',
            'form-0-production_byline_search': '',
        })
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)
        self.assertEqual(self.bbs.bbstros.count(), 1)

        edit = Edit.for_model(self.bbs, True).first()
        self.assertEqual("Set BBStros to Pondlife", edit.description)

        # no change => no edit log entry added
        edit_count = Edit.for_model(self.bbs, True).count()
        response = self.client.post('/bbs/%d/edit_bbstros/' % self.bbs.id, {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000,
            'form-0-production_id': self.pondlife.id,
            'form-0-production_title': 'Pondlife',
            'form-0-production_byline_search': '',
        })
        self.assertRedirects(response, '/bbs/%d/' % self.bbs.id)
        self.assertEqual(edit_count, Edit.for_model(self.bbs, True).count())


class TestShowHistory(TestCase):
    fixtures = ['tests/gasman.json']

    def test_get(self):
        bbs = BBS.objects.get(name='StarPort')
        response = self.client.get('/bbs/%d/history/' % bbs.id)
        self.assertEqual(response.status_code, 200)


class TestAddOperator(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.gasman = Releaser.objects.get(name='Gasman')

    def test_get(self):
        response = self.client.get('/bbs/%d/add_operator/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/add_operator/' % self.bbs.id, {
            'releaser_nick_search': 'gasman',
            'releaser_nick_match_id': self.gasman.primary_nick.id,
            'releaser_nick_match_name': 'gasman',
            'role': 'co-sysop'
        })
        self.assertRedirects(response, '/bbs/%d/?editing=staff' % self.bbs.id)
        self.assertEqual(1, Operator.objects.filter(releaser=self.gasman, bbs=self.bbs).count())


class TestEditOperator(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.abyss = Releaser.objects.get(name='Abyss')
        self.yerzmyey = Releaser.objects.get(name='Yerzmyey')
        self.operator = Operator.objects.get(bbs=self.bbs, releaser=self.abyss)

    def test_get(self):
        response = self.client.get('/bbs/%d/edit_operator/%d/' % (self.bbs.id, self.operator.id))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/edit_operator/%d/' % (self.bbs.id, self.operator.id), {
            'releaser_nick_search': 'yerzmyey',
            'releaser_nick_match_id': self.yerzmyey.primary_nick.id,
            'releaser_nick_match_name': 'yerzmyey',
            'role': 'co-sysop'
        })
        self.assertRedirects(response, '/bbs/%d/?editing=staff' % self.bbs.id)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.role, "co-sysop")
        self.assertEqual(self.operator.releaser, self.yerzmyey)


class TestRemoveOperator(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.abyss = Releaser.objects.get(name='Abyss')
        self.operator = Operator.objects.get(bbs=self.bbs, releaser=self.abyss)

    def test_get(self):
        response = self.client.get('/bbs/%d/remove_operator/%d/' % (self.bbs.id, self.operator.id))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/remove_operator/%d/' % (self.bbs.id, self.operator.id), {
            'yes': 'yes',
        })
        self.assertRedirects(response, '/bbs/%d/?editing=staff' % self.bbs.id)
        self.assertEqual(0, Operator.objects.filter(releaser=self.abyss, bbs=self.bbs).count())


class TestAddAffiliation(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.hprg = Releaser.objects.get(name='Hooy-Program')

    def test_get(self):
        response = self.client.get('/bbs/%d/add_affiliation/' % self.bbs.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/add_affiliation/' % self.bbs.id, {
            'group_nick_search': 'hooy-program',
            'group_nick_match_id': self.hprg.primary_nick.id,
            'group_nick_match_name': 'hooy-program',
            'role': '020-hq'
        })
        self.assertRedirects(response, '/bbs/%d/?editing=affiliations' % self.bbs.id)
        self.assertEqual(1, Affiliation.objects.filter(group=self.hprg, bbs=self.bbs).count())

    def test_post_blank_role(self):
        response = self.client.post('/bbs/%d/add_affiliation/' % self.bbs.id, {
            'group_nick_search': 'hooy-program',
            'group_nick_match_id': self.hprg.primary_nick.id,
            'group_nick_match_name': 'hooy-program',
            'role': ''
        })
        self.assertRedirects(response, '/bbs/%d/?editing=affiliations' % self.bbs.id)
        self.assertEqual(1, Affiliation.objects.filter(group=self.hprg, bbs=self.bbs).count())


class TestEditAffiliation(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.fc = Releaser.objects.get(name='Future Crew')
        self.hprg = Releaser.objects.get(name='Hooy-Program')
        self.affiliation = Affiliation.objects.get(bbs=self.bbs, group=self.fc)

    def test_get(self):
        response = self.client.get('/bbs/%d/edit_affiliation/%d/' % (self.bbs.id, self.affiliation.id))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/edit_affiliation/%d/' % (self.bbs.id, self.affiliation.id), {
            'group_nick_search': 'hooy-program',
            'group_nick_match_id': self.hprg.primary_nick.id,
            'group_nick_match_name': 'hooy-program',
            'role': '020-hq'
        })
        self.assertRedirects(response, '/bbs/%d/?editing=affiliations' % self.bbs.id)
        self.affiliation.refresh_from_db()
        self.assertEqual(self.affiliation.role, "020-hq")
        self.assertEqual(self.affiliation.group, self.hprg)


class TestRemoveAffiliation(TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.bbs = BBS.objects.get(name='StarPort')
        self.fc = Releaser.objects.get(name='Future Crew')
        self.affiliation = Affiliation.objects.get(bbs=self.bbs, group=self.fc)

    def test_get(self):
        response = self.client.get('/bbs/%d/remove_affiliation/%d/' % (self.bbs.id, self.affiliation.id))
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/bbs/%d/remove_affiliation/%d/' % (self.bbs.id, self.affiliation.id), {
            'yes': 'yes',
        })
        self.assertRedirects(response, '/bbs/%d/?editing=affiliations' % self.bbs.id)
        self.assertEqual(0, Affiliation.objects.filter(group=self.fc, bbs=self.bbs).count())


class TestEditTextAds(MediaTestMixin, TestCase):
    fixtures = ['tests/gasman.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        User.objects.create_superuser(username='testsuperuser', email='testsuperuser@example.com', password='12345')
        self.starport = BBS.objects.get(name='StarPort')

        self.info1 = self.starport.text_ads.create(
            file=File(name="starport1.txt", file=BytesIO(b"First text ad for StarPort")),
            filename="starport1.txt", filesize=100, sha1="1234123412341234"
        )
        self.info2 = self.starport.text_ads.create(
            file=File(name="starport2.txt", file=BytesIO(b"Second text ad for StarPort")),
            filename="starport2.txt", filesize=100, sha1="1234123412341235"
        )

    def test_get(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get('/bbs/%d/edit_text_ads/' % self.starport.id)
        self.assertEqual(response.status_code, 200)

    def test_add_one(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post('/bbs/%d/edit_text_ads/' % self.starport.id, {
            'text_ad': SimpleUploadedFile('starport3.txt', b"Third text ad", content_type="text/plain")
        })
        self.assertRedirects(response, '/bbs/%d/' % self.starport.id)
        self.assertEqual(3, self.starport.text_ads.count())

    def test_add_multiple(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post('/bbs/%d/edit_text_ads/' % self.starport.id, {
            'text_ad': [
                SimpleUploadedFile('starport3.txt', b"Third text ad", content_type="text/plain"),
                SimpleUploadedFile('starport4.txt', b"Fourth text ad", content_type="text/plain"),
            ]
        })
        self.assertRedirects(response, '/bbs/%d/' % self.starport.id)
        self.assertEqual(4, self.starport.text_ads.count())

    def test_delete_one(self):
        self.client.login(username='testsuperuser', password='12345')
        response = self.client.post('/bbs/%d/edit_text_ads/' % self.starport.id, {
            'text_ads-TOTAL_FORMS': 2,
            'text_ads-INITIAL_FORMS': 2,
            'text_ads-MIN_NUM_FORMS': 0,
            'text_ads-MAX_NUM_FORMS': 1000,
            'text_ads-0-DELETE': 'text_ads-0-DELETE',
            'text_ads-0-id': self.info1.id,
            'text_ads-0-bbs': self.starport.id,
            'text_ads-1-id': self.info2.id,
            'text_ads-1-bbs': self.starport.id,
        })
        self.assertRedirects(response, '/bbs/%d/' % self.starport.id)
        self.assertEqual(1, self.starport.text_ads.count())

    def test_delete_multiple(self):
        self.client.login(username='testsuperuser', password='12345')
        response = self.client.post('/bbs/%d/edit_text_ads/' % self.starport.id, {
            'text_ads-TOTAL_FORMS': 2,
            'text_ads-INITIAL_FORMS': 2,
            'text_ads-MIN_NUM_FORMS': 0,
            'text_ads-MAX_NUM_FORMS': 1000,
            'text_ads-0-DELETE': 'text_ads-0-DELETE',
            'text_ads-0-id': self.info1.id,
            'text_ads-0-bbs': self.starport.id,
            'text_ads-1-DELETE': 'text_ads-1-DELETE',
            'text_ads-1-id': self.info2.id,
            'text_ads-1-bbs': self.starport.id,
        })
        self.assertRedirects(response, '/bbs/%d/' % self.starport.id)
        self.assertEqual(0, self.starport.text_ads.count())
