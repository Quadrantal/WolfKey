from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.urls import reverse
import os
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='forum_users',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='forum_users',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    school_email = models.EmailField(
        unique=True,
        help_text="Must be a valid @wpga.ca email address",
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9._%+-]+@wpga\.ca$',
                message="Email must be a valid @wpga.ca address"
            )
        ]
    )
    personal_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Optional personal email address"
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text="Optional phone number in international format (e.g., +12345678900)"
    )

class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, default = "Misc")
    description = models.TextField(blank=True)
    
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.JSONField() 
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    search_vector = SearchVectorField(null=True, blank=True)
    courses = models.ManyToManyField(Course, related_name='posts', blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        search_vector = (
            SearchVector('title', weight='A') +
            SearchVector('content', weight='B')
        )
        Post.objects.filter(id=self.id).update(search_vector=search_vector)

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.id])

    
class SavedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saves")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Ensure users can't save the same post twice.

    def __str__(self):
        return f"{self.user.username} saved {self.post.title}"

class File(models.Model):
    post = models.ForeignKey('Post', related_name='files', on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='uploads/')
    temporary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    upload_session = models.CharField(max_length=100, blank=True)
    
    def delete(self, *args, **kwargs):
        # Delete actual file when model is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.file.name}"
    
    @property
    def filename(self):
        return os.path.basename(self.file.name)

class Solution(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='solutions')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    def __str__(self):
        return f'Solution by {self.author.username} for {self.post.title}'

class Comment(models.Model):
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    upvotes = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author.username}'

class SolutionUpvote(models.Model):
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('solution', 'user')

class SolutionDownvote(models.Model):
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('solution', 'user')

class CommentUpvote(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('comment', 'user')

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    points = models.IntegerField(default=0)
    is_moderator = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
    



class UserCourseExperience(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experienced_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'course']

class UserCourseHelp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='help_needed_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'course']


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('post', 'New Post'),
        ('solution', 'New Solution'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']