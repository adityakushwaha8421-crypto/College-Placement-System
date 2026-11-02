#!/usr/bin/env python3
"""Rebuild the 41-page report with the provided college reference layout."""
from pathlib import Path
from xml.sax.saxutils import escape
import ast, json, math, textwrap
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.utils import ImageReader
from content import TITLE, NAME, GUIDE, COLLEGE, PAGES
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'report_source/assets'
OUT=ROOT/'output/pdf/COLLEGE_PLACEMENT_TUSHAR_LALLU_KHARWAR.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
W,H=A4; LEFT=72; RIGHT=W-72; CW=RIGHT-LEFT
BLUE=colors.HexColor('#5296db'); RED=colors.HexColor('#ff0000')
STYLES={
 'p':ParagraphStyle('body',fontName='Times-Roman',fontSize=12,leading=15,alignment=TA_JUSTIFY,spaceAfter=9),
 'h':ParagraphStyle('h',fontName='Times-Bold',fontSize=12,leading=16,spaceBefore=5,spaceAfter=10),
 'h2':ParagraphStyle('h2',fontName='Times-Bold',fontSize=12,leading=16,spaceBefore=3,spaceAfter=8),
 'title':ParagraphStyle('title',fontName='Times-Bold',fontSize=14,leading=18,alignment=TA_CENTER,textColor=BLUE,spaceAfter=17),
 'chapter':ParagraphStyle('chapter',fontName='Times-Bold',fontSize=18,leading=22,alignment=TA_CENTER,textColor=BLUE,spaceAfter=19),
 'bullet':ParagraphStyle('bullet',fontName='Times-Roman',fontSize=12,leading=15,leftIndent=14,firstLineIndent=-11,spaceAfter=7,alignment=TA_LEFT),
 'cell':ParagraphStyle('cell',fontName='Times-Roman',fontSize=10.7,leading=13.1),
 'small':ParagraphStyle('small',fontName='Times-Roman',fontSize=10,leading=12.5,alignment=TA_LEFT),
 'caption':ParagraphStyle('caption',fontName='Times-Bold',fontSize=11,leading=14,alignment=TA_CENTER),
 'diagram':ParagraphStyle('diagram',fontName='Helvetica',fontSize=9,leading=12,alignment=TA_CENTER),
}
LOG=[]
c=canvas.Canvas(str(OUT),pagesize=A4)
c.setTitle('College Placement Management System - Tushar Lallu Kharwar')
c.setAuthor('Tushar Lallu Kharwar')
c.setSubject('B.Sc. Computer Science Project Report, 2026-27')

