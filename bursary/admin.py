from django.contrib import admin
from .models import Student, Guardian, Sibling, BursaryApplication, SupportingDocument, SiteProfile, County, Constituency, OfficerProfile, Ward

admin.site.register(Student)
admin.site.register(Guardian)
admin.site.register(Sibling)
admin.site.register(BursaryApplication)
admin.site.register(SupportingDocument)
admin.site.register(SiteProfile)
admin.site.register(Constituency)
admin.site.register(County)
admin.site.register(OfficerProfile)
admin.site.register(Ward)