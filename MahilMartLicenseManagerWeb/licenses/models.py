from django.db import models


class GeneratedLicense(models.Model):
    machine_id = models.CharField(max_length=64, db_index=True)
    license_key = models.CharField(max_length=64, unique=True)
    customer_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    note = models.TextField(blank=True)
    generated_by = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, default="generated")
    source = models.CharField(max_length=64, default="license_manager_web")
    generated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.machine_id} :: {self.license_key}"


class LicenseRuntimeConfig(models.Model):
    mongo_uri = models.TextField(blank=True)
    mongo_db = models.CharField(max_length=128, blank=True)
    mongo_collection = models.CharField(max_length=128, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "License Runtime Config"
        verbose_name_plural = "License Runtime Config"

    @classmethod
    def get_singleton(cls):
        return cls.objects.order_by("-id").first()

    @classmethod
    def save_singleton(cls, *, mongo_uri, mongo_db, mongo_collection, updated_by):
        instance = cls.get_singleton()
        if instance is None:
            instance = cls.objects.create(
                mongo_uri=mongo_uri,
                mongo_db=mongo_db,
                mongo_collection=mongo_collection,
                updated_by=updated_by,
            )
        else:
            instance.mongo_uri = mongo_uri
            instance.mongo_db = mongo_db
            instance.mongo_collection = mongo_collection
            instance.updated_by = updated_by
            instance.save()

        cls.objects.exclude(pk=instance.pk).delete()
        return instance

    def __str__(self):
        return f"{self.mongo_db}.{self.mongo_collection}"
