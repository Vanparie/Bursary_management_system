from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from bursary.models import (
    BursaryApplication, Student, Guardian, Sibling,
    SupportingDocument, Constituency
)

class Command(BaseCommand):
    help = 'Set up the Constituency Officer group with proper permissions'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='(Optional) Username to add to officer group')

    def handle(self, *args, **options):
        group_name = 'Constituency Officer'
        group, created = Group.objects.get_or_create(name=group_name)

        # Models and permissions they need
        model_perms = {
            BursaryApplication: ['view_bursaryapplication', 'change_bursaryapplication'],
            Student: ['view_student'],
            Guardian: ['view_guardian'],
            Sibling: ['view_sibling'],
            SupportingDocument: ['view_supportingdocument'],
            Constituency: ['view_constituency'],
        }

        for model, perms in model_perms.items():
            ct = ContentType.objects.get_for_model(model)
            for codename in perms:
                try:
                    perm = Permission.objects.get(content_type=ct, codename=codename)
                    group.permissions.add(perm)
                    self.stdout.write(self.style.SUCCESS(f"Added {codename} for {model.__name__}"))
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission {codename} not found"))

        if options['username']:
            try:
                user = User.objects.get(username=options['username'])
                user.groups.add(group)
                self.stdout.write(self.style.SUCCESS(f"✅ User '{user.username}' added to '{group_name}' group"))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{options['username']}' not found"))

        self.stdout.write(self.style.SUCCESS(f"🎉 Group '{group_name}' setup complete."))