class Page:
 def __init__(self,n):
  self.n=n; self.y=H-82;self.lowest=self.y
  c.setStrokeColor(colors.black);c.setLineWidth(1);c.rect(28,28,W-56,H-56)
  c.setFillColor(colors.black);c.setFont('Times-Roman',12);c.drawCentredString(W/2,42,str(n))
  c.bookmarkPage(f'page{n}')
 def put(self,kind,text):
  style=STYLES[kind]
  self.y-=style.spaceBefore
  p=Paragraph(text,style);_,h=p.wrap(CW,1000)
  if self.y-h<67:raise ValueError(f'Page {self.n} overflows: {kind}, bottom={self.y-h:.1f}, {text[:55]}')
  p.drawOn(c,LEFT,self.y-h);self.y-=h+style.spaceAfter;self.lowest=min(self.lowest,self.y)
 def para(self,text):self.put('p',text)
 def gap(self,n):self.y-=n
 def table(self,headers,rows,widths=None,fs=10.7):
  style=ParagraphStyle('tablecell',parent=STYLES['cell'],fontSize=fs,leading=fs+2.8)
  data=[[Paragraph('<b>'+escape(str(x))+'</b>',style) for x in headers]]+[[Paragraph(escape(str(v)),style) for v in row]for row in rows]
  t=Table(data,colWidths=widths or [CW*.63,CW*.37],hAlign='LEFT')
  t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.6,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]))
  _,h=t.wrap(CW,1000)
  if self.y-h<67:raise ValueError(f'Table overflows page {self.n}: {h}')
  t.drawOn(c,LEFT,self.y-h);self.y-=h+15;self.lowest=min(self.lowest,self.y)
 def code(self,source,size=9,leading=11.5):
  maxchars=int((CW-12)/(size*.6));lines=[]
  for line in source.rstrip().splitlines():
   if len(line)<=maxchars:lines.append(line)
   else:
    # Soft print wrapping only; the named source file remains executable.
    indent=' '*(len(line)-len(line.lstrip())+4)
    lines.extend(textwrap.wrap(line,width=maxchars,subsequent_indent=indent,replace_whitespace=False,drop_whitespace=False,break_long_words=True,break_on_hyphens=False))
  h=len(lines)*leading+16
  if self.y-h<67:raise ValueError(f'Code overflows p{self.n}: {len(lines)} lines, y {self.y}')
  c.setFillColor(colors.HexColor('#f7f7f7'));c.setStrokeColor(colors.HexColor('#dddddd'));c.setLineWidth(.4);c.rect(LEFT,self.y-h,CW,h,fill=1)
  t=c.beginText(LEFT+6,self.y-12);t.setFont('Courier',size);t.setLeading(leading);t.setFillColor(colors.black)
  for line in lines:t.textLine(line)
  c.drawText(t);self.y-=h+12;self.lowest=min(self.lowest,self.y)
 def finish(self):
  LOG.append({'page':self.n,'lowest_content_y':round(self.lowest,1)});c.showPage()

def center(text,y,size=12,font='Times-Roman',color=colors.black):
 c.setFillColor(color);c.setFont(font,size);c.drawCentredString(W/2,y,text)

def absolute_paragraph(text,x,top,width,style):
 p=Paragraph(text,style);_,h=p.wrap(width,1000);p.drawOn(c,x,top-h);return h

def picture(path,x,y,w,h):
 im=ImageReader(str(path));iw,ih=im.getSize();scale=min(w/iw,h/ih)
 c.drawImage(im,x+(w-iw*scale)/2,y+(h-ih*scale)/2,width=iw*scale,height=ih*scale,mask='auto')

def cover():
 p=Page(1)
 center('COLLEGE PLACEMENT',H-105,19,'Times-Bold',RED)
 center('MANAGEMENT SYSTEM',H-127,19,'Times-Bold',RED)
 center('A Project Report',H-150,12,color=BLUE)
 center('Submitted in partial fulfillment of the',H-170,12,color=BLUE)
 center('requirements for the award of the degree of',H-187,12,color=BLUE)
 center('BACHELOR OF SCIENCE (COMPUTER SCIENCE)',H-221,13,'Times-Bold')
 center('Submitted By',H-245,12,color=BLUE)
 center(NAME,H-268,13,'Times-Bold',BLUE)
 center('Under the Guidance of',H-290,12)
 center(GUIDE,H-314,15,'Times-Bold',BLUE)
 picture(ASSETS/'college-logo.png',W/2-75,H-498,150,170)
 center('DEPARTMENT OF COMPUTER SCIENCE',H-522,13,'Times-Bold')
 center('Janseva Shikshan Mandal\'s',H-544,12,color=BLUE)
 center('SHANTARAMBHAU GHOLAP ARTS, SCIENCE AND',H-566,12,'Times-BoldItalic',BLUE)
 center('GOTIRAMBHAU PAWAR COMMERCE COLLEGE SHIVLE',H-585,12,'Times-BoldItalic',BLUE)
 center('(Affiliated to University of Mumbai)',H-609,12)
 center('SHIVALE (MURBAD) - 421401',H-630,13,'Times-Bold')
 center('MAHARASHTRA',H-651,13,'Times-Bold');center('2026-27',H-677,15)
 p.finish()

