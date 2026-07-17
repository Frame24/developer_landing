from django.urls import path

from developer_landing.contact.views import ContactCreateView
from developer_landing.contact.views import HealthView
from developer_landing.contact.views import MetricsView

app_name = "contact"

urlpatterns = [
    path("contact", ContactCreateView.as_view(), name="contact-create"),
    path("contact/", ContactCreateView.as_view(), name="contact-create-slash"),
    path("health", HealthView.as_view(), name="health"),
    path("health/", HealthView.as_view(), name="health-slash"),
    path("metrics", MetricsView.as_view(), name="metrics"),
    path("metrics/", MetricsView.as_view(), name="metrics-slash"),
]

