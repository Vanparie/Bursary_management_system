import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates User accounts for students from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the student CSV file')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']
        created_count = 0
        skipped_count = 0

        try:
            with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    username = row['admission_number'].strip()
                    full_name = row['full_name'].strip()
                    email = f"{username.lower()}@example.com"  # or use actual if available

                    if not User.objects.filter(username=username).exists():
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password='student123'  # 🔒 Set a default password
                        )
                        user.first_name = full_name.split()[0]
                        user.last_name = ' '.join(full_name.split()[1:])
                        user.save()
                        created_count += 1
                    else:
                        skipped_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"✅ {created_count} users created. {skipped_count} users already existed."
            ))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"❌ File not found: {csv_file_path}"))
        except KeyError as e:
            self.stderr.write(self.style.ERROR(f"❌ Missing expected column: {e}"))
