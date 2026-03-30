from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os

class InvoiceGenerator:
    """Generate PDF invoices from transactions"""
    
    def __init__(self, output_dir='invoices'):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def generate_invoice(self, transaction, company_name="Voice Accounting System", 
                        company_address="Your Address Here", company_phone="Your Phone"):
        """
        Generate PDF invoice from transaction
        
        Args:
            transaction: Transaction object with party, material, amount info
            company_name: Your company name
            company_address: Your company address
            company_phone: Your company phone
        
        Returns:
            filepath: Path to generated PDF
        """
        try:
            filename = f"INV_{transaction.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=6,
                alignment=TA_CENTER,
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                textAlign=TA_LEFT,
            )
            
            # Title
            elements.append(Paragraph(company_name, title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Company Info
            company_info = [
                f"<b>Address:</b> {company_address}",
                f"<b>Phone:</b> {company_phone}",
            ]
            for info in company_info:
                elements.append(Paragraph(info, heading_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Invoice Header
            invoice_data = [
                ['<b>INVOICE</b>', '', f'<b>Invoice #:</b> INV-{transaction.id}'],
                ['', '', f'<b>Date:</b> {transaction.created_at.strftime("%d-%m-%Y")}'],
            ]
            
            invoice_table = Table(invoice_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            invoice_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(invoice_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Party Info
            party_data = [
                ['<b>PARTY DETAILS</b>'],
                [f'Name: {transaction.party.name}'],
                [f'Phone: {transaction.party.phone or "N/A"}'],
                [f'Address: {transaction.party.address or "N/A"}'],
            ]
            
            party_table = Table(party_data, colWidths=[5.5*inch])
            party_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6e6e6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(party_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Transaction Details
            rate = transaction.rate if transaction.rate else 0
            amount = transaction.amount if transaction.amount else 0
            
            details_data = [
                ['<b>Item</b>', '<b>Qty</b>', '<b>Unit</b>', '<b>Rate</b>', '<b>Amount</b>'],
                [
                    transaction.material.name.capitalize(),
                    str(transaction.quantity),
                    'Ton',
                    f"₹{rate:,.2f}",
                    f"₹{amount:,.2f}"
                ],
            ]
            
            if transaction.trips and transaction.trips > 1:
                details_data.append([f'Trips: {transaction.trips}', '', '', '', ''])
            
            details_table = Table(details_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d0d0d0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 1), (4, -1), 'RIGHT'),
            ]))
            elements.append(details_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Totals
            payment_amount = transaction.payment_amount if transaction.payment_amount else 0
            pending_amount = amount - payment_amount
            
            totals_data = [
                ['<b>Total Amount</b>', f"₹{amount:,.2f}"],
                ['<b>Payment Received</b>', f"₹{payment_amount:,.2f}"],
                ['<b>Pending Amount</b>', f"₹{pending_amount:,.2f}"],
                ['<b>Status</b>', transaction.payment_status.upper()],
            ]
            
            totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Notes
            if transaction.notes:
                notes_style = ParagraphStyle(
                    'Notes',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor('#666666'),
                )
                elements.append(Paragraph(f"<b>Notes:</b> {transaction.notes}", notes_style))
                elements.append(Spacer(1, 0.1*inch))
            
            # Footer
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#999999'),
                alignment=TA_CENTER,
            )
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph(
                f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | "
                "This is an electronically generated invoice.",
                footer_style
            ))
            
            # Build PDF
            doc.build(elements)
            return filepath
        
        except Exception as e:
            raise Exception(f"Error generating invoice: {str(e)}")
    
    def generate_ledger(self, transactions, filename='ledger.pdf', 
                       company_name="Voice Accounting System"):
        """
        Generate comprehensive ledger PDF from multiple transactions
        """
        try:
            filepath = os.path.join(self.output_dir, filename)
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=6,
                alignment=TA_CENTER,
            )
            
            # Title
            elements.append(Paragraph(f"{company_name} - Ledger", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Generate ledger table
            ledger_data = [
                ['Date', 'Party', 'Material', 'Qty', 'Rate', 'Amount', 'Status']
            ]
            
            total_amount = 0
            for txn in transactions:
                amount = txn.amount if txn.amount else 0
                total_amount += amount
                
                ledger_data.append([
                    txn.created_at.strftime('%d-%m-%Y'),
                    txn.party.name,
                    txn.material.name.capitalize(),
                    str(txn.quantity),
                    f"₹{txn.rate:,.2f}" if txn.rate else "N/A",
                    f"₹{amount:,.2f}",
                    txn.payment_status.capitalize(),
                ])
            
            # Add total row
            ledger_data.append([
                '', '', '', '', '<b>Total</b>', f"<b>₹{total_amount:,.2f}</b>", ''
            ])
            
            ledger_table = Table(ledger_data)
            ledger_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d0d0d0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e6e6e6')),
            ]))
            elements.append(ledger_table)
            
            # Build PDF
            doc.build(elements)
            return filepath
        
        except Exception as e:
            raise Exception(f"Error generating ledger: {str(e)}")
