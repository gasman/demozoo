from django.contrib.auth.models import User
from django.test import TestCase

from forums.models import Post, Topic


class TestIndex(TestCase):
    fixtures = ['tests/forum.json']

    def test_get(self):
        response = self.client.get('/forums/')
        self.assertEqual(response.status_code, 200)


class TestNewTopic(TestCase):
    fixtures = ['tests/forum.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_get(self):
        response = self.client.get('/forums/new/')
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post('/forums/new/', {
            'title': "I'm off to the shops",
            'body': "does anyone need anything"
        })
        topic = Topic.objects.get(title="I'm off to the shops")
        self.assertRedirects(response, '/forums/%d/' % topic.id)

    def test_post_overlong(self):
        response = self.client.post('/forums/new/', {
            'title': "Amig" + ('a' * 1000),
            'body': "I am very original."
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value has at most 255 characters")


class TestShowTopic(TestCase):
    fixtures = ['tests/forum.json']

    def test_get(self):
        response = self.client.get('/forums/1/')
        self.assertEqual(response.status_code, 200)

    def test_get_specific_post(self):
        response = self.client.get('/forums/post/1/')
        self.assertEqual(response.status_code, 200)


class TestTopicReply(TestCase):
    fixtures = ['tests/forum.json']

    def setUp(self):
        User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')

    def test_get(self):
        response = self.client.get('/forums/1/reply/')
        self.assertEqual(response.status_code, 200)

    def test_empty_post(self):
        response = self.client.post('/forums/1/reply/', {
            'body': "",
        })
        self.assertEqual(Topic.objects.get(id=1).reply_count, 0)
        self.assertEqual(Post.objects.filter(body="").count(), 0)
        self.assertRedirects(response, '/forums/1/')

    def test_post(self):
        response = self.client.post('/forums/1/reply/', {
            'body': "it's only a bit broken",
        })
        self.assertEqual(Topic.objects.get(id=1).reply_count, 1)
        post = Post.objects.get(body="it's only a bit broken")
        self.assertRedirects(response, '/forums/1/#post-%d' % post.id)


class TestDeletePost(TestCase):
    fixtures = ['tests/forum.json']

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='testuser@example.com', password='12345', is_staff=True
        )
        self.client.login(username='testuser', password='12345')
        self.post = Post.objects.create(topic_id=1, user_id=1, body="it's only a bit broken")

    def test_get(self):
        response = self.client.get('/forums/post/%d/delete/' % self.post.id)
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.client.post(
            '/forums/post/%d/delete/' % self.post.id,
            {'yes': 'yes'},
        )
        self.assertRedirects(response, '/forums/1/')
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())

    def test_delete_requires_admin_privileges(self):
        self.user.is_staff = False
        self.user.save()

        response = self.client.post(
            '/forums/post/%d/delete/' % self.post.id,
            {'yes': 'yes'},
        )
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())
        self.assertRedirects(response, '/forums/post/%d/' % self.post.id)
