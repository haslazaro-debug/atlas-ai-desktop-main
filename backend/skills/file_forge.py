import os
import datetime
import logging
import asyncio
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

def generate_invoice_pdf_sync(client_name: str, amount: str, service_description: str, invoice_number: str = None) -> str:
    """
    Generates a professional PDF invoice synchronously and returns the file path.
    """
    try:
        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
        
        font_paths = [
            ("C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"),
            ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
        
        for reg_path, bold_path in font_paths:
            if os.path.exists(reg_path):
                try:
                    pdfmetrics.registerFont(TTFont("CustomArial", reg_path))
                    font_regular = "CustomArial"
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont("CustomArial-Bold", bold_path))
                        font_bold = "CustomArial-Bold"
                    else:
                        font_bold = "CustomArial"
                    break
                except Exception as font_err:
                    logger.warning(f"Font register error: {font_err}")

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        inv_id = invoice_number or f"INV-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
        safe_client = "".join([c for c in client_name if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        filename = f"Invoice_{safe_client.replace(' ', '_')}_{inv_id}.pdf"
        file_path = os.path.join(desktop, filename)

        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        # Header / Brand
        c.setFillColor(colors.HexColor("#0f172a"))
        c.rect(0, height - 80, width, 80, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(font_bold, 20)
        c.drawString(40, height - 50, "INVOICE")
        c.setFont(font_regular, 10)
        c.drawString(width - 160, height - 50, "ATLAS OS Billing")

        # Invoice Details
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont(font_bold, 12)
        c.drawString(40, height - 120, f"Billed To: {client_name}")
        c.setFont(font_regular, 10)
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        c.drawString(40, height - 140, f"Invoice #: {inv_id}")
        c.drawString(40, height - 155, f"Date: {current_date}")

        # Table Header
        c.setFillColor(colors.HexColor("#f1f5f9"))
        c.rect(40, height - 200, width - 80, 24, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont(font_bold, 10)
        c.drawString(50, height - 193, "Description")
        c.drawString(width - 120, height - 193, "Amount")

        # Item Row
        c.setFont(font_regular, 10)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawString(50, height - 230, str(service_description))
        c.drawString(width - 120, height - 230, f"{amount}")

        # Total line
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.line(40, height - 250, width - 40, height - 250)
        c.setFont(font_bold, 12)
        c.drawString(width - 220, height - 280, f"Total Due: {amount}")

        c.save()
        logger.info(f"Invoice generated: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Invoice generation error: {e}")
        raise e

async def generate_invoice_pdf_async(client_name: str, amount: str, service_description: str, invoice_number: str = None) -> str:
    """
    Generates a PDF invoice asynchronously (in a thread) and returns the file path.
    """
    return await asyncio.to_thread(
        generate_invoice_pdf_sync,
        client_name,
        amount,
        service_description,
        invoice_number
    )
