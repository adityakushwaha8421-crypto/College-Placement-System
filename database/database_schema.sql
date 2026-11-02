-- =====================================================
-- College Placement Management System
-- Database Schema (SQLite / MySQL Compatible)
-- =====================================================

-- Users table (common for Admin, Student, Company)
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
    resume VARCHAR(255),          -- path to uploaded resume file
    is_placed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Jobs / Job Openings table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    package DECIMAL(10,2),               -- CTC in LPA
    eligibility_cgpa DECIMAL(3,2),
    eligible_branches TEXT,              -- e.g. "CSE,IT,ECE"
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

-- =====================================================
-- Sample Indexes for better performance
-- =====================================================
CREATE INDEX idx_students_branch ON students(branch);
CREATE INDEX idx_students_cgpa ON students(cgpa);
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_applications_student ON applications(student_id);
CREATE INDEX idx_applications_job ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
```
