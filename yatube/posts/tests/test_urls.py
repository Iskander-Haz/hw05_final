from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Создадим запись в БД для проверки доступности адреса
        cls.user = User.objects.create_user(username='name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            pk='1'
        )

        cls.TEMPLATES_URL_NAMES = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{cls.group.slug}/',
            'posts/profile.html': f'/profile/{cls.user.username}/',
            'posts/post_detail.html': f'/posts/{cls.post.id}/',
        }

        cls.URL_NAMES = [
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.user.username}/',
            f'/posts/{cls.post.id}/',
        ]

        cls.URL_EDIT_PAGE = f'/posts/{cls.post.id}/edit/'
        cls.URL_404 = f'/posts/{cls.post.id}/ed/'

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages(self):
        """Страницы доступны"""
        for url in self.URL_NAMES:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес для всех использует соответствующий шаблон."""

        for template, url in self.TEMPLATES_URL_NAMES.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_private_urls_uses_correct_template(self):
        """URL-адрес для авторизованных использует соответствующий шаблон."""
        templates_url_names = {
            'posts/create_post.html': '/create/'
        }

        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_page(self):
        """Доступ для авторизованных к странице редактирования поста"""
        self.user = User.objects.get(username=self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user)
        response = self.authorized_client.get(self.URL_EDIT_PAGE)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_page_redirect(self):
        """Доступ для не авторизованных к странице редактирования поста"""
        response_guest = self.guest_client.get(self.URL_EDIT_PAGE)
        response = self.authorized_client.get(self.URL_EDIT_PAGE)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response_guest.status_code, HTTPStatus.FOUND)

    def test_page_404(self):
        """Страницы не существует"""
        response = self.guest_client.get('/sargfsza/')
        self.assertTemplateUsed(response, 'core/404.html')
