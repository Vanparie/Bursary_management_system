from django import forms
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    Student, Guardian, Sibling, BursaryApplication, SupportingDocument,
    SiteProfile, County, Constituency, OfficerProfile, Ward, LandingSlide, SuccessStory
)
from .resources import StudentResource


# --- Student Admin ---
class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource
    list_display = (
        'admission_number',
        'first_name', 'middle_name', 'last_name',
        'constituency',
        'institution',
        'year_of_study',
        'phone',
    )
    search_fields = ('admission_number', 'full_name', 'institution')


# --- Custom Form for SiteProfile ---
class SiteProfileForm(forms.ModelForm):
    PROFILE_TYPE_CHOICES = (
        ("county", "County-level"),
        ("constituency", "Constituency-level"),
    )

    profile_type = forms.ChoiceField(
        choices=PROFILE_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Profile Type",
        help_text="Select whether this bursary is managed at county or constituency level."
    )

    class Meta:
        model = SiteProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-fill profile_type based on instance
        if self.instance and self.instance.pk:
            if self.instance.county and not self.instance.constituency:
                self.fields["profile_type"].initial = "county"
            elif self.instance.constituency and not self.instance.county:
                self.fields["profile_type"].initial = "constituency"

    def clean(self):
        cleaned_data = super().clean()
        profile_type = cleaned_data.get("profile_type")

        county = cleaned_data.get("county")
        constituency = cleaned_data.get("constituency")

        if profile_type == "county":
            if not county:
                raise forms.ValidationError("Please select a county for a county-level profile.")
            cleaned_data["constituency"] = None  # clear constituency
        elif profile_type == "constituency":
            if not constituency:
                raise forms.ValidationError("Please select a constituency for a constituency-level profile.")
            cleaned_data["county"] = None  # clear county

        return cleaned_data


@admin.register(SiteProfile)
class SiteProfileAdmin(admin.ModelAdmin):
    form = SiteProfileForm

    list_display = (
        'branding_name',
        'county',
        'constituency',
        'is_active',
        'application_deadline',
    )
    list_filter = ('county', 'constituency', 'is_active')
    search_fields = ('branding_name',)
    ordering = ('county', 'constituency')

    fieldsets = (
        ("Branding", {"fields": ("branding_name", "branding_logo", "is_active")}),
        ("Profile Type", {"fields": ("profile_type",)}),
        ("Location", {"fields": ("county", "constituency")}),
        ("Application Settings", {"fields": ("application_deadline",)}),
    )


# --- Other Models ---
admin.site.register(Guardian)
admin.site.register(Sibling)
admin.site.register(BursaryApplication)
admin.site.register(SupportingDocument)
admin.site.register(Constituency)
admin.site.register(County)
admin.site.register(OfficerProfile)
admin.site.register(Ward)
admin.site.register(Student, StudentAdmin)


@admin.register(LandingSlide)
class LandingSlideAdmin(admin.ModelAdmin):
    list_display = ("headline", "is_active", "order", "updated_at")
    list_editable = ("is_active", "order")
    ordering = ("order",)
    search_fields = ("headline", "subheadline")


@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order", "updated_at")
    list_editable = ("is_active", "order")
    ordering = ("order",)
    search_fields = ("title", "description")



