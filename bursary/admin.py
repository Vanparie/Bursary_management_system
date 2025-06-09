from django.contrib import admin
from .models import Student, Guardian, Sibling, BursaryApplication, SupportingDocument, SiteProfile, County, Constituency, OfficerProfile, Ward
from import_export.admin import ImportExportModelAdmin
from .resources import StudentResource


admin.site.register(Guardian)
admin.site.register(Sibling)
admin.site.register(BursaryApplication)
admin.site.register(SupportingDocument)
admin.site.register(SiteProfile)
admin.site.register(Constituency)
admin.site.register(County)
admin.site.register(OfficerProfile)
admin.site.register(Ward)



class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource
    list_display = (
        'admission_number',
        'full_name',
        'constituency',
        'institution',
        'year_of_study',
        'phone',
    )
    search_fields = ('admission_number', 'full_name', 'institution')


admin.site.register(Student, StudentAdmin)
