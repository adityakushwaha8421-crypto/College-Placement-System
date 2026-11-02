import csv
from io import BytesIO
from decimal import Decimal
from django.db.models import Count, Max
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape
from .models import User, Application, BRANCHES

def application_scope(user):
    qs = Application.objects.select_related('student', 'job', 'job__company', 'interview')
    if user.role == 'student': return qs.filter(student=user)
    if user.role == 'company': return qs.filter(job__company=user)
    if user.role == 'admin': return qs
    raise PermissionDenied

def report_data(branch=''):
    students = User.objects.filter(role='student', approval='approved', is_active=True)
    if branch: students = students.filter(branch=branch)
    selected = Application.objects.filter(status='selected', student__in=students)
    placed_ids = selected.values('student_id').distinct()
    total, placed = students.count(), placed_ids.count()
    rows = []
    for code, label in BRANCHES:
        cohort = students.filter(branch=code)
        n = cohort.count()
        p = cohort.filter(pk__in=placed_ids).count()
        if n: rows.append({'code': code, 'label': label, 'total': n, 'placed': p, 'rate': round(p / n * 100)})
    companies = selected.values('selection_company').annotate(count=Count('student_id', distinct=True)).order_by('-count')
    salaries = selected.aggregate(highest=Max('selection_package'))
    # Average each student's highest accepted package, so multiple selections do not double-count a student.
    best = list(selected.values('student_id').annotate(best=Max('selection_package')).values_list('best', flat=True))
    average = sum(best, Decimal(0)) / len(best) if best else Decimal(0)
    return {'total': total, 'placed': placed, 'unplaced': total - placed, 'rate': round(placed / total * 100) if total else 0,
            'branches': rows, 'companies': companies, 'highest': salaries['highest'] or 0, 'average': round(average, 2), 'selected': selected}

def safe_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text

def csv_response(filename, headers, rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows: writer.writerow([safe_cell(c) for c in row])
    return response

def pdf_response(filename, title, subtitle, headers, rows, footer='Campus Placement Office | Internal placement records'):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=40)
    styles = getSampleStyleSheet()
    body = styles['BodyText']; body.fontSize = 9; body.leading = 13
    flow = [Paragraph(escape(title), styles['Title']), Paragraph(escape(subtitle), body), Spacer(1, 20)]
    data = [[Paragraph(escape(str(v)), body) for v in headers]]
    data += [[Paragraph(escape(str(v)), body) for v in row] for row in rows]
    table = Table(data, repeatRows=1, colWidths=[(landscape(A4)[0] - 64) / len(headers)] * len(headers), hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e9fa')), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f8fc')]), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9), ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d9deea'))]))
    flow.append(table)
    flow += [Spacer(1, 20), Paragraph(escape(footer), body)]
    def page_footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(32, 20, f'PlacementOS | Generated {timezone.localtime():%d %b %Y, %H:%M} IST')
        canvas.drawRightString(landscape(A4)[0] - 32, 20, str(doc.page))
    doc.build(flow, onFirstPage=page_footer, onLaterPages=page_footer)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
