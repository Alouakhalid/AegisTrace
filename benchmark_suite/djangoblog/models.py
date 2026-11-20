from django.db import models

class UserProfile(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    bio = models.TextField()

class Article(models.Model):
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

class Category(models.Model):
    name = models.CharField(max_length=50)
