from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Sum, Count
from datetime import datetime
import json

from .models import Document, DocumentItem, Customer, DocumentHistory, Company
from .forms import (
    DocumentForm, DocumentItemFormSet, CustomerForm, CompanyForm,
    CustomUserCreationForm, CustomAuthenticationForm
)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'invoices/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'invoices/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard(request):
    """Main dashboard with overview"""
    # Get statistics - REMOVED created_by filter to show all documents
    total_quotations = Document.objects.filter(
        document_type='quotation'
    ).count()
    
    total_invoices = Document.objects.filter(
        document_type='invoice'
    ).count()
    
    pending_quotations = Document.objects.filter(
        document_type='quotation',
        status='pending'
    ).count()
    
    approved_invoices = Document.objects.filter(
        document_type='invoice',
        status__in=['approved', 'paid']
    ).count()
    
    # Recent documents - show all, not just current user's
    recent_documents = Document.objects.all().select_related(
        'customer', 'approved_by'
    ).order_by('-created_at')[:10]
    
    # Total revenue (approved invoices) - all users
    from django.db.models import Sum, F
    total_revenue = Document.objects.filter(
        document_type='invoice',
        status__in=['approved', 'paid']
    ).aggregate(
        total=Sum(F('items__unit_price') * F('items__quantity'))
    )['total'] or 0
    
    context = {
        'stats': {
            'total_quotations': total_quotations,
            'total_invoices': total_invoices,
            'pending_quotations': pending_quotations,
            'approved_invoices': approved_invoices,
            'total_revenue': total_revenue,
        },
        'recent_documents': recent_documents,
    }
    
    return render(request, 'invoices/dashboard.html', context)


