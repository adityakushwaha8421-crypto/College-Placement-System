# College Placement Management System
### Mini Project for 3rd Year Computer Science

---

## 1. Project Overview

**Title:** College Placement Management System  

**Objective:**  
To develop a web-based application that automates and manages the complete campus placement process of a college. The system helps the Training & Placement (T&P) Cell, students, and companies interact efficiently for job postings, applications, interviews, and final placement tracking.

**Scope:**  
- Multi-role system (Admin, Student, Company)
- Job posting and application management
- Interview scheduling
- Placement reports and statistics
- Secure login and role-based access

**Duration:** 3–5 weeks (suitable for mini project)

---

## 2. Technology Stack (Recommended)

| Layer          | Technology                  |
|----------------|-----------------------------|
| Frontend       | HTML5, CSS3, Bootstrap 5, JavaScript |
| Backend        | Python + Django (Recommended) |
| Database       | SQLite (development) / MySQL (production) |
| Charts         | Chart.js                    |
| Authentication | Django built-in Auth + Custom User Model |

**Alternative Stacks:**
- Flask + SQLAlchemy + Bootstrap
- MERN (MongoDB, Express, React, Node.js)
- PHP + MySQL + Bootstrap

---

## 3. User Roles & Features

### 3.1 Admin (T&P Officer)
- Secure login
- Dashboard with placement statistics
- Manage Students (Approve/Reject registration, view profiles)
- Manage Companies (Approve/Reject, view details)
- Post / Approve Job Openings
- Schedule Interviews
- Update final placement status
- Generate Reports:
  - Placed / Unplaced students
  - Branch-wise placement percentage
  - Company-wise placement count
  - Package-wise analysis
- Export reports (CSV / PDF)

### 3.2 Student
- Registration with academic details (Roll No, Branch, CGPA, Backlogs, Resume)
- Login
- Update Profile & Upload Resume
- View eligible Job Openings
- Apply for jobs
- Track Application Status (Applied → Shortlisted → Selected / Rejected)
- View Interview Schedule
- Download Offer Letter (if selected)

### 3.3 Company
- Registration
- Login
- Post Job Openings (Title, Description, Package, Eligibility Criteria, Deadline)
- View list of Applied Students
- Shortlist / Reject candidates
- Update Interview Results
- View selected candidates

---

## 4. Database Schema (SQL)

```sql
-- Users table (common for all roles)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK(role IN ('admin', 'student', 'company')),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Students table
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    roll_no VARCHAR(20) UNIQUE NOT NULL,
    branch VARCHAR(50) NOT NULL,
    year INTEGER,
    cgpa DECIMAL(3,2),
    backlogs INTEGER DEFAULT 0,
    phone VARCHAR(15),
    resume VARCHAR(255),
    is_placed BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Companies table
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    hr_name VARCHAR(100),
    hr_email VARCHAR(100),
    hr_phone VARCHAR(15),
    website VARCHAR(200),
    description TEXT,
    is_approved BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Jobs table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    package DECIMAL(10,2),
    eligibility_cgpa DECIMAL(3,2),
    eligible_branches TEXT,          -- comma separated or JSON
    location VARCHAR(100),
    last_date DATE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Applications table
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'Applied' 
        CHECK(status IN ('Applied', 'Shortlisted', 'Selected', 'Rejected')),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, job_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Interviews table
CREATE TABLE interviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER UNIQUE NOT NULL,
    interview_date DATE,
    interview_time TIME,
    mode VARCHAR(20) DEFAULT 'Offline',  -- Offline / Online
    venue_or_link VARCHAR(255),
    result VARCHAR(20) DEFAULT 'Pending'
        CHECK(result IN ('Pending', 'Selected', 'Rejected')),
    remarks TEXT,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);
```

---

## 5. Project Folder Structure (Django)

```
placement_system/
├── manage.py
├── requirements.txt
├── placement_system/          # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                  # Custom user & authentication
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── students/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── companies/
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── jobs/
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── applications/
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── base.html
│   ├── admin/
│   ├── student/
│   └── company/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── media/                     # For resume uploads
```

---

## 6. Step-by-Step Implementation Guide (Django)

### Step 1: Setup
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install django pillow
django-admin startproject placement_system
cd placement_system
python manage.py startapp accounts
python manage.py startapp students
python manage.py startapp companies
python manage.py startapp jobs
python manage.py startapp applications
```

### Step 2: Create Custom User Model (accounts/models.py)
Use AbstractUser and add a role field.

### Step 3: Create remaining models
Follow the database schema above.

### Step 4: Create Forms
- StudentRegistrationForm
- CompanyRegistrationForm
- JobPostForm
- ApplicationForm

### Step 5: Implement Views
- Login / Logout / Register
- Role-based dashboards
- Job listing with eligibility filter
- Apply for job
- Admin approval workflows

### Step 6: Templates
Use Bootstrap 5 for clean UI. Create separate dashboards for Admin, Student, and Company.

### Step 7: Reports
Use Django ORM aggregation + Chart.js for visual reports.

### Step 8: Final Polish
- Form validations
- File upload for resume
- Messages framework for success/error
- Responsive design

---

## 7. Sample Project Report Structure

1. Title Page
2. Certificate
3. Acknowledgement
4. Abstract
5. Table of Contents
6. List of Figures / Tables
7. Chapter 1: Introduction
   - 1.1 Problem Statement
   - 1.2 Objectives
   - 1.3 Scope
8. Chapter 2: Literature Survey / Existing System
9. Chapter 3: System Analysis
   - 3.1 Feasibility Study
   - 3.2 Requirements (Functional & Non-functional)
10. Chapter 4: System Design
    - 4.1 Architecture
    - 4.2 ER Diagram
    - 4.3 Data Flow Diagrams
    - 4.4 Database Design
11. Chapter 5: Implementation
12. Chapter 6: Testing
13. Chapter 7: Results & Screenshots
14. Chapter 8: Conclusion & Future Scope
15. References
16. Appendix (Source Code / User Manual)

---

## 8. Important Viva Questions

1. What is the main objective of this project?
2. Explain the different user roles and their permissions.
3. How did you implement role-based access control?
4. Explain the database schema and relationships.
5. How does the eligibility filter work for job applications?
6. What security measures have you taken (password hashing, etc.)?
7. How can this system be improved further?
8. Difference between your system and existing manual process.
9. Which design patterns or Django features did you use?
10. How do you generate placement reports?

---

## 9. Future Enhancements
- Email / SMS notifications
- Resume parsing using AI
- Online aptitude test integration
- Company feedback system
- Mobile app version
- Integration with LinkedIn / Naukri APIs

---

**Prepared for 3rd Year Computer Science Mini Project**
```
