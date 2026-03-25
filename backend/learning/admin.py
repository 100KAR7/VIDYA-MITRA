from django.contrib import admin
from .models import Class, Subject, Topic, Content, Question

admin.site.register(Class)
admin.site.register(Subject)
admin.site.register(Topic)
admin.site.register(Content)
admin.site.register(Question)