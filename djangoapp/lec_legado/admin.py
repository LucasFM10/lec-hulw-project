from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import LecLegado

@admin.register(LecLegado)
class LecLegadoAdmin(ModelAdmin):
    list_display = [f.name for f in LecLegado._meta.fields[:6]]  # mostra primeiras 6 colunas no list_display
    search_fields = [f.name for f in LecLegado._meta.fields[:6]]
