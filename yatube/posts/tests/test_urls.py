from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Post, Group


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='kirill')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='test-group',
            slug='test-slug',
            description='test-description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test-post',
            group=cls.group,
        )

    def test_page_availability(self):
        user_not_author = User.objects.create_user(username='daniil')
        authorized_client_not_author = Client()
        authorized_client_not_author.force_login(user_not_author)
        guest_client = Client()

        list_of_pages_with_settings = [
            ('/', guest_client, 200),
            ('/', authorized_client_not_author, 200),
            ('/', self.authorized_client, 200),
            (f'/group/{self.post.group.slug}/', guest_client, 200),
            (f'/group/{self.post.group.slug}/',
             authorized_client_not_author,
             200),
            (f'/group/{self.post.group.slug}/', self.authorized_client, 200),
            (f'/profile/{self.post.author.username}/', guest_client, 200),
            (f'/profile/{self.post.author.username}/',
             authorized_client_not_author,
             200),
            (f'/profile/{self.post.author.username}/',
             self.authorized_client,
             200),
            (f'/posts/{self.post.pk}/', guest_client, 200),
            (f'/posts/{self.post.pk}/', authorized_client_not_author, 200),
            (f'/posts/{self.post.pk}/', self.authorized_client, 200),
            ('/create/', guest_client, 302),
            ('/create/', authorized_client_not_author, 200),
            ('/create/', self.authorized_client, 200),
            (f'/posts/{self.post.pk}/edit/', guest_client, 302),
            (f'/posts/{self.post.pk}/edit/',
             authorized_client_not_author,
             302),
            (f'/posts/{self.post.pk}/edit/', self.authorized_client, 200),
            (f'/posts/{self.post.pk}/comment/', guest_client, 302),
        ]
        for address, client, status in list_of_pages_with_settings:
            with self.subTest(address=address):
                response = client.get(address)
                self.assertEqual(response.status_code, status)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.post.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.post.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_incorrect_template(self):
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)
