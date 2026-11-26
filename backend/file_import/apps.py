from django.apps import AppConfig


class FileImportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "file_import"
    label = "eml_import"