def certificate():
 p=Page(2)
 center('SHANTARAMBHAU GHOLAP ARTS, SCIENCE AND',H-94,14,'Times-Bold')
 center('GOTIRAMBHAU PAWAR COMMERCE COLLEGE SHIVLE',H-113,14,'Times-Bold')
 center('(Affiliated to University of Mumbai)',H-132,12)
 center('SHIVLE (MURBAD)-MAHARASHTRA-421401',H-151,13,'Times-Bold')
 center('DEPARTMENT OF COMPUTER SCIENCE',H-170,12,'Times-Bold',BLUE)
 picture(ASSETS/'college-logo.png',W/2-75,H-356,150,174)
 center('CERTIFICATE',H-379,14,'Times-Bold')
 c.setLineWidth(.6);c.line(W/2-45,H-382,W/2+45,H-382)
 text=f'This is to certify that the project entitled, "<b>{TITLE}</b>" is the bonafide work of <b>{NAME}</b>, submitted in partial fulfillment of the requirements for the award of the degree of <b>BACHELOR OF SCIENCE (COMPUTER SCIENCE)</b> from the University of Mumbai, under the guidance of <b>{GUIDE}</b>.'
 absolute_paragraph(text,LEFT,H-396,CW,STYLES['p'])
 c.setFillColor(BLUE);c.setFont('Times-Bold',12)
 for x,y,t in [(LEFT,H-514,'Internal Guide'),(LEFT+6,H-600,'Internal Examiner'),(RIGHT-105,H-600,'External Examiner'),(LEFT+6,H-682,'Date:'),(W/2-32,H-682,'College Seal'),(RIGHT-54,H-682,'Principal')]:c.drawString(x,y,t)
 p.finish()

def proforma():
 p=Page(3);p.put('title','PROJECT PROFORMA FOR THE APPROVAL PROJECT PROPOSAL')
 p.para('(Note: All entries of the proforma of approval should be filled up with appropriate and complete information. Incomplete proforma of approval in any respect will be summarily rejected.)')
 p.gap(24)
 for text in [f'1. Name of the Student : <b>{NAME}</b>',f'2. Title of the Project : <b>{TITLE}</b>',f'3. Name of the Guide : <b>{GUIDE}</b>','4. Teaching experience of the Guide : Excellent','5. Is this your first submission? Yes']:
  p.para(text);p.gap(7)
 p.gap(55);y=p.y
 absolute_paragraph('Signature of the Student<br/><br/>Date: ....................',LEFT,y,210,STYLES['p'])
 absolute_paragraph('Signature of the Guide<br/><br/>Date: ....................',RIGHT-190,y,190,STYLES['p'])
 p.y-=130;p.para('Signature of the Coordinator');p.para('Date: ....................');p.finish()

def index():
 p=Page(7);p.put('title','INDEX')
 rows=[['1','Certificate','2'],['2','Project Proforma for the Approval Project Proposal','3'],['3','Abstract','4'],['4','Acknowledgment','5'],['5','Declaration','6'],['6','INDEX','7'],['7','CHAPTER 1 - INTRODUCTION','8-10'],['8','CHAPTER 2 - LITERATURE REVIEW / RELATED WORK','11-13'],['9','CHAPTER 3 - METHODOLOGY','14-15'],['10','CHAPTER 4 - IMPLEMENTATION DETAILS','16-18'],['11','CHAPTER 5 - SYSTEM DESIGN','19-22'],['12','CHAPTER 6 - EXPERIMENTAL SETUP & RESULT','23-29'],['13','CHAPTER 7 - ANALYSIS AND REPORT','30-31'],['14','CHAPTER 8 - FUTURE ENHANCEMENTS','32'],['15','CHAPTER 9 - PROGRAM CODE','33-39'],['16','CHAPTER 10 - CONCLUSION','40'],['17','REFERENCES','41']]
 p.table(['SR.NO','CONTENTS','PAGE NO'],rows,[40,CW-90,50],fs=10.3);p.finish()

