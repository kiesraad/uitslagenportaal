from django.contrib import admin

from .models import Election, TimelineEntry


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(TimelineEntry)
class TimelineEntryAdmin(admin.ModelAdmin):
    list_display = ("election_config", "status", "title", "date")