class QuotationListView(LoginRequiredMixin, ListView):
    """List all quotations - for all users"""
    model = Document
    template_name = 'invoices/quotation_list.html'
    context_object_name = 'quotations'
    paginate_by = 20
    
    def get_queryset(self):
        # REMOVED created_by filter - show all quotations
        queryset = Document.objects.filter(
            document_type='quotation'
        ).select_related(
            'customer', 'created_by', 'approved_by', 'converted_to_invoice'
        ).prefetch_related('items')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(customer_name__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Stats for all quotations, not just current user
        all_quotations = Document.objects.filter(document_type='quotation')
        context['stats'] = {
            'total': all_quotations.count(),
            'draft': all_quotations.filter(status='draft').count(),
            'pending': all_quotations.filter(status='pending').count(),
            'approved': all_quotations.filter(status='approved').count(),
            'rejected': all_quotations.filter(status='rejected').count(),
        }
        
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class InvoiceListView(LoginRequiredMixin, ListView):
    """List all invoices - for all users"""
    model = Document
    template_name = 'invoices/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        # REMOVED created_by filter - show all invoices
        queryset = Document.objects.filter(
            document_type='invoice'
        ).select_related(
            'customer', 'created_by', 'approved_by'
        ).prefetch_related('items')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_po_ref__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Stats for all invoices, not just current user
        all_invoices = Document.objects.filter(document_type='invoice')
        context['stats'] = {
            'total': all_invoices.count(),
            'draft': all_invoices.filter(status='draft').count(),
            'pending': all_invoices.filter(status='pending').count(),
            'approved': all_invoices.filter(status='approved').count(),
            'paid': all_invoices.filter(status='paid').count(),
        }
        
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context

# ============================================================================
# DOCUMENT DETAIL VIEWS
# ============================================================================

class DocumentDetailView(LoginRequiredMixin, DetailView):
    """View document details"""
    model = Document
    template_name = 'invoices/document_detail.html'
    context_object_name = 'document'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = Company.get_company()
        context['history'] = self.object.history.select_related('user').order_by('-timestamp')[:20]
        return context


# ============================================================================
# DOCUMENT CREATE/EDIT VIEWS
# ============================================================================

@login_required
def document_create(request, document_type='quotation'):
    """Create new quotation or invoice"""
    
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        formset = DocumentItemFormSet(request.POST)
        
        # Debug: Print POST data
        print(f"POST data: {request.POST}")
        print(f"Document type: {document_type}")
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Save document
                    document = form.save(commit=False)
                    document.created_by = request.user
                    document.document_type = document_type  # Set from URL parameter
                    
                    # Debug: Check if quotation fields are present
                    if document_type == 'quotation':
                        print(f"Work Delivery: {document.work_delivery}")
                        print(f"Payment Terms: {document.payment_terms}")
                    
                    document.save()
                    
                    # Save items
                    items = formset.save(commit=False)
                    for idx, item in enumerate(items, start=1):
                        item.document = document
                        item.item_number = idx
                        item.save()
                    
                    # Delete removed items
                    for item in formset.deleted_objects:
                        item.delete()
                    
                    # Create history entry
                    DocumentHistory.objects.create(
                        document=document,
                        action='created',
                        user=request.user,
                        details=f"{document.get_document_type_display()} created"
                    )
                    
                    messages.success(
                        request,
                        f'{document.get_document_type_display()} {document.reference} created successfully!'
                    )
                    return redirect('document_detail', pk=document.pk)
                    
            except Exception as e:
                import traceback
                print(f"Error creating document: {str(e)}")
                print(traceback.format_exc())
                messages.error(request, f'Error creating document: {str(e)}')
        else:
            # Show validation errors
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")
            
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    messages.error(request, error)
    else:
        # GET request - set initial document_type
        initial_data = {'document_type': document_type}
        form = DocumentForm(initial=initial_data)
        formset = DocumentItemFormSet(queryset=DocumentItem.objects.none())
    
    doc_name = 'Quotation' if document_type == 'quotation' else 'Invoice'
    
    return render(request, 'invoices/document_form.html', {
        'form': form,
        'formset': formset,
        'action': 'Create',
        'document_type': document_type,
        'doc_name': doc_name,
        'is_edit': False,  # Flag to tell template we're creating
    })


@login_required
def document_edit(request, pk):
    """Edit existing document"""
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow editing drafts or if user is staff
    if document.status not in ['draft', 'pending'] and not request.user.is_staff:
        messages.error(request, 'You cannot edit this document.')
        return redirect('document_detail', pk=pk)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        formset = DocumentItemFormSet(request.POST, instance=document)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Don't change document_type on edit
                    doc = form.save(commit=False)
                    doc.document_type = document.document_type  # Keep original type
                    doc.save()
                    
                    # Save items with correct numbering
                    items = formset.save(commit=False)
                    for idx, item in enumerate(items, start=1):
                        item.document = doc
                        item.item_number = idx
                        item.save()
                    
                    # Delete removed items
                    for item in formset.deleted_objects:
                        item.delete()
                    
                    # Create history entry
                    DocumentHistory.objects.create(
                        document=doc,
                        action='updated',
                        user=request.user,
                        details='Document updated'
                    )
                    
                    messages.success(request, 'Document updated successfully!')
                    return redirect('document_detail', pk=doc.pk)
                    
            except Exception as e:
                import traceback
                print(f"Error updating document: {str(e)}")
                print(traceback.format_exc())
                messages.error(request, f'Error updating document: {str(e)}')
        else:
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # GET request - load existing data
        form = DocumentForm(instance=document)
        formset = DocumentItemFormSet(instance=document)
    
    return render(request, 'invoices/document_form.html', {
        'form': form,
        'formset': formset,
        'document': document,
        'action': 'Edit',
        'document_type': document.document_type,  # Important! Pass this for template conditionals
        'doc_name': document.get_document_type_display(),
        'is_edit': True,  # Flag to tell template we're editing
    })

# ============================================================================
# DOCUMENT ACTIONS
# ============================================================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def document_approve(request, pk):
    """Approve a document (staff only)"""
    document = get_object_or_404(Document, pk=pk)
    
    try:
        document.approve(request.user)
        messages.success(request, f'{document.get_document_type_display()} {document.reference} approved!')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('document_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_staff)
def document_reject(request, pk):
    """Reject a document (staff only)"""
    document = get_object_or_404(Document, pk=pk)
    
    try:
        document.reject(request.user)
        messages.warning(request, f'{document.get_document_type_display()} {document.reference} rejected.')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('document_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_staff)
def quotation_convert_to_invoice(request, pk):
    """Convert quotation to invoice - DEBUG VERSION"""
    import traceback
    
    quotation = get_object_or_404(Document, pk=pk, document_type='quotation')
    
    print("\n" + "=" * 80)
    print(f"VIEW: Starting conversion process for quotation {quotation.reference}")
    print(f"      User: {request.user.username}")
    print(f"      Quotation PK: {quotation.pk}")
    print(f"      Items count: {quotation.items.count()}")
    print("=" * 80 + "\n")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                print("VIEW: Calling convert_to_invoice()...")
                invoice = quotation.convert_to_invoice(request.user)
                print(f"VIEW: Conversion successful! Invoice {invoice.reference} created")
                
                messages.success(
                    request,
                    f'Quotation {quotation.reference} converted to invoice {invoice.reference}!'
                )
                return redirect('document_detail', pk=invoice.pk)
                
        except Exception as e:
            print("\n" + "!" * 80)
            print("VIEW: ERROR OCCURRED")
            print("!" * 80)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("\nFull traceback:")
            traceback.print_exc()
            print("!" * 80 + "\n")
            
            messages.error(request, f'Error converting quotation: {str(e)}')
            return redirect('document_detail', pk=pk)
    
    return render(request, 'invoices/quotation_convert_confirm.html', {
        'quotation': quotation
    })

@login_required
def document_change_status(request, pk):
    """Change document status (staff only for certain statuses)"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # Staff-only statuses
        protected_statuses = ['approved', 'paid']
        if new_status in protected_statuses and not request.user.is_staff:
            messages.error(request, 'You do not have permission to set this status.')
            return redirect('document_detail', pk=pk)
        
        if new_status in dict(Document.STATUS_CHOICES):
            old_status = document.status
            document.status = new_status
            document.save()
            
            DocumentHistory.objects.create(
                document=document,
                action='status_changed',
                user=request.user,
                old_status=old_status,
                new_status=new_status,
                details=f'Status changed from {old_status} to {new_status}'
            )
            
            messages.success(request, 'Status updated successfully!')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('document_detail', pk=pk)


@login_required
def document_delete(request, pk):
    """Delete a document (drafts or staff only)"""
    document = get_object_or_404(Document, pk=pk)
    
    if document.status != 'draft' and not request.user.is_staff:
        messages.error(request, 'You cannot delete this document.')
        return redirect('document_detail', pk=pk)
    
    if request.method == 'POST':
        reference = document.reference
        doc_type = document.document_type
        document.delete()
        messages.success(request, f'Document {reference} deleted successfully!')
        
        if doc_type == 'quotation':
            return redirect('quotation_list')
        else:
            return redirect('invoice_list')
    
    return render(request, 'invoices/document_confirm_delete.html', {
        'document': document
    })


# ============================================================================
# PDF GENERATION
# ============================================================================

@login_required
def document_preview(request, pk):
    """Preview document in print-ready format"""
    document = get_object_or_404(Document, pk=pk)
    company = Company.get_company()
    
    template = 'invoices/document_preview.html'
    
    return render(request, template, {
        'document': document,
        'company': company,
    })


@login_required
def document_pdf(request, pk):
    """Generate and download PDF directly using xhtml2pdf"""
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    from django.conf import settings
    import os
    
    document = get_object_or_404(Document, pk=pk)
    company = Company.get_company()
    
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        
        # Get absolute paths for images (xhtml2pdf needs file:// paths on Windows)
        static_root = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT
        
        # Build absolute file paths for images
        logo_path = os.path.join(static_root, 'invoices', 'images', 'logo.png')
        stamp_path = os.path.join(static_root, 'invoices', 'images', 'company-stamp.png')
        
        # Convert to file:// URI format for xhtml2pdf on Windows
        logo_uri = f"file:///{logo_path.replace(os.sep, '/')}"
        stamp_uri = f"file:///{stamp_path.replace(os.sep, '/')}"
        
        # Render the PDF-specific template
        html_string = render_to_string('invoices/document_pdf.html', {
            'document': document,
            'company': company,
            'logo_path': logo_uri,
            'stamp_path': stamp_uri,
        })
        
        # Create PDF
        result = BytesIO()
        
        # Link callback to handle static files
        def link_callback(uri, rel):
            """Convert URIs to absolute system paths for xhtml2pdf"""
            if uri.startswith('file:///'):
                return uri.replace('file:///', '')
            
            # Handle static files
            if uri.startswith(settings.STATIC_URL):
                path = uri.replace(settings.STATIC_URL, '')
                return os.path.join(static_root, path)
            
            return uri
        
        pdf = pisa.pisaDocument(
            BytesIO(html_string.encode("UTF-8")), 
            result,
            encoding='UTF-8',
            link_callback=link_callback
        )
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"{document.reference}-{document.customer_name}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            messages.error(request, 'Error generating PDF. Please try the print option.')
            return redirect('document_preview', pk=pk)
            
    except ImportError:
        messages.info(request, 'PDF library not installed. Use the Print button to save as PDF.')
        return redirect('document_preview', pk=pk)
    except Exception as e:
        import traceback
        print(f"PDF Error: {str(e)}")
        traceback.print_exc()
        messages.error(request, f'Error: {str(e)}')
        return redirect('document_preview', pk=pk)



# ============================================================================
# CUSTOMER VIEWS
# ============================================================================

class CustomerListView(LoginRequiredMixin, ListView):
    """List all customers"""
    model = Customer
    template_name = 'invoices/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Customer.objects.filter(is_active=True)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset.order_by('name')


@login_required
def customer_create(request):
    """Create new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.name}" created successfully!')
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'customer': {
                        'id': customer.id,
                        'name': customer.name,
                        'location': customer.location,
                        'phone': customer.phone,
                    }
                })
            
            return redirect('customer_list')
    else:
        form = CustomerForm()
    
    return render(request, 'invoices/customer_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def customer_edit(request, pk):
    """Edit existing customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'invoices/customer_form.html', {
        'form': form,
        'customer': customer,
        'action': 'Edit',
    })


@login_required
def customer_detail(request, pk):
    """View customer details"""
    customer = get_object_or_404(Customer, pk=pk)
    documents = Document.objects.filter(customer=customer).order_by('-date')[:20]
    
    return render(request, 'invoices/customer_detail.html', {
        'customer': customer,
        'documents': documents,
    })


# ============================================================================
# COMPANY SETTINGS
# ============================================================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def company_settings(request):
    """Edit company settings (staff only)"""
    company = Company.get_company()
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company settings updated successfully!')
            return redirect('company_settings')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'invoices/company_settings.html', {
        'form': form,
        'company': company,
    })


# ============================================================================
# AJAX VIEWS
# ============================================================================

@login_required
def get_customer_data(request, pk):
    """Get customer data for AJAX requests"""
    customer = get_object_or_404(Customer, pk=pk)
    
    return JsonResponse({
        'name': customer.name,
        'location': customer.location,
        'phone': customer.phone,
        'email': customer.email,
    })