from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from bursary.models import Banner, LandingSlide, SuccessStory, Announcement, SiteProfile, OfficerProfile
from bursary.forms import BannerForm, LandingSlideForm, SuccessStoryForm, AnnouncementForm

from .decorators import officer_required_can_manage_content


# ----------------------------------------
# Helper: Get officer + site
# ----------------------------------------
def _get_officer_and_site(request):
    try:
        officer = request.user.officer_profile
        return officer, officer.site_profile
    except OfficerProfile.DoesNotExist:
        return None, None



# =========================================================
#                         BANNERS
# =========================================================
@officer_required_can_manage_content
def officer_banners_list(request):
    officer, site = _get_officer_and_site(request)
    if not site:
        messages.error(request, "Site profile not found.")
        return redirect("officer_dashboard")

    banners = Banner.objects.filter(site_profile=site).order_by("order")
    return render(request, "bursary/officer/content/banners_list.html", {
        "banners": banners,
        "page_title": "Banners"
    })


@officer_required_can_manage_content
def officer_banner_create(request):
    officer, site = _get_officer_and_site(request)

    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site_profile = site
            obj.save()
            messages.success(request, "Banner created successfully.")
            return redirect("officer_banners")
    else:
        form = BannerForm()

    return render(request, "bursary/officer/content/banner_form.html", {
        "form": form,
        "action": "Create",
        "page_title": "Create Banner"
    })


@officer_required_can_manage_content
def officer_banner_edit(request, pk):
    officer, site = _get_officer_and_site(request)
    banner = get_object_or_404(Banner, pk=pk, site_profile=site)

    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, "Banner updated successfully.")
            return redirect("officer_banners")
    else:
        form = BannerForm(instance=banner)

    return render(request, "bursary/officer/content/banner_form.html", {
        "form": form,
        "action": "Edit",
        "page_title": "Edit Banner"
    })


@officer_required_can_manage_content
def officer_banner_delete(request, pk):
    officer, site = _get_officer_and_site(request)
    banner = get_object_or_404(Banner, pk=pk, site_profile=site)

    if request.method == "POST":
        banner.delete()
        messages.success(request, "Banner deleted.")
        return redirect("officer_banners")

    return render(request, "bursary/officer/content/confirm_delete.html", {
        "obj": banner,
        "cancel": reverse("officer_banners"),
        "page_title": "Delete Banner"
    })



# =========================================================
#                     LANDING SLIDES
# =========================================================
@officer_required_can_manage_content
def officer_slides_list(request):
    officer, site = _get_officer_and_site(request)
    slides = LandingSlide.objects.filter(site_profile=site).order_by("order")
    return render(request, "bursary/officer/content/slides_list.html", {
        "slides": slides,
        "page_title": "Landing Slides"
    })


@officer_required_can_manage_content
def officer_slide_create(request):
    officer, site = _get_officer_and_site(request)

    if request.method == "POST":
        form = LandingSlideForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site_profile = site
            obj.save()
            messages.success(request, "Landing slide created.")
            return redirect("officer_slides")
    else:
        form = LandingSlideForm()

    return render(request, "bursary/officer/content/slide_form.html", {
        "form": form,
        "action": "Create",
        "page_title": "Create Slide"
    })


@officer_required_can_manage_content
def officer_slide_edit(request, pk):
    officer, site = _get_officer_and_site(request)
    slide = get_object_or_404(LandingSlide, pk=pk, site_profile=site)

    if request.method == "POST":
        form = LandingSlideForm(request.POST, request.FILES, instance=slide)
        if form.is_valid():
            form.save()
            messages.success(request, "Landing slide updated.")
            return redirect("officer_slides")
    else:
        form = LandingSlideForm(instance=slide)

    return render(request, "bursary/officer/content/slide_form.html", {
        "form": form,
        "action": "Edit",
        "page_title": "Edit Slide"
    })


