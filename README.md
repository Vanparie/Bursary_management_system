# Bursary Management System

**BursaryFlow** is a Django-based web application for managing bursary applications efficiently at county and constituency levels. It supports students, officers, and admins with a secure and scalable platform.

---

## Features

- **Student Portal**
  - Sign up with National ID/NEMIS verification.
  - Submit bursary applications (personal, guardian, siblings, documents).
  - Upload multiple supporting documents.
  - Track application status and officer feedback.

- **Officer Portal**
  - Role-based access by constituency/county.
  - Review, approve, or reject bursary applications.
  - Add/edit/delete other officers.
  - View statistics and reports.
  - Manage and respond to support requests.

- **Admin Features**
  - Configure site branding per county/constituency.
  - Activity logs for officer actions.
  - Export applications and reports to CSV.

- **Notifications**
  - SMS and email notifications for application updates.
  - Unread support feedback alerts for students.

- **Security & Validation**
  - Robust student identity verification.
  - File upload validation and secure storage.
  - Role-based access control.

---

## Technology Stack

- **Backend:** Django (Python)  
- **Database:** MySQL (production), SQLite (development)  
- **Frontend:** Bootstrap, Django Templates  
- **Notifications:** Africa's Talking (SMS), Email  
- **Version Control:** Git & GitHub  

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Vanparie/bursary-management-system.git
cd bursary-management-system


2. Create and activate a virtual environment:

python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate


3. Install dependencies:

pip install -r requirements.txt


4. Configure environment variables:

- SECRET_KEY

- Database settings (MySQL recommended for production)

- AT_USERNAME, AT_API_KEY for SMS (Africa's Talking)

- Email settings (EMAIL_HOST, EMAIL_PORT, etc.)


5. Apply migrations:

python manage.py migrate


6. Create a superuser:

python manage.py createsuperuser


7. Run the development server:

python manage.py runserver


## Usage

Student: /signup → create account → login → apply for bursary → track applications.

Officer: /officer-login → login → view dashboard → manage applications → respond to support requests.

Admin: /admin → manage site configuration, officers, and student data.


## Project Structure

bursary_management_system/
│
├─ bursary/
│  ├─ templates/
│  ├─ static/
│  ├─ models.py
│  ├─ views.py
│  ├─ forms.py
│  └─ context_processors.py
│
├─ bursary_management_system/
│  ├─ settings.py
│  └─ urls.py
│
├─ manage.py
└─ requirements.txt


## Contributing

1. Fork the repository.

2. Create a feature branch.

3. Commit your changes.

4. Push to your branch.

5. Create a pull request.


## License

This project is licensed under the MIT License.