# All diagram coordinates are vector PDF points, preserving print sharpness.
def box(x,y,w,h,title,lines=(),fill='#f0f5fc',title_size=10):
 c.setFillColor(colors.HexColor(fill));c.setStrokeColor(colors.HexColor('#4c607c'));c.setLineWidth(.8);c.roundRect(x,y,w,h,5,fill=1)
 ts=ParagraphStyle('bt',parent=STYLES['diagram'],fontName='Helvetica-Bold',fontSize=title_size,leading=title_size+2)
 absolute_paragraph(title,x+7,y+h-9,w-14,ts)
 if lines:
  absolute_paragraph('<br/>'.join(escape(s) for s in lines),x+7,y+h-30,w-14,STYLES['diagram'])

def arrow(x1,y1,x2,y2,label='',color='#52677d',dashed=False):
 c.setStrokeColor(colors.HexColor(color));c.setFillColor(colors.HexColor(color));c.setLineWidth(.8)
 if dashed:c.setDash(3,3)
 c.line(x1,y1,x2,y2);c.setDash()
 a=math.atan2(y2-y1,x2-x1);s=5
 path=c.beginPath();path.moveTo(x2,y2);path.lineTo(x2-s*math.cos(a-.45),y2-s*math.sin(a-.45));path.lineTo(x2-s*math.cos(a+.45),y2-s*math.sin(a+.45));path.close();c.drawPath(path,fill=1,stroke=0)
 if label:
  c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#40546c'));c.drawCentredString((x1+x2)/2,(y1+y2)/2+5,label)

def er_page():
 p=Page(15);p.put('h','3.4 DATABASE DESIGN AND RELATIONSHIPS')
 p.para('The working schema uses a custom User record for all three roles. Jobs belong to company users, applications connect students to jobs and an interview belongs to one application. Activity records describe workflow events; pending deletions retain ownership of superseded resume files.')
 box(LEFT,475,185,150,'USER',['PK id; unique email','role; approval; display_name','student: branch, CGPA, roll_no','company: website, bio','private resume reference'])
 box(RIGHT-185,490,185,135,'JOB',['PK id; FK company_id -> User','title; CTC; deadline; state','branches; min_cgpa; max_backlogs'])
 box(LEFT+125,290,200,135,'APPLICATION',['PK id; FK student_id -> User','FK job_id -> Job; status','Unique(student, job)','saved selection facts'])
 arrow(LEFT+95,475,LEFT+180,425,'student 1 : N')
 arrow(RIGHT-90,490,LEFT+255,425,'job 1 : N')
 arrow(LEFT+185,590,RIGHT-185,590,'company 1 : N')
 box(LEFT,130,195,100,'INTERVIEW',['PK id; unique application_id','start; duration; mode; venue'])
 box(RIGHT-195,130,195,100,'ACTIVITY',['PK id; actor_id; application_id','message; created_at'])
 arrow(LEFT+180,290,LEFT+100,230,'0..1 interview')
 arrow(LEFT+270,290,RIGHT-95,230,'0..N events')
 p.y=108;p.put('small','Fig 3.1 Core entity relationships. PendingResumeDeletion stores filename, attempts and last error separately; it has no student/job ownership relationship.');p.finish()

def architecture():
 p=Page(19);p.put('chapter','CHAPTER 5 SYSTEM DESIGN');p.put('h','5.1 ARCHITECTURE DIAGRAM')
 box(LEFT,602,CW,72,'WEB BROWSER',['Officer | Student | Recruiter','HTML templates, local CSS and JavaScript'])
 arrow(W/2,602,W/2,565,'HTTP request / HTML response')
 box(LEFT,470,CW,95,'DJANGO APPLICATION',['Routing + session authentication + CSRF middleware','Forms + role-scoped views + eligibility checks','Application decisions + interview scheduling + report services'])
 arrow(LEFT+100,470,LEFT+100,405,'ORM / transactions')
 arrow(RIGHT-95,470,RIGHT-95,405,'Permission-checked files')
 box(LEFT,312,205,93,'SQLITE DATABASE',['Users, jobs, applications','Interviews, activity, selections','Resume cleanup queue'])
 box(RIGHT-205,312,205,93,'PRIVATE FILE STORAGE',['PDF resumes; random filenames','No public media route','Retry failed replacement cleanup'])
 box(LEFT,180,CW,75,'GENERATED OUTPUTS',['Scoped dashboards and status history','CSV placement reports | PDF reports | selection confirmations'],fill='#f5f7ef')
 arrow(W/2,312,W/2,255,'Read authorised records')
 p.y=153;p.put('caption','Fig 5.1 Architecture of the local College Placement Management System')
 p.put('small','The browser does not connect directly to the database or private upload directory. External email, employer APIs and calendar services are not connected in this implementation.');p.finish()

