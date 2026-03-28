from django.db import models

class Class(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    student_class = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="subjects"
    )
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ["student_class", "name"]

    def __str__(self):
        return f"{self.student_class} - {self.name}"


class Topic(models.Model):
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="topics"
    )
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ["subject", "name"]

    def __str__(self):
        return f"{self.subject} - {self.name}"


class Content(models.Model):
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="contents"
    )
    title = models.CharField(max_length=200)
    notes = models.TextField()
    video = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
    )

    def __str__(self):
        return f"{self.get_difficulty_display()}: {self.question_text[:50]}"