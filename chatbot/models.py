from django.db import models
from django.conf import settings
import uuid


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.id})"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    agent_used = models.CharField(max_length=50, blank=True, default='')
    route = models.CharField(max_length=20, blank=True, default='')
    sources = models.JSONField(default=list, blank=True)
    citation_map = models.JSONField(default=dict, blank=True)
    graph = models.JSONField(null=True, blank=True, default=None)
    diagnosis = models.JSONField(null=True, blank=True, default=None)
    feedback = models.CharField(
        max_length=20,
        blank=True,
        default='',
        choices=[
            ('', 'No Feedback'),
            ('correct', 'Correct'),
            ('incorrect', 'Incorrect'),
            ('partial', 'Partially Correct'),
        ],
    )
    feedback_note = models.TextField(blank=True, default='')
    processing_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
