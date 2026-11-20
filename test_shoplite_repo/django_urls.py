from django.urls import path
from django.db import models

class UserProfile(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    bio = models.TextField()

def profile_detail(request, user_id):
    return {"user_id": user_id}

urlpatterns = [
    path("api/v1/profiles/<int:user_id>/", profile_detail),
]
