import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from posts.models import Post, Group, Comment


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='kirill')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group_1 = Group.objects.create(
            title='test-title-1',
            slug='test-slug-1',
            description='test-description-1',
        )
        cls.group_2 = Group.objects.create(
            title='test-title-2',
            slug='test-slug-2',
            description='test-description-2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test-text',
            group=cls.group_1
        )

    def setUp(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'test-text',
            'group': self.group_1.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        latest_post = Post.objects.latest('pk')

        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            )
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(
            latest_post.author,
            self.user
        )
        self.assertEqual(
            latest_post.text,
            form_data['text']
        )
        self.assertEqual(
            latest_post.group.id,
            self.group_1.id
        )
        self.assertFalse(latest_post.image is None)

    def test_edit_post(self):
        '''Редактирование записи в Post.'''
        post_count = Post.objects.count()
        form_data = {
            'text': 'test-text-1',
            'group': self.group_2.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
        )
        latest_post = Post.objects.latest('pk')

        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            )
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(
            latest_post.author,
            self.user
        )
        self.assertEqual(
            latest_post.text,
            form_data['text']
        )
        self.assertEqual(
            latest_post.group.id,
            self.group_2.id
        )
        self.assertFalse(latest_post.image is None)

    def test_add_comment(self):
        '''Валидная форма создает запись в Comment.'''
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'test-comment'
        }
        response_authorized_client = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        latest_comment = Comment.objects.latest('pk')

        self.assertRedirects(
            response_authorized_client,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            )
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(
            latest_comment.author,
            self.user
        )
        self.assertEqual(
            latest_comment.text,
            form_data['text']
        )
        self.assertEqual(
            latest_comment.post,
            self.post
        )

    def test_guest_client_can_not_add_comment(self):
        '''Неавторизованный пользователь
           не может добавить комментарий'''
        guest_client = Client()
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'test-comment'
        }
        guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertNotEqual(Comment.objects.count(), comment_count + 1)
