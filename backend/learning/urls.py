from django.urls import path
from . import views

urlpatterns = [
    path("classes/", views.class_collection),
    path("classes/<int:class_id>/", views.class_detail),

    path("subjects/", views.subject_collection),
    path("subjects/<int:subject_id>/", views.subject_detail),
    path("classes/<int:class_id>/subjects/", views.subjects_by_class),

    path("topics/", views.topic_collection),
    path("topics/<int:topic_id>/", views.topic_detail),
    path("subjects/<int:subject_id>/topics/", views.topics_by_subject),

    path("contents/", views.content_collection),
    path("contents/<int:content_id>/", views.content_detail),
    path("topics/<int:topic_id>/contents/", views.contents_by_topic),

    path("questions/", views.question_collection),
    path("questions/<int:question_id>/", views.question_detail),
    path("topics/<int:topic_id>/questions/", views.questions_by_topic),

    path("signup/", views.signup),
    path("login/", views.login),
]