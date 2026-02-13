from django.contrib import admin

from .models import GeneratedLicense, LicenseRuntimeConfig


@admin.register(GeneratedLicense)
class GeneratedLicenseAdmin(admin.ModelAdmin):
    list_display = (
        "machine_id",
        "license_key",
        "customer_name",
        "generated_by",
        "generated_at",
        "status",
    )
    list_filter = ("status", "source", "generated_at")
    search_fields = ("machine_id", "license_key", "customer_name", "contact_email")


@admin.register(LicenseRuntimeConfig)
class LicenseRuntimeConfigAdmin(admin.ModelAdmin):
    list_display = (
        "mongo_db",
        "mongo_collection",
        "updated_by",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