def sequence():
 p=Page(20);p.put('h','5.2 SEQUENCE DIAGRAM (JOB APPLICATION)')
 xs=[94,211,340,474];names=['Student','Browser UI','Django server','SQLite']
 for x,name in zip(xs,names):
  box(x-38,650,76,38,name,title_size=8.5)
  c.setDash(3,3);c.setStrokeColor(colors.HexColor('#a7b2c2'));c.line(x,650,x,218);c.setDash()
 steps=[(615,0,1,'1. Open opportunity'),(570,1,2,'2. GET job details'),(525,2,3,'3. Read job + account'),(480,3,2,'4. Current records'),(435,2,1,'5. Show details / eligibility'),(390,0,1,'6. Submit application'),(345,1,2,'7. POST + session + CSRF'),(300,2,3,'8. Recheck; insert once'),(255,2,1,'9. Redirect / feedback')]
 for y,a,b,label in steps:
  arrow(xs[a],y,xs[b],y)
  c.setFillColor(colors.black);c.setFont('Helvetica',8);c.drawCentredString((xs[a]+xs[b])/2,y+9,label)
 p.y=190;p.put('caption','Fig 5.2 Student application request and persistent insertion')
 p.para('The server refreshes the relevant records within the local write transaction. If approval, branch, CGPA, backlogs, availability or deadline checks fail, the application is not inserted. If the student already applied, the existing application is retained rather than duplicated.');p.finish()

def actor(x,y,name):
 c.setStrokeColor(colors.HexColor('#40546c'));c.setLineWidth(1)
 c.circle(x,y+18,9,stroke=1,fill=0);c.line(x,y+9,x,y-20);c.line(x-15,y-2,x+15,y-2);c.line(x,y-20,x-13,y-40);c.line(x,y-20,x+13,y-40)
 c.setFillColor(colors.black);c.setFont('Helvetica-Bold',9);c.drawCentredString(x,y-56,name)

def oval(x,y,w,h,text):
 c.setStrokeColor(colors.HexColor('#67809b'));c.setFillColor(colors.HexColor('#f2f6fc'));c.ellipse(x,y,x+w,y+h,stroke=1,fill=1)
 absolute_paragraph(text,x+10,y+h/2+12,w-20,STYLES['diagram'])

def usecase():
 p=Page(21);p.put('h','5.3 USE CASE DIAGRAM')
 c.setStrokeColor(colors.HexColor('#a5afbf'));c.setLineWidth(.7);c.rect(177,145,244,535)
 center('College Placement System',659,10,'Helvetica-Bold')
 cases=[(605,'Register / sign in'),(535,'Maintain profile / resume'),(465,'Browse / apply / withdraw'),(395,'Review candidates'),(325,'Manage / view interviews'),(255,'Approve accounts / jobs'),(185,'View reports / confirmation')]
 for y,t in cases:oval(197,y-20,204,47,t)
 actor(105,502,'Student');actor(490,400,'Recruiter');actor(105,263,'Officer')
 for y in [605,535,465,325,185]:arrow(120,492,197,y,dashed=True)
 for y in [605,535,395,325,185]:arrow(475,390,401,y,dashed=True)
 for y in [605,395,325,255,185]:arrow(120,253,197,y,dashed=True)
 p.y=117;p.put('caption','Fig 5.3 Main actors and permitted campus placement use cases')
 p.put('small','Students view interviews and their own confirmations; officers export reports. Scheduling is restricted to approved recruiters/officers. Recruiters see their own candidates.');p.finish()

