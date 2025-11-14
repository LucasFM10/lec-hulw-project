from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    AihDetailView,
    DashboardView,
    FilaDeactivateView,
    FilaListView,
    FilaCreateView,
    FilaDetailView,
    FilaUpdateView,
    FilaHistoryView,
    AihListView,
    AihCreateView,
    PortalLoginView
)

app_name = "portal"

urlpatterns = [
    # Autenticação (usa templates do portal)
    path("login/", PortalLoginView.as_view(template_name="portal/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Dashboard
    path("", DashboardView.as_view(), name="dashboard"),

    # Fila (ListaEsperaCirurgica)
    path("fila/", FilaListView.as_view(), name="fila_list"),
    path("fila/nova/", FilaCreateView.as_view(), name="fila_create"),
    path("fila/<int:pk>/", FilaDetailView.as_view(), name="fila_detail"),
    path("fila/<int:pk>/editar/", FilaUpdateView.as_view(), name="fila_update"),
    path("fila/<int:pk>/historico/", FilaHistoryView.as_view(), name="fila_history"),
    path("fila/<int:pk>/remover/", FilaDeactivateView.as_view(), name="fila_remove"),
    path("aih/", AihListView.as_view(), name="aih_list"),
    path("aih/nova/", AihCreateView.as_view(), name="aih_create"),
    path("aih/<int:pk>/", AihDetailView.as_view(), name="aih_detail"),
]
