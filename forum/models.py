from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        null=True,  # Allow null for existing posts
        blank=True  # Allow blank in forms
    )
    
    def __str__(self):
        return self.title

class Solution(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='solutions')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Solution by {self.author.username} for {self.post.title}'

class Comment(models.Model):
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.solution.content}'