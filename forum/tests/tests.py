from django.urls import reverse
from forum.models import User, Post, Course
from django.test import TestCase
import json

class URLTests(TestCase):

    def setUp(self):
        # Create a user to simulate an authenticated user
        self.user = User.objects.create_user(username='testuser', password='testpassword', school_email = 'test@wpga.ca', first_name = 'John', last_name = 'Doe')


    def test_for_you_url(self):
        login_successful = self.client.login(school_email = 'test@wpga.ca', password='testpassword')
        self.assertTrue(login_successful, "Login failed")
        url = reverse('for_you')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_all_posts_url(self):
        url = reverse('all_posts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_post_detail_url(self):
        self.client.login(school_email = 'test@wpga.ca', password='testpassword')
        self.course = Course.objects.create(name="Test Course")

        post_data = {
            'title': 'Test Post',
            'content': json.dumps({'blocks': [{'type': 'paragraph', 'data': {'text': 'Test Content'}}]}),
            'courses': [self.course.id],  
        }

        response = self.client.post(reverse('create_post'), data=post_data)
        
        self.post = Post.objects.get(title='Test Post')
        post_in_db = Post.objects.filter(id=self.post.id).exists()
        self.assertTrue(post_in_db, "Post was not created in the database.")
        url = reverse('post_detail', kwargs={'post_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_post_url(self):
        self.client.login(school_email = 'test@wpga.ca', password='testpassword')
        url = reverse('create_post')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_register_url(self):
        url = reverse('register')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_login_url(self):
        url = reverse('login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_logout_url(self):
        url = reverse('logout')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # 302 for redirection

    def test_search_posts_url(self):
        self.client.login(school_email = 'test@wpga.ca', password='testpassword')
        url = reverse('search_posts') + '?q=test_query'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_profile_view_url(self):
        self.client.login(school_email = 'test@wpga.ca', password='testpassword')
        url = reverse('profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # def test_save_post_url(self):
    #     self.client.login(school_email = 'test@wpga.ca', password='testpassword')
    #     url = reverse('save_post', kwargs={'post_id': 1})
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, 200)
