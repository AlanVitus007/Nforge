from django.contrib import admin
from .models import PaperChunk, ResearchSession, ResearchMessage, ResearchEvidence


@admin.register(PaperChunk)
class PaperChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "paper", "chunk_index", "page_number", "created_at")
    search_fields = ("paper__title", "text")
    list_filter = ("paper",)


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "created_at", "updated_at")
    search_fields = ("title", "project__title")
    list_filter = ("project", "created_at")
    filter_horizontal = ("papers",)


@admin.register(ResearchMessage)
class ResearchMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "created_at")
    search_fields = ("content", "session__title")
    list_filter = ("role", "created_at")


@admin.register(ResearchEvidence)
class ResearchEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "paper", "chunk", "page_number", "created_at")
    search_fields = ("text", "paper__title")
    list_filter = ("paper", "created_at")
