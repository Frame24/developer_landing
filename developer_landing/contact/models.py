from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactRequest(models.Model):
    class RequestType(models.TextChoices):
        LEAD = "lead", _("Lead")
        QUESTION = "question", _("Question")
        BUG = "bug", _("Bug")
        PARTNERSHIP = "partnership", _("Partnership")
        OTHER = "other", _("Other")

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    email = models.EmailField()
    comment = models.TextField()
    request_type = models.CharField(
        max_length=32,
        choices=RequestType.choices,
        blank=True,
        default="",
    )
    ai_reply = models.TextField(blank=True, default="")
    ai_available = models.BooleanField(default=False)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Contact request")
        verbose_name_plural = _("Contact requests")

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
