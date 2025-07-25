# {{ Samburu West NG-CDF Bursary }}

This is a secure, customizable Bursary Management System for {{ Samburu West Constituency }} use.

## Features

- Student registration & login
- Bursary application with document uploads
- Admin dashboard and filters
- SMS + email notifications (optional)
- PDF/CSV reports
- Branding and logo support
- County or CDF type configuration

## Setup

1. Clone this project
2. Create .env file using .env.example
3. Install dependencies:


## pip install -r requirements.txt

4. Run migrations:

## python manage.py migrate

5. Create a superuser:

## python manage.py createsuperuser

6. Start server:

## python manage.py runserver


## Configuration (in .env)

## PROJECT_NAME= Samburu West NG-CDF Bursary BRANDING_TYPE=samburu west constituency EMAIL_HOST_USER=you@example.com EMAIL_HOST_PASSWORD=your-app-password



###  Step 4: (Optional) Create Offline Start Scripts

#### ✅ start.bat for Windows:

```bat
@echo off
call venv\Scripts\activate
python manage.py runserver
pause

✅ start.sh for Linux:

#!/bin/bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000

✅ This allows any CDF/County office to double-click and run the server locally.
