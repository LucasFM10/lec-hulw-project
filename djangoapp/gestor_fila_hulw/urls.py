"""
URL configuration for gestor_fila_hulw project.
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# handlers globais (usados quando DEBUG=False)
handler404 = "portal.views.error_404"
handler403 = "portal.views.error_403"
handler500 = "portal.views.error_500"

urlpatterns = ([
    # 1. Redireciona a URL raiz ('') para a página de admin ('/admin/')
    path('', RedirectView.as_view(url='/externo/consulta-posicao', permanent=True)),
    path("i18n/", include("django.conf.urls.i18n")),
    path("fila_cirurgica/", include("fila_cirurgica.urls")),
    path('externo/', include('externo.urls', namespace="externo")),
    path("portal/", include("portal.urls", namespace="portal")),
    path("admin/", admin.site.urls),
    ]
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)