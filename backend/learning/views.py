from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate

from .models import Class, Content, Question, Subject, Topic
from .serializers import (
    ClassSerializer,
    ContentSerializer,
    QuestionSerializer,
    SubjectSerializer,
    TopicSerializer,
    SignupSerializer,
    LoginSerializer,
)

from rest_framework.authtoken.models import Token


def res(data=None, error=None, code=status.HTTP_200_OK):
    return Response(
        {"success": error is None, "data": data if error is None else None, "error": error},
        status=code,
    )


def handle_detail(request, obj, serializer_class):
    if request.method == "GET":
        return res(serializer_class(obj).data)

    if request.method == "DELETE":
        obj.delete()
        return res(code=status.HTTP_204_NO_CONTENT)

    serializer = serializer_class(
        obj, data=request.data, partial=(request.method == "PATCH")
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def class_collection(request):
    if request.method == "GET":
        return res(ClassSerializer(Class.objects.all().order_by("-id"), many=True).data)

    serializer = ClassSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data, code=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def class_detail(request, class_id):
    return handle_detail(request, get_object_or_404(Class, pk=class_id), ClassSerializer)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def subject_collection(request):
    if request.method == "GET":
        name = request.GET.get("name")
        qs = Subject.objects.filter(name__icontains=name) if name else Subject.objects.all()
        return res(SubjectSerializer(qs, many=True).data)

    serializer = SubjectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data, code=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def subject_detail(request, subject_id):
    return handle_detail(request, get_object_or_404(Subject, pk=subject_id), SubjectSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subjects_by_class(request, class_id):
    return res(SubjectSerializer(Subject.objects.filter(student_class_id=class_id), many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def topic_collection(request):
    if request.method == "GET":
        name = request.GET.get("name")
        qs = Topic.objects.filter(name__icontains=name) if name else Topic.objects.all()
        return res(TopicSerializer(qs, many=True).data)

    serializer = TopicSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data, code=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def topic_detail(request, topic_id):
    return handle_detail(request, get_object_or_404(Topic, pk=topic_id), TopicSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topics_by_subject(request, subject_id):
    return res(TopicSerializer(Topic.objects.filter(subject_id=subject_id), many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def content_collection(request):
    if request.method == "GET":
        return res(ContentSerializer(Content.objects.all(), many=True).data)

    serializer = ContentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data, code=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def content_detail(request, content_id):
    return handle_detail(request, get_object_or_404(Content, pk=content_id), ContentSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contents_by_topic(request, topic_id):
    return res(ContentSerializer(Content.objects.filter(topic_id=topic_id), many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def question_collection(request):
    if request.method == "GET":
        return res(QuestionSerializer(Question.objects.all(), many=True).data)

    serializer = QuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return res(serializer.data, code=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def question_detail(request, question_id):
    return handle_detail(request, get_object_or_404(Question, pk=question_id), QuestionSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def questions_by_topic(request, topic_id):
    return res(QuestionSerializer(Question.objects.filter(topic_id=topic_id), many=True).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)

    return res(
        {"user_id": user.id, "username": user.username, "token": token.key},
        code=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(
        request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )

    if not user:
        return res(error="Invalid username or password", code=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)
    return res({"token": token.key})