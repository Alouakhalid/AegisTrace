from django.urls import path

def article_detail(request, article_id):
    pass

def create_article(request):
    pass

def profile_detail(request, user_id):
    pass

def delete_article(request, article_id):
    pass

urlpatterns = [
    path("api/v1/articles/<int:article_id>/", article_detail),
    path("api/v1/articles/", create_article),
    path("api/v1/profiles/<int:user_id>/", profile_detail),
    path("api/v1/articles/delete/<int:article_id>/", delete_article),
]
