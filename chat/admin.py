from django.contrib import admin
from .models import UserProfile, Conversation, Message


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'tokens_used_today', 'token_limit_display', 'tokens_reset_date']
    list_editable = ['plan']
    list_filter = ['plan']
    search_fields = ['user__username']
    readonly_fields = ['tokens_used_today', 'tokens_reset_date']

    def token_limit_display(self, obj):
        return f"{obj.get_token_limit():,}"
    token_limit_display.short_description = 'Лимит токенов'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'updated_at']
    list_filter = ['user']
    search_fields = ['title', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'timestamp']
    list_filter = ['role', 'conversation__user']
    readonly_fields = ['timestamp']