@officer_required_can_manage_content
def officer_slide_delete(request, pk):
    officer, site = _get_officer_and_site(request)
    slide = get_object_or_404(LandingSlide, pk=pk, site_profile=site)

    if request.method == "POST":
        slide.delete()
        messages.success(request, "Landing slide deleted.")
        return redirect("officer_slides")

    return render(request, "bursary/officer/content/confirm_delete.html", {
        "obj": slide,
        "cancel": reverse("officer_slides"),
        "page_title": "Delete Slide"
    })



# =========================================================
#                     SUCCESS STORIES
# =========================================================
@officer_required_can_manage_content
def officer_success_list(request):
    officer, site = _get_officer_and_site(request)

    success_stories = SuccessStory.objects.filter(site_profile=site).order_by("order")
    return render(request, "bursary/officer/content/success_list.html", {
        "success_stories": success_stories,
        "page_title": "Success Stories"
    })


@officer_required_can_manage_content
def officer_success_create(request):
    officer, site = _get_officer_and_site(request)

    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site_profile = site
            obj.save()
            messages.success(request, "Success story created.")
            return redirect("officer_success")
    else:
        form = SuccessStoryForm()

    return render(request, "bursary/officer/content/success_form.html", {
        "form": form,
        "action": "Create",
        "page_title": "Create Success Story"
    })


@officer_required_can_manage_content
def officer_success_edit(request, pk):
    officer, site = _get_officer_and_site(request)
    story = get_object_or_404(SuccessStory, pk=pk, site_profile=site)

    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, "Success story updated.")
            return redirect("officer_success")
    else:
        form = SuccessStoryForm(instance=story)

    return render(request, "bursary/officer/content/success_form.html", {
        "form": form,
        "action": "Edit",
        "page_title": "Edit Success Story"
    })


@officer_required_can_manage_content
def officer_success_delete(request, pk):
    officer, site = _get_officer_and_site(request)
    story = get_object_or_404(SuccessStory, pk=pk, site_profile=site)

    if request.method == "POST":
        story.delete()
        messages.success(request, "Success story deleted.")
        return redirect("officer_success")

    return render(request, "bursary/officer/content/confirm_delete.html", {
        "obj": story,
        "cancel": reverse("officer_success"),
        "page_title": "Delete Success Story"
    })



# =========================================================
#                     ANNOUNCEMENTS
# =========================================================
@officer_required_can_manage_content
def officer_announcements_list(request):
    officer, site = _get_officer_and_site(request)

    announcements = Announcement.objects.filter(site_profile=site).order_by("-created_at")
    return render(request, "bursary/officer/content/announcements_list.html", {
        "announcements": announcements,
        "page_title": "Announcements"
    })


@officer_required_can_manage_content
def officer_announcement_create(request):
    officer, site = _get_officer_and_site(request)

    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.site_profile = site
            obj.created_by = officer
            obj.save()
            messages.success(request, "Announcement created.")
            return redirect("officer_announcements")
    else:
        form = AnnouncementForm()

    return render(request, "bursary/officer/content/announcement_form.html", {
        "form": form,
        "action": "Create",
        "page_title": "Create Announcement"
    })


@officer_required_can_manage_content
def officer_announcement_edit(request, pk):
    officer, site = _get_officer_and_site(request)
    ann = get_object_or_404(Announcement, pk=pk, site_profile=site)

    if request.method == "POST":
        form = AnnouncementForm(request.POST, request.FILES, instance=ann)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated.")
            return redirect("officer_announcements")
    else:
        form = AnnouncementForm(instance=ann)

    return render(request, "bursary/officer/content/announcement_form.html", {
        "form": form,
        "action": "Edit",
        "page_title": "Edit Announcement"
    })


@officer_required_can_manage_content
def officer_announcement_delete(request, pk):
    officer, site = _get_officer_and_site(request)
    ann = get_object_or_404(Announcement, pk=pk, site_profile=site)

    if request.method == "POST":
        ann.delete()
        messages.success(request, "Announcement deleted.")
        return redirect("officer_announcements")

    return render(request, "bursary/officer/content/confirm_delete.html", {
        "obj": ann,
        "cancel": reverse("officer_announcements"),
        "page_title": "Delete Announcement"
    })
