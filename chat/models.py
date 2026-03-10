from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    PLAN_FREE = 'free'
    PLAN_PREMIUM = 'premium'
    PLAN_CHOICES = [
        (PLAN_FREE, 'Бесплатный'),
        (PLAN_PREMIUM, 'Премиум'),
    ]

    FREE_DAILY_TOKENS = 10000
    PREMIUM_DAILY_TOKENS = 100000

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_FREE)
    tokens_used_today = models.IntegerField(default=0)
    tokens_reset_date = models.DateField(default=timezone.now)

    def get_token_limit(self):
        if self.plan == self.PLAN_PREMIUM:
            return self.PREMIUM_DAILY_TOKENS
        return self.FREE_DAILY_TOKENS

    def reset_tokens_if_needed(self):
        today = timezone.now().date()
        if self.tokens_reset_date < today:
            self.tokens_used_today = 0
            self.tokens_reset_date = today
            self.save(update_fields=['tokens_used_today', 'tokens_reset_date'])

    def can_send_message(self):
        self.reset_tokens_if_needed()
        return self.tokens_used_today < self.get_token_limit()

    def tokens_remaining(self):
        return max(0, self.get_token_limit() - self.tokens_used_today)

    def __str__(self):
        return f"{self.user.username} ({self.get_plan_display()})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Conversation(models.Model):
    CONSULTANT_BUSINESS = 'business'
    CONSULTANT_LEGAL = 'legal'
    CONSULTANT_CHOICES = [
        (CONSULTANT_BUSINESS, 'Бизнес-консультант'),
        (CONSULTANT_LEGAL, 'Юридический консультант'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, default='Новый чат')
    consultant = models.CharField(max_length=20, choices=CONSULTANT_CHOICES, default=CONSULTANT_BUSINESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=10)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
