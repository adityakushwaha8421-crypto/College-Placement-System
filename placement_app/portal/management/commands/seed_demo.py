from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from portal.models import User, Job, Application, Interview, Activity

class Command(BaseCommand):
    help = 'Create fictional demo records once; never reset existing accounts, passwords, or workflows.'
    @transaction.atomic
    def handle(self, *args, **kwargs):
        def account(email, name, role, **extra):
            user, created = User.objects.get_or_create(email=email, defaults={'username':email, 'display_name':name, 'role':role, 'approval':'approved', **extra})
            if created:
                user.set_password('Campus@2027!'); user.save()
            return user
        officer = account('admin@college.edu', 'Priya Sharma', 'admin')
        students = [
            account('student@college.edu', 'Aarav Mehta', 'student', roll_no='CS27001', branch='CSE', cgpa=Decimal('8.70'), phone='9876500101', bio='Computer science student interested in product engineering, accessible design, and practical machine learning.'),
            account('ananya@college.edu', 'Ananya Rao', 'student', roll_no='CS27002', branch='CSE', cgpa=Decimal('9.10')),
            account('kabir@college.edu', 'Kabir Shah', 'student', roll_no='IT27001', branch='IT', cgpa=Decimal('8.20')),
            account('diya@college.edu', 'Diya Nair', 'student', roll_no='EC27001', branch='ECE', cgpa=Decimal('8.80')),
            account('ishaan@college.edu', 'Ishaan Patel', 'student', roll_no='ME27001', branch='ME', cgpa=Decimal('7.90')),
            account('sana@college.edu', 'Sana Khan', 'student', roll_no='IT27002', branch='IT', cgpa=Decimal('8.60')),
            account('rohan@college.edu', 'Rohan Verma', 'student', roll_no='EE27001', branch='EE', cgpa=Decimal('7.60')),
            account('tara@college.edu', 'Tara Das', 'student', roll_no='CE27001', branch='CE', cgpa=Decimal('8.00')),
        ]
        pending, created = User.objects.get_or_create(email='neha@college.edu', defaults={'username':'neha@college.edu', 'display_name':'Neha Iyer', 'role':'student', 'approval':'pending', 'roll_no':'CS27003', 'branch':'CSE', 'cgpa':Decimal('8.40')})
        if created: pending.set_password('Campus@2027!'); pending.save()
        north = account('hr@northstar.example', 'Northstar Labs', 'company', website='https://example.com', bio='Fictional demo partner. A product engineering studio building thoughtful software for ambitious teams. We value curiosity, craftsmanship, and a collaborative mindset.')
        orbit = account('hr@orbit.example', 'Orbit Technologies', 'company', website='https://example.com', bio='Fictional demo partner. Cloud platforms, data products, and a culture built around learning.')
        bloom = account('hr@bloom.example', 'Bloom Digital', 'company', website='https://example.com', bio='Fictional demo partner. A design-focused technology company creating useful digital experiences.')
        terra = account('hr@terra.example', 'Terra Engineering', 'company', website='https://example.com', bio='Fictional demo partner. Engineering a more sustainable world through thoughtful infrastructure and connected systems.')
        day = timezone.localdate()
        specs = [
            (north, 'Graduate Software Engineer', 'Bengaluru · Hybrid', 'Full-time', '12.00', '7.50', ['CSE','IT','ECE'], 21),
            (orbit, 'Cloud Engineering Associate', 'Pune · On-site', 'Full-time', '9.50', '7.00', ['CSE','IT','ECE','EE'], 15),
            (bloom, 'Product Design Intern', 'Remote', 'Internship', '4.80', '6.50', ['CSE','IT','ECE','EE','ME','CE'], 10),
            (north, 'Data & Analytics Associate', 'Bengaluru · Hybrid', 'Full-time', '10.50', '8.00', ['CSE','IT'], 18),
            (terra, 'Graduate Mechanical Engineer', 'Mumbai · On-site', 'Full-time', '7.20', '7.00', ['ME'], 24),
            (orbit, 'Frontend Engineering Intern', 'Remote', 'Internship', '6.00', '7.00', ['CSE','IT'], 14),
            (bloom, 'Quality Assurance Engineer', 'Hyderabad · Hybrid', 'Full-time', '8.00', '7.00', ['CSE','IT','ECE'], 28),
            (terra, 'Infrastructure Engineering Trainee', 'Ahmedabad · On-site', 'Full-time', '6.50', '6.50', ['CE','EE','ME'], 30),
        ]
        jobs=[]
        for company,title,location,kind,package,cgpa,branches,days in specs:
            j,_=Job.objects.get_or_create(company=company,title=title, defaults={'location':location,'job_type':kind,'package':Decimal(package),'min_cgpa':Decimal(cgpa),'branches':branches,'deadline':day+timedelta(days=days),'status':'open','description':f'Build your career with {company}. This fictional opening is part of the local college placement demo.\n\nWhat you will do\n• Work alongside experienced engineers on meaningful projects.\n• Turn ideas into reliable, well-tested solutions.\n• Collaborate with product, design, and operations teams.\n• Share what you learn and grow through mentoring.\n\nWhat we are looking for\nStrong fundamentals, clear communication, and a willingness to learn. Personal projects and collaborative work are welcome.\n\nOur hiring process\nApplication review → Technical discussion → Team conversation → Selection.\n\nWhat you can expect\nStructured onboarding, an assigned mentor, regular feedback, and a supportive campus-to-career experience.'})
            jobs.append(j)
        Job.objects.get_or_create(company=bloom,title='Associate UX Researcher', defaults={'location':'Remote','package':Decimal('8.50'),'min_cgpa':Decimal('7.00'),'branches':['CSE','IT','ECE'],'deadline':day+timedelta(days=20),'status':'pending','description':'Help us understand user needs and turn research into better product decisions. This is a fictional demo role awaiting placement-office approval.'})
        specs = [(0,0,'shortlisted'),(0,1,'applied'),(1,0,'selected'),(2,3,'shortlisted'),(3,1,'selected'),(4,4,'selected'),(5,6,'applied'),(6,7,'applied'),(7,7,'shortlisted')]
        for index,(s,j,status) in enumerate(specs):
            defaults = {'status':status,'cover_note':'I am excited to bring my curiosity, practical project experience, and teamwork to this role.'}
            if status == 'selected':
                defaults.update(selection_package=jobs[j].package, selection_title=jobs[j].title, selection_company=jobs[j].company.display_name, selected_at=timezone.now())
            a,created=Application.objects.get_or_create(student=students[s],job=jobs[j],defaults=defaults)
            if created:
                Activity.objects.create(actor=officer,application=a,message=f'{a.student}: {a.get_status_display()} for {a.job.title}.')
                if status=='shortlisted':
                    Interview.objects.create(application=a,starts_at=timezone.now()+timedelta(days=2+index,hours=2),duration=45,mode='On campus',venue='Placement cell · Interview room 2',notes='Bring a copy of your resume and be ready to discuss a project you are proud of.')
        self.stdout.write(self.style.SUCCESS('Demo records ready. Existing records were preserved.'))
        self.stdout.write('Local demo accounts: admin@college.edu | student@college.edu | hr@northstar.example')
        self.stdout.write('Password: Campus@2027!')
