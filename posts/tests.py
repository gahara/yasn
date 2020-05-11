from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

from .models import Post, User, Group, Comment, Follow

IMG_TAG = '<img'


class BasicTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='naruto', email='hokage@ya.ru', password='sharingan')
        self.client.force_login(self.user)
        self.post = Post.objects.create(text='dattebayo', author=self.user)
        self.user1 = User.objects.create_user(username='sakura', email='lalala@ya.ru', password='sharingan')

    def test_profile(self):
        """
        После регистрации пользователя создается его персональная страница (profile)
        """
        response = self.client.get(f'/{self.user.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')

    def test_publish_new_post(self):
        """
        Авторизованный пользователь может опубликовать пост (new)
        """
        response = self.client.get(f'/{self.user.username}/{self.post.id}/')
        self.assertTemplateUsed(response, 'post.html')

    def test_return_404(self):
        """
        Возвращает ли сервер код 404, если страница не найдена.
        """
        response = self.client.get('saske/1000')
        self.assertEqual(response.status_code, 404)

    def test_comment(self):
        """
        Авторизированный пользователь может комментировать посты.
        """
        comment_text = 'BRAND NEW COMMENT'
        self.client.post(f'/{self.user.username}/{self.post.id}/comment/', data={'text': comment_text})

        comment_exists = Comment.objects.filter(text=comment_text, post=self.post, author=self.post.author).exists()
        self.assertTrue(comment_exists)

        response = self.client.post(f'/{self.user.username}/{self.post.pk}/')
        self.assertContains(response, comment_text)

    def tearDown(self):
        print('tearDown')


class TestPosts(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='naruto', email='hokage@ya.ru', password='sharingan')
        self.client.force_login(self.user)
        self.test_post = 'Ya budu hokage'

    def test_no_new_post_when_not_authorized(self):
        """
        Неавторизованный посетитель не может опубликовать пост
         (его редиректит на страницу входа)
        """
        self.client.logout()
        response = self.client.get('/new/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/auth/login/?next=/new/')

    @override_settings(CACHES=settings.DUMMY_CACHES)
    def test_post_is_created(self):
        """
        После публикации поста новая запись появляется на главной странице сайта (index),
        на персональной странице пользователя (profile), и на отдельной странице поста (post)
        """
        self.client.post('/new/', {'text': self.test_post})

        response = self.client.get('/')
        self.assertContains(response, self.test_post)

        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, self.test_post)

        response = self.client.get(f'/{self.user.username}/1/')
        self.assertContains(response, self.test_post)

    @override_settings(CACHES=settings.DUMMY_CACHES)
    def test_post_is_edited(self):
        """
        Авторизованный пользователь может отредактировать свой пост
         и его содержимое изменится на всех связанных страницах
        """
        self.client.post('/new/', {'text': self.test_post}, follow=True)

        post = Post.objects.filter(author=self.user).first()

        new_post = 'no eto te tochno'
        self.client.post(f'/{self.user.username}/{post.id}/edit/', {'text': new_post}, follow=True)

        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, new_post)

        response = self.client.get(f'/{self.user.username}/{post.id}/')
        self.assertContains(response, new_post)

        response = self.client.get('/')
        self.assertContains(response, new_post)

    def test_cache(self):
        key = make_template_fragment_key('index_page')
        self.assertFalse(cache.get(key))
        self.client.get('')
        self.assertTrue(cache.get(key))

    def tearDown(self):
        print('tearDown')


class TestImage(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='naruto', email='hokage@ya.ru', password='sharingan')
        user = User.objects.get(username='naruto')
        self.client.force_login(user)
        self.group = Group.objects.create(title='group1', slug='testgroup')

    @override_settings(CACHES=settings.DUMMY_CACHES)
    def test_image_is_loaded(self):
        """
        проверяeт страницу конкретной записи с картинкой: на странице есть тег <img>
        проверяeт, что на главной странице, на странице профайла и на странице группы пост с картинкой отображается корректно, с тегом <img>
        """
        with open('test_files/jojo.jpg', 'rb') as img:
            self.client.post('/new/', {'text': 'post with image', "group": self.group.pk, 'image': img}, follow=True)

        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, IMG_TAG)

        response = self.client.get(f'/group/{self.group.slug}/')
        self.assertContains(response, IMG_TAG)

        response = self.client.get('/')
        self.assertContains(response, IMG_TAG)

        response = self.client.get(f'/{self.user.username}/1/')
        self.assertContains(response, IMG_TAG)

    def test_only_images_can_be_loaded(self):
        """
        проверяет, что срабатывает защита от загрузки файлов не-графических форматов
        """
        with open('test_files/not_image.txt', 'rb') as fp:
            self.client.post('/new/',
                             {'text': 'post with image', 'group': self.group.pk, 'image': fp},
                             follow=True)
        response = self.client.get(f'/{self.user.username}/')
        self.assertNotContains(response, self.client.post)

    def tearDown(self):
        print("tearDown")


class TestFollowers(TestCase):

    def setUp(self):
        self.client = Client()

        self.user1 = User.objects.create_user(
            username='naruto', email='hokage@ya.ru', password="12345"
        )
        self.user2 = User.objects.create_user(
            username='sakura', email='lol@ya.ru', password="12345"
        )
        self.user3 = User.objects.create_user(
            username='saske', email='lmafo@ya.ry', password="12345"
        )

        self.client.force_login(self.user2)
        self.test_post = 'user psto'

    def test_follow_unfollow(self):
        """
        Авторизованный пользователь может подписываться на других пользователей и удалять их из подписок.
        """
        following_exists = Follow.objects.filter(user=self.user2, author=self.user1).exists()
        self.assertFalse(following_exists)
        self.assertEqual(self.user1.following.count(), 0)
        self.assertEqual(self.user2.follower.count(), 0)

        self.client.get(f'/{self.user1.username}/follow')

        following_exists = Follow.objects.filter(user=self.user2, author=self.user1).exists()
        self.assertEqual(self.user1.following.count(), 1)
        self.assertEqual(self.user2.follower.count(), 1)
        self.assertTrue(following_exists)

        self.client.get(f'/{self.user1.username}/unfollow')

        following_exists = Follow.objects.filter(user=self.user2, author=self.user1).exists()
        self.assertFalse(following_exists)
        self.assertEqual(self.user1.following.count(), 0)
        self.assertEqual(self.user2.follower.count(), 0)

    def test_feed(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него подписан
        и не появляется в ленте тех, кто не подписан на него.

        """
        self.client.post('/new/', {'text': self.test_post})
        self.client.logout()

        self.client.force_login(self.user1)
        self.client.get(f'/{self.user2.username}/follow')
        response = self.client.get('/follow/')
        self.assertContains(response, self.test_post)
        self.client.logout()

        self.client.force_login(self.user3)
        response = self.client.get('/follow/')
        self.assertNotContains(response, self.test_post)

    def tearDown(self):
        print('tearDown')
