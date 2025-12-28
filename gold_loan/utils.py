import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML, CSS

def render_to_pdf(template_src, context_dict={}):
    """
    Renders a Django template to a PDF using WeasyPrint.
    """
    template = get_template(template_src)
    html_content = template.render(context_dict)
    
    # Create a PDF
    pdf_file = HTML(string=html_content, base_url=settings.MEDIA_ROOT).write_pdf()
    
    return pdf_file

def render_to_pdf_response(template_src, context_dict={}, filename="receipt.pdf"):
    """
    Renders a Django template to a PDF and returns as an HttpResponse.
    """
    pdf = render_to_pdf(template_src, context_dict)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response
