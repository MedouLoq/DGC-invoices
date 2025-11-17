from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime


class Company(models.Model):
    """Company information - Singleton model (only one instance allowed)"""
    
    name = models.CharField(max_length=200, default="DGC Engineering Sarl")
    address = models.TextField(default="TVZ- NDB Street - University zone 0321")
    city = models.CharField(max_length=100, default="Nouakchott")
    country = models.CharField(max_length=100, default="Mauritania")
    phone = models.CharField(max_length=20, default="+222 33 35 93 33")
    email = models.EmailField(default="info@dgc.mr")
    nif = models.CharField(
        max_length=50, 
        default="00718015",
        verbose_name="NIF",
        help_text="Tax Identification Number"
    )
    
    # Bank information
    bank_name = models.CharField(max_length=200, default="BPM")
    account_number = models.CharField(max_length=100, default="1004497")
    bank_code = models.CharField(max_length=50, default="DGC - EG", blank=True)
    
    # Settings
    default_currency = models.CharField(max_length=10, default="MRU")
    default_tva_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Default TVA/VAT rate in percentage"
    )
    
    # Department info
    department = models.CharField(max_length=100, default="Commercial Dept", blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Information"
        verbose_name_plural = "Company Information"
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Ensure only one company instance exists"""
        if not self.pk and Company.objects.exists():
            raise ValidationError("Only one company instance is allowed. Please edit the existing one.")
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_company(cls):
        """Get or create the singleton company instance"""
        company, created = cls.objects.get_or_create(pk=1)
        return company


class Customer(models.Model):
    """Customer/Client information"""
    
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True, help_text="City or location")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True, help_text="Full address")
    tax_id = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="NIF/Tax ID",
        help_text="Customer Tax Identification Number"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='customers_created'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_invoices(self):
        """Count of invoices for this customer"""
        return self.documents.filter(document_type='invoice').count()
    
    @property
    def total_quotations(self):
        """Count of quotations for this customer"""
        return self.documents.filter(document_type='quotation').count()


class Document(models.Model):
    """
    Main document model handling both Quotations and Invoices.
    Quotations can be converted to Invoices upon approval.
    """
    
    DOCUMENT_TYPE_CHOICES = [
        ('quotation', 'Quotation'),
        ('invoice', 'Invoice'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    CURRENCY_CHOICES = [
        ('MRU', 'MRU - Mauritanian Ouguiya'),
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
    ]
    
    # Document identification
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default='quotation',
        help_text="Type of document"
    )
    reference = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Auto-generated: QT-YY-MM-XXX or IN-YY-MM-XXX"
    )
    date = models.DateField(default=datetime.now)
    
    # Customer information
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT,
        null=True, 
        blank=True,
        related_name='documents',
        help_text="Link to customer database (optional)"
    )
    customer_name = models.CharField(max_length=200, help_text="Customer name (required)")
    customer_location = models.CharField(max_length=300, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_po_ref = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Customer PO Reference",
        help_text="Customer's Purchase Order reference (for invoices)"
    )
    
    # Quotation-specific fields
    work_delivery = models.TextField(
        blank=True,
        verbose_name="Work Delivery Terms",
        help_text="Delivery terms (quotations only)"
    )
    payment_terms = models.TextField(
        blank=True,
        verbose_name="Payment Terms",
        help_text="Payment conditions (quotations only)"
    )
    
    # Financial fields
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='MRU'
    )
    tva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="TVA Rate (%)",
        help_text="Tax rate in percentage"
    )
    
    # Invoice-specific: Amount in words (generated automatically)
    amount_in_words = models.TextField(
        blank=True,
        help_text="Amount written in words (invoices only)"
    )
    
    # Document workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Conversion tracking (only for quotations)
    converted_to_invoice = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_quotation',
        help_text="Invoice created from this quotation"
    )
    
    # Approval tracking
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_documents'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_documents'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Internal notes (not shown on document)"
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Additional text for document footer"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['reference']),
            models.Index(fields=['customer']),
        ]
        verbose_name = "Document"
        verbose_name_plural = "Documents"
    
    def __str__(self):
        return f"{self.get_document_type_display()} {self.reference} - {self.customer_name}"
    
    def clean(self):
        """Validate document before saving"""
        # Prevent converting invoices to quotations
        if self.pk:
            old_instance = Document.objects.get(pk=self.pk)
            if old_instance.document_type == 'invoice' and self.document_type == 'quotation':
                raise ValidationError("Cannot convert an invoice back to a quotation")
        
        # Quotations cannot have customer_po_ref or amount_in_words
        if self.document_type == 'quotation':
            if self.customer_po_ref:
                raise ValidationError("Quotations should not have Customer PO Reference")
        
        # Invoices should not have work_delivery or payment_terms
        if self.document_type == 'invoice':
            if self.work_delivery or self.payment_terms:
                raise ValidationError("Invoices should not have work delivery or payment terms")
    
    def save(self, *args, **kwargs):
        # Auto-generate reference if not provided
        if not self.reference:
            self.reference = self.generate_reference()
        
        # Copy customer data if customer is linked
        if self.customer and not self.customer_name:
            self.customer_name = self.customer.name
            self.customer_location = self.customer.location
            self.customer_phone = self.customer.phone
        
        # Generate amount in words for invoices
        if self.document_type == 'invoice' and not self.amount_in_words:
            self.amount_in_words = self._generate_amount_in_words()
        
        # Only run validation if not explicitly skipped
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()  # Run validation
        
        super().save(*args, **kwargs)
    def generate_reference(self):
        """Generate unique reference number: QT-YY-MM-XXX or IN-YY-MM-XXX"""
        now = datetime.now()
        year = now.strftime('%y')
        month = now.strftime('%m')
        
        # Determine prefix
        prefix_code = "QT" if self.document_type == 'quotation' else "IN"
        prefix = f"{prefix_code}-{year}-{month}-"
        
        # Get last document of this type for this month
        last_doc = Document.objects.filter(
            document_type=self.document_type,
            reference__startswith=prefix
        ).order_by('-reference').first()
        
        if last_doc:
            try:
                last_num = int(last_doc.reference.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:03d}"
    
    @property
    def subtotal(self):
        """Calculate subtotal from all line items"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def tva_amount(self):
        """Calculate TVA/VAT amount"""
        return (self.subtotal * self.tva_rate) / Decimal('100')
    
    @property
    def total(self):
        """Calculate total including TVA"""
        return self.subtotal + self.tva_amount
    

    def _generate_amount_in_words(self):
        """Generate amount in words (English) - CORRECTED VERSION"""
        try:
            # Check if we have a primary key (saved to database)
            if not self.pk:
                print("WARNING: _generate_amount_in_words called before document has PK")
                return "Amount to be calculated"
            
            # Calculate total (this requires items to exist)
            try:
                total_amount = self.total
            except Exception as e:
                print(f"WARNING: Could not calculate total: {e}")
                return "Amount to be calculated"
            
            amount = int(total_amount)
            currency = self.currency
            
            if amount == 0:
                return f"Zero {currency}"
            
            # Simple number to words conversion
            ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
            teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 
                     'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
            tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
            thousands = ['', 'Thousand', 'Million', 'Billion']
            
            def convert_below_thousand(n):
                if n == 0:
                    return ''
                elif n < 10:
                    return ones[n]
                elif n < 20:
                    return teens[n - 10]
                elif n < 100:
                    return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
                else:
                    return ones[n // 100] + ' Hundred' + (' ' + convert_below_thousand(n % 100) if n % 100 != 0 else '')
            
            # FIXED chunking logic - properly reverse and chunk
            num_str = str(amount)[::-1]
            chunks = [num_str[i:i+3][::-1] for i in range(0, len(num_str), 3)]
            
            result = []
            for i, chunk in enumerate(chunks):
                num = int(chunk)
                if num != 0:
                    result.append(convert_below_thousand(num) + ' ' + thousands[i])
            
            words = ' '.join(reversed(result)).strip()
            return f"{words} {currency} ({amount} {currency}) excluding VAT"
        
        except Exception as e:
            print(f"ERROR in _generate_amount_in_words: {e}")
            import traceback
            traceback.print_exc()
            return "Amount to be calculated"
    def approve(self, user):
        """Approve the document"""
        if self.status == 'approved':
            raise ValidationError("Document is already approved")
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = datetime.now()
        self.save()
        
        # Create history entry
        DocumentHistory.objects.create(
            document=self,
            action='approved',
            user=user,
            old_status=self.status,
            new_status='approved',
            details=f"{self.get_document_type_display()} approved"
        )
    
    def reject(self, user):
        """Reject the document"""
        if self.status == 'rejected':
            raise ValidationError("Document is already rejected")
        
        old_status = self.status
        self.status = 'rejected'
        self.rejected_by = user
        self.rejected_at = datetime.now()
        self.save()
        
        # Create history entry
        DocumentHistory.objects.create(
            document=self,
            action='rejected',
            user=user,
            old_status=old_status,
            new_status='rejected',
            details=f"{self.get_document_type_display()} rejected"
        )
    
    def convert_to_invoice(self, user):
        """Convert quotation to invoice"""
        from django.utils import timezone
        
        # Validation
        if self.document_type != 'quotation':
            raise ValidationError("Only quotations can be converted to invoices")
        
        if self.converted_to_invoice:
            raise ValidationError(
                f"This quotation has already been converted to invoice {self.converted_to_invoice.reference}"
            )
        
        if self.status == 'rejected':
            raise ValidationError("Cannot convert a rejected quotation")
        
        # Get all items from the quotation
        source_items = list(self.items.all())
        
        # Generate reference for the invoice
        now = datetime.now()
        year = now.strftime('%y')
        month = now.strftime('%m')
        prefix = f"IN-{year}-{month}-"
        
        last_invoice = Document.objects.filter(
            document_type='invoice',
            reference__startswith=prefix
        ).order_by('-reference').first()
        
        if last_invoice:
            try:
                last_num = int(last_invoice.reference.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        invoice_reference = f"{prefix}{new_num:03d}"
        
        # Create invoice instance
        invoice = Document(
            document_type='invoice',
            reference=invoice_reference,
            date=now.date(),
            customer=self.customer,
            customer_name=self.customer_name,
            customer_location=self.customer_location,
            customer_phone=self.customer_phone,
            customer_po_ref='',
            currency=self.currency,
            tva_rate=self.tva_rate,
            status='draft',
            notes=f"Converted from quotation {self.reference}",
            footer_text=self.footer_text,
            created_by=user,
            work_delivery='',
            payment_terms='',
        )
        
        # Save invoice (bypass custom save to avoid validation issues)
        super(Document, invoice).save()
        
        # Copy all line items
        for item in source_items:
            DocumentItem.objects.create(
                document=invoice,
                item_number=item.item_number,
                description=item.description,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price
            )
        
        # Generate amount in words (now that items exist)
        try:
            invoice.amount_in_words = invoice._generate_amount_in_words()
            invoice.save(update_fields=['amount_in_words'])
        except Exception:
            # Fallback if amount generation fails
            invoice.amount_in_words = f"{int(invoice.total)} {invoice.currency} excluding VAT"
            invoice.save(update_fields=['amount_in_words'])
        
        # Update quotation status
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.converted_to_invoice = invoice
        super(Document, self).save()
        
        # Create history entries
        DocumentHistory.objects.create(
            document=self,
            action='approved',
            user=user,
            details=f"Quotation approved and converted to invoice {invoice.reference}"
        )
        
        DocumentHistory.objects.create(
            document=invoice,
            action='created',
            user=user,
            details=f"Invoice created from quotation {self.reference}"
        )
        
        return invoice

class DocumentItem(models.Model):
    """Line items for documents (both quotations and invoices)"""
    
    UNIT_CHOICES = [
        ('PC', 'PC'),
        ('Unit', 'Unit'),
        ('Hour', 'Hour'),
        ('Day', 'Day'),
        ('Month', 'Month'),
        ('Set', 'Set'),
        ('Box', 'Box'),
        ('Kg', 'Kg'),
        ('Meter', 'Meter'),
        ('Liter', 'Liter'),
    ]
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_number = models.PositiveIntegerField(
        help_text="Line item number (auto-generated)"
    )
    description = models.TextField(
        help_text="Description of the item/service"
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='PC'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price per unit"
    )
    
    class Meta:
        ordering = ['item_number']
        unique_together = ['document', 'item_number']
        indexes = [
            models.Index(fields=['document', 'item_number']),
        ]
    
    def __str__(self):
        return f"Item {self.item_number}: {self.description[:50]}"
    
    @property
    def total_price(self):
        """Calculate total price for this line item"""
        return self.quantity * self.unit_price
    
    def save(self, *args, **kwargs):
        # Auto-assign item_number if not provided
        if not self.item_number:
            last_item = DocumentItem.objects.filter(
                document=self.document
            ).aggregate(models.Max('item_number'))['item_number__max']
            
            self.item_number = (last_item + 1) if last_item else 1
        
        super().save(*args, **kwargs)


class DocumentHistory(models.Model):
    """Audit trail for document changes"""
    
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('status_changed', 'Status Changed'),
        ('converted', 'Converted to Invoice'),
    ]
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(
        blank=True,
        help_text="Additional details about the change"
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Document Histories"
        indexes = [
            models.Index(fields=['document', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.document.reference} - {self.get_action_display()} at {self.timestamp:%Y-%m-%d %H:%M}"