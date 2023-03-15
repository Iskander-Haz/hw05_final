from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post

User = get_user_model()


class PostPagesTests(TestCase):

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

        cls.TEMPLATE_PAGES_NAME = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': cls.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': cls.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

    def setUp(self):
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.TEMPLATE_PAGES_NAME.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(
                    reverse_name, follow=True
                )
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        """Шаблоны сформированы с правильным контекстом."""
        response_list = [
            self.authorized_client.get(reverse('posts:index')),
            self.authorized_client.get(
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ),
            self.authorized_client.get(
                reverse('posts:profile', kwargs={'username': self.post.author})
            ),
        ]
        for response in response_list:
            with self.subTest(response=response):
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object.text, self.post.text)
                self.assertEqual(first_object.author, self.post.author)
                self.assertEqual(first_object.group, self.post.group)
                self.assertEqual(first_object.image, self.post.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контентом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контентом."""
        self.user = User.objects.get(username=self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        form_field = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контентом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_field = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_when_create_post(self):
        """Проверка при создании поста"""
        user = User.objects.create_user(username='name_new')
        group = Group.objects.create(
            title='Тестовая группа NEW',
            slug='test_slug_new',
            description='Тестовое описание NEW',
        )
        post = Post.objects.create(
            author=user,
            text='Тестовый пост NEW',
            group=group,
        )
        template_response_list = [
            self.authorized_client.get(reverse('posts:index')),
            self.authorized_client.get(
                reverse('posts:group_list', kwargs={'slug': group.slug})
            ),
            self.authorized_client.get(
                reverse('posts:profile', kwargs={'username': post.author})
            ),
        ]
        for response in template_response_list:
            with self.subTest(response=response):
                self.assertIn(post, response.context['page_obj'])
        response_group = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': group.slug})
        )
        self.assertNotIn(
            PostPagesTests.post, response_group.context['page_obj']
        )

    def test_cache(self):
        """Проверка работы кэша"""
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        posts = response.content
        Post.objects.create(
            text='Тестовый пост NEW',
            author=PostPagesTests.user,
        )
        old_response = self.authorized_client.get(
            reverse('posts:index')
        )
        old_posts = old_response.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        new_response = self.authorized_client.get(
            reverse('posts:index')
        )
        new_posts = new_response.content
        self.assertNotEqual(old_posts, new_posts)

    def test_follow(self):
        """Подписки на авторов работают"""
        Follow.objects.get_or_create(
            user=PostPagesTests.user,
            author=self.post.author
        )
        response_follow = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response_follow.context["page_obj"]), 1)
        self.assertIn(PostPagesTests.post, response_follow.context['page_obj'])
        user = User.objects.create(username='sun')
        self.authorized_client.force_login(user)
        response_not_follow = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post, response_not_follow.context['page_obj'])
        Follow.objects.all().delete()
        response_unfollow = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response_unfollow.context['page_obj']), 0)

    def test_follow_unfollow(self):
        """Подписки и отписки"""
        self.authorized_client.post(
            reverse('posts:profile_follow', kwargs={'username': self.user}),
            follow=True
        )
        self.assertTrue(
            Follow.objects.filter(
                user=PostPagesTests.user, author=self.user
            ).exists()
        )
        self.authorized_client.post(
            reverse('posts:profile_unfollow', kwargs={'username': self.user}),
            follow=True
        )
        self.assertFalse(
            Follow.objects.filter(
                user=PostPagesTests.user, author=self.user
            ).exists()
        )


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.posts = []
        for i in range(13):
            cls.posts.append(
                Post(
                    author=cls.user,
                    text=f'Тестовый пост {i}',
                    group=cls.group
                )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='leo')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно 10"""
        response_list = [
            self.client.get(reverse('posts:index')),
            self.client.get(
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ),
            self.client.get(
                reverse('posts:profile', kwargs={'username': 'name'})
            ),
        ]
        for response in response_list:
            with self.subTest(response=response):
                self.assertEqual(
                    len(response.context['page_obj'].object_list), 10
                )

    def test_second_page_contains_ten_records(self):
        """Количество постов на второй странице равно 3"""
        response_list = [
            self.client.get(reverse('posts:index') + '?page=2'),
            self.client.get(
                reverse(
                    'posts:group_list', kwargs={'slug': self.group.slug}
                ) + '?page=2'
            ),
            self.client.get(
                reverse(
                    'posts:profile', kwargs={'username': 'name'}
                ) + '?page=2'
            ),
        ]
        for response in response_list:
            with self.subTest(response=response):
                self.assertEqual(
                    len(response.context['page_obj'].object_list), 3
                )