def activity_diagram():
 p=Page(22);p.put('h','5.4 ACTIVITY DIAGRAM')
 x=170;w=255
 steps=[(666,'Register / sign in and prepare profile'),(595,'Officer approves account and opening'),(524,'Student reviews role and applies')]
 for y,t in steps:box(x,y,w,42,t,title_size=9)
 arrow(W/2,666,W/2,637);arrow(W/2,595,W/2,566)
 # Decision diamond.
 c.setStrokeColor(colors.HexColor('#4c607c'));c.setFillColor(colors.HexColor('#fff5df'))
 path=c.beginPath();path.moveTo(W/2,492);path.lineTo(W/2+100,459);path.lineTo(W/2,426);path.lineTo(W/2-100,459);path.close();c.drawPath(path,fill=1,stroke=1)
 center('Eligible and not already applied?',456,8,'Helvetica-Bold')
 arrow(W/2,524,W/2,492)
 box(75,335,165,54,'NO: Show reason',['No new application row'],fill='#fff0ee',title_size=9)
 box(315,335,205,54,'YES: Save application',['Applied -> Shortlisted'],title_size=9)
 arrow(W/2-100,459,157,389,'No');arrow(W/2+100,459,417,389,'Yes')
 box(315,245,205,50,'Schedule / conduct interview',title_size=9);arrow(417,335,417,295)
 box(290,150,230,55,'Record decision',['Selected or Rejected','Student may withdraw while active'],fill='#eef6ed',title_size=9)
 arrow(417,245,417,205)
 p.y=118;p.put('caption','Fig 5.4 Recruitment activity flow with server-side eligibility')
 p.put('small','A selection preserves its recorded terms and becomes available in reports. Withdrawn applications remain stored and cannot be resubmitted to the same opening.');p.finish()

def screenshots(n,first,second):
 p=Page(n)
 if n==27:p.put('h','6.10 SCREENSHOTS')
 for filename,caption in [first,second]:
  height=275;path=ASSETS/(filename+'.png')
  c.setStrokeColor(colors.HexColor('#cccccc'));c.setLineWidth(.5);c.rect(LEFT,p.y-height,CW,height)
  picture(path,LEFT+1,p.y-height+1,CW-2,height-2)
  p.y-=height+8;p.put('caption',caption);p.gap(13)
 p.finish()

def source_block(file,node,method=None,decorators=True):
 source=(ROOT/file).read_text();tree=ast.parse(source)
 target=next(n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==node)
 if method:target=next(n for n in target.body if isinstance(n,ast.FunctionDef) and n.name==method)
 start=min([target.lineno]+[d.lineno for d in getattr(target,'decorator_list',[])]) if decorators else target.lineno
 return '\n'.join(source.splitlines()[start-1:target.end_lineno])

