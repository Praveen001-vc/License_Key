from django.urls import path

from .views import (
    dashboard_view,
    initial_admin_setup,
    login_view,
    logout_view,
    user_create_view,
    user_edit_view,
    user_list_view,
)


app_name = "licenses"

urlpatterns = [
    path("", login_view, name="login"),
    path("setup-admin/", initial_admin_setup, name="initial_admin_setup"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("users/", user_list_view, name="user_list"),
    path("users/create/", user_create_view, name="user_create"),
    path("users/<int:user_id>/edit/", user_edit_view, name="user_edit"),
]
