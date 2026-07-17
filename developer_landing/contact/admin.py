from django.contrib import admin

from .models import ContactRequest


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "phone",
        "request_type",
        "ai_available",
        "created_at",
    )
    list_filter = ("request_type", "ai_available", "created_at")
    search_fields = ("name", "email", "phone", "comment")
    readonly_fields = ("created_at",)
