from django.contrib import admin

from .models import Election, ElectionStep

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("name", )

@admin.register(ElectionStep)
class ElectionStepAdmin(admin.ModelAdmin):
    list_display = ("election_config", "position", "state", "title", "date")