from django.urls import path
from bursary.officer import content_views as content

urlpatterns = [
    # banners
    path("content/banners/", content.officer_banners_list, name="officer_banners"),
    path("content/banners/create/", content.officer_banner_create, name="officer_banner_create"),
    path("content/banners/<int:pk>/edit/", content.officer_banner_edit, name="officer_banner_edit"),
    path("content/banners/<int:pk>/delete/", content.officer_banner_delete, name="officer_banner_delete"),

    # slides
    path("content/slides/", content.officer_slides_list, name="officer_slides"),
    path("content/slides/create/", content.officer_slide_create, name="officer_slide_create"),
    path("content/slides/<int:pk>/edit/", content.officer_slide_edit, name="officer_slide_edit"),
    path("content/slides/<int:pk>/delete/", content.officer_slide_delete, name="officer_slide_delete"),

    # success stories
    path("content/success/", content.officer_success_list, name="officer_success"),
    path("content/success/create/", content.officer_success_create, name="officer_success_create"),
    path("content/success/<int:pk>/edit/", content.officer_success_edit, name="officer_success_edit"),
    path("content/success/<int:pk>/delete/", content.officer_success_delete, name="officer_success_delete"),

    # announcements
    path("content/announcements/", content.officer_announcements_list, name="officer_announcements"),
    path("content/announcements/create/", content.officer_announcement_create, name="officer_announcement_create"),
    path("content/announcements/<int:pk>/edit/", content.officer_announcement_edit, name="officer_announcement_edit"),
    path("content/announcements/<int:pk>/delete/", content.officer_announcement_delete, name="officer_announcement_delete"),

]
