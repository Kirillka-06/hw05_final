import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.urls import reverse
from django import forms
from django.conf import settings

from posts.models import Post, Group, Follow

User = get_user_model()
NUMBER_OF_POST_FOR_TEST = 3
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='kirill')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test-post',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_views_uses_correct_template(self):
        """URL uses correct template."""
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.post.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        """Шаблоны index, group_list и profile
           сформирован с правильным контекстом."""
        list_of_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.post.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for page in list_of_pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                context = response.context['page_obj'][0]
                self.assertEqual(context.author, self.user)
                self.assertEqual(context.text, self.post.text)
                self.assertEqual(context.group, self.post.group)
                self.assertEqual(context.pk, self.post.pk)
                self.assertEqual(context.image, self.post.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        context = response.context['page_obj']
        self.assertEqual(context.author, self.user)
        self.assertEqual(context.text, self.post.text)
        self.assertEqual(context.pk, self.post.pk)
        self.assertEqual(context.group, self.group)
        self.assertEqual(context.image, self.post.image)

    def test_post_edit_show_correct_context(self):
        """Шаблон create_post для редактирования
           сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_index_cache_show_correct_context(self):
        """Кэш шаблона create_post сформирован с правильным контекстом."""
        post = Post.objects.create(
            author=self.user,
            text='test-text',
            group=self.group
        )
        response_1 = self.authorized_client.get(
            reverse('posts:index')
        )
        post.delete()
        response_2 = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response_1.content, response_3.content)

    def test_user_can_follow_unfollow(self):
        '''Авторизованный пользователь может подписываться
           на других пользователей и удалять их из подписок.'''
        new_user = User.objects.create(username='daniil')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)

        follow_count = Follow.objects.count()
        new_authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post.author})
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)

        new_authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.post.author})
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_section_with_selected_authors(self):
        '''Новая запись пользователя появляется в ленте тех,
           кто на него подписан и не появляется в ленте тех,
           кто не подписан.'''
        user_1 = User.objects.create(username='daniil')
        authorized_client_1 = Client()
        authorized_client_1.force_login(user_1)
        user_2 = User.objects.create(username='anton')
        authorized_client_2 = Client()
        authorized_client_2.force_login(user_2)

        authorized_client_1.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post.author})
        )
        response_1 = authorized_client_1.get(
            reverse('posts:follow_index')
        )
        context_1 = response_1.context['page_obj'][0]
        self.assertEqual(context_1.author, self.user)
        self.assertEqual(context_1.text, self.post.text)
        self.assertEqual(context_1.group, self.post.group)
        self.assertEqual(context_1.pk, self.post.pk)
        self.assertEqual(context_1.image, self.post.image)

        response_2 = authorized_client_2.get(
            reverse('posts:follow_index')
        )
        context_2_count = len(response_2.context['page_obj'])
        self.assertEqual(context_2_count, 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='kirill')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-description',
        )
        for _ in range(settings.NUMBER_OF_POST_PER_PAGE
                       + NUMBER_OF_POST_FOR_TEST):
            cls.post = Post.objects.create(
                author=cls.user,
                text='test-post',
                group=cls.group,
            )

    """Проверка пагинатора шаблона index.html"""
    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']),
                         settings.NUMBER_OF_POST_PER_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         NUMBER_OF_POST_FOR_TEST)

    """Проверка пагинатора шаблона group_list.html"""
    def test_first_page_contains_ten_records(self):
        response = self.client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug})
        )
        self.assertEqual(len(response.context['page_obj']),
                         settings.NUMBER_OF_POST_PER_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']),
                         NUMBER_OF_POST_FOR_TEST)

    """Проверка пагинатора шаблона profile.html"""
    def test_first_page_contains_ten_records(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(len(response.context['page_obj']),
                         settings.NUMBER_OF_POST_PER_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user}) + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']),
                         NUMBER_OF_POST_FOR_TEST)
