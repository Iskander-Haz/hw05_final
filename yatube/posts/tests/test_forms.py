import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import CommentForm, PostForm
from posts.models import Comment, Group, Post

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )
        cls.form = PostForm()
        cls.comment_form = CommentForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        """Валидная форма создает пост"""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=PostFormTests.user,
                text=form_data['text'],
                group=self.group.id,
                image=f'posts/{form_data["image"]}',
            ).exists()
        )
        new_post = Post.objects.latest('id')
        self.assertEqual(new_post.author, PostFormTests.user)
        self.assertEqual(new_post.group, self.group)

    def test_edit_post(self):
        """Валидная форма изменяет пост"""
        new_group = Group.objects.create(
            title='NEW Тестовая группа',
            slug='new_test_slug',
            description='NEW Тестовое описание',
        )
        form_data = {
            'text': 'Тестовый пост edit',
            'group': new_group.id
        }
        response_edit = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response_edit.status_code, HTTPStatus.OK)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
            ).exists()
        )
        new_group_response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': new_group.slug}),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            new_group_response.context['page_obj'].paginator.count, 1
        )
        old_group_response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count, 0
        )

    def test_add_comment(self):
        """Валидная форма создает комментарий"""
        comment_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(self.comment.author, PostFormTests.user)
        self.assertTrue(
            Comment.objects.filter(text=form_data['text']).exists()
        )