def code_pages():
 # Selected excerpts are copied from the verified working source, not invented APIs.
 specs=[
 (33,'9.1 Implementation Code','The application is implemented with Python and Django. The following pages contain selected source excerpts from the working project. Long lines wrap for printing; the named project files contain the executable source.',[
 ('9.1.1 Role-scoped application access','portal/services.py',source_block('portal/services.py','application_scope')),
 ('9.1.2 Eligibility boundary','portal/models.py',source_block('portal/models.py','Job','eligibility_reasons')),
 ]),
 (34,'9.1.3 Persistent application record','Applications link a student to an opportunity, enforce uniqueness and retain selection facts. Display properties use the saved facts after selection.',[
 ('Application model and display properties','portal/models.py',source_block('portal/models.py','Application')),
 ]),
 (35,'9.1.4 Registration validation','Fields belonging to another registration role are ignored before validation. This excerpt shows role-specific validation and account persistence.',[
 ('RegistrationForm.clean and save','portal/forms.py',source_block('portal/forms.py','RegistrationForm','clean')+'\n\n'+source_block('portal/forms.py','RegistrationForm','save')),
 ('Case-insensitive sign-in lookup','portal/auth.py',source_block('portal/auth.py','EmailBackend')),
 ]),
 (36,'9.1.5 Applying to an opportunity','The POST handler performs the current eligibility check inside a transaction and uses get_or_create with the database uniqueness constraint.',[
 ('Application submission view','portal/views.py',source_block('portal/views.py','apply')),
 ('Recorded selection display','portal/models.py',source_block('portal/models.py','Application','display_title')+'\n\n'+source_block('portal/models.py','Application','display_package')),
 ]),
 (37,'9.1.6 Interview form validation','Future times and valid HTTP(S) meeting URLs are checked before scheduling. Invalid parsing, credentials and invalid ports are returned as form errors.',[
 ('Interview validation methods','portal/forms.py',source_block('portal/forms.py','InterviewForm','clean_starts_at')+'\n\n'+source_block('portal/forms.py','InterviewForm','clean')),
 ('Duplicate application constraint','portal/models.py','class Meta:\n    ordering = ["-applied_at", "-pk"]\n    constraints = [models.UniqueConstraint(\n        fields=["student", "job"],\n        name="one_application_per_student_job"\n    )]'),
 ]),
 (38,'9.1.7 Retryable resume cleanup','File cleanup is not treated as an automatic database rollback. Failed superseded-file deletions retain their queue entries and can be retried safely.',[
 ('Retry superseded resume deletions','portal/uploads.py',source_block('portal/uploads.py','retry_resume_deletions')),
 ('Discard an upload after rollback','portal/uploads.py',source_block('portal/uploads.py','discard_rolled_back_upload')),
 ]),
 (39,'9.1.8 CSV export and privacy response','Export values that resemble spreadsheet formulas are prefixed as text. Authenticated pages and downloads receive explicit private/no-store caching directives.',[
 ('CSV value boundary','portal/services.py',source_block('portal/services.py','safe_cell')),
 ('Scoped response cache policy','portal/middleware.py',source_block('portal/middleware.py','WorkspacePrivacyMiddleware')),
 ])]
 for n,heading,desc,blocks in specs:
  p=Page(n)
  if n==33:p.put('chapter','CHAPTER 9 PROGRAM CODE')
  p.put('h',heading);p.para(desc)
  for title,file,code in blocks:
   p.put('h2',title);p.put('small','Source: '+file+' (selected excerpt)');p.code(code)
  p.finish()

cover();certificate();proforma()
for n in range(4,7):
 p=Page(n)
 for kind,value in PAGES[n]:
  if kind=='gap':p.gap(value)
  else:p.put(kind,value)
 p.finish()
index()

# Build remaining pages in exact order.
for n in range(8,33):
 if n==15:er_page();continue
 if n==19:architecture();continue
 if n==20:sequence();continue
 if n==21:usecase();continue
 if n==22:activity_diagram();continue
 if 27<=n<=29:
  pairs={27:(('login','Fig 6.1 Login page with role-specific demo access'),('officer','Fig 6.2 Placement officer dashboard and campus overview')),28:(('student','Fig 6.3 Student dashboard with eligible opportunities'),('jobs','Fig 6.4 Searchable job openings and eligibility information')),29:(('applications','Fig 6.5 Application pipeline with role-scoped decisions'),('reports','Fig 6.6 Placement reports and export controls'))}
  screenshots(n,*pairs[n]);continue
 p=Page(n)
 for kind,value in PAGES[n]:
  if kind=='gap':p.gap(value)
  elif kind=='items':
   for item in value:p.put('bullet','- '+item)
  elif kind=='table':p.table(*value)
  elif kind=='code':p.code(value)
  else:p.put(kind,value)
 p.finish()
code_pages()
for n in (40,41):
 p=Page(n)
 for kind,value in PAGES[n]:
  if kind=='refs':
   for i,(title,url) in enumerate(value,1):
    p.put('small',f'{i}. {escape(title)}<br/>{escape(url)}');p.gap(7)
  else:p.put(kind,value)
 p.finish()
c.save()
(ROOT/'tmp/pdfs/placement-report/layout-log.json').write_text(json.dumps(LOG,indent=2))
print('Created',OUT)
print('Pages:',len(LOG))
