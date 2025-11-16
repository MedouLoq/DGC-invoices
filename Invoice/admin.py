from django.contrib import admin
from django.utils.html import format_html
from .models import Company, Customer, Document, DocumentItem, DocumentHistory


# ============================================================================
# INLINE ADMINS
# ============================================================================

class DocumentItemInline(admin.TabularInline):
    model = DocumentItem
    extra = 1
    fields = ['item_number', 'description', 'unit', 'quantity', 'unit_price', 'total_price']
    readonly_fields = ['total_price']
    
    def total_price(self, obj):
        if obj.pk:
            return f"{obj.total_price:,.2f}"
        return "-"


class DocumentHistoryInline(admin.TabularInline):
    model = DocumentHistory
    extra = 0
    readonly_fields = ['action', 'user', 'timestamp', 'details', 'old_status', 'new_status']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# MODEL ADMINS
# ============================================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Company Information', {
            'fields': ('name', 'address', 'city', 'country', 'phone', 'email', 'nif', 'department')
        }),
        ('Bank Information', {
            'fields': ('bank_name', 'account_number', 'bank_code')
        }),
        ('Default Settings', {
            'fields': ('default_currency', 'default_tva_rate')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one company instance
        return not Company.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deleting the company
        return False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'phone', 'email', 'total_documents', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'phone', 'location', 'tax_id']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('name', 'location', 'phone', 'email', 'address', 'tax_id', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_documents(self, obj):
        count = obj.documents.count()
        return format_html(
            '<a href="/admin/invoices/document/?customer__id__exact={}">{} documents</a>',
            obj.id, count
        )
    total_documents.short_description = 'Documents'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'document_type', 'customer_name', 'date', 
        'status', 'total_amount', 'created_by', 'created_at'
    ]
    list_filter = ['document_type', 'status', 'date', 'created_at']
    search_fields = ['reference', 'customer_name', 'customer_po_ref', 'notes']
    readonly_fields = [
        'reference', 'subtotal', 'tva_amount', 'total', 
        'created_at', 'updated_at', 'approved_by', 'approved_at',
        'rejected_by', 'rejected_at'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('document_type', 'reference', 'date', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer', 'customer_name', 'customer_location', 'customer_phone', 'customer_po_ref')
        }),
        ('Financial Information', {
            'fields': ('currency', 'tva_rate', 'subtotal', 'tva_amount', 'total')
        }),
        ('Quotation Fields', {
            'fields': ('work_delivery', 'payment_terms'),
            'classes': ('collapse',)
        }),
        ('Invoice Fields', {
            'fields': ('amount_in_words',),
            'classes': ('collapse',)
        }),
        ('Workflow', {
            'fields': ('converted_to_invoice', 'approved_by', 'approved_at', 'rejected_by', 'rejected_at')
        }),
        ('Additional Information', {
            'fields': ('notes', 'footer_text'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DocumentItemInline, DocumentHistoryInline]
    
    def total_amount(self, obj):
        return format_html(
            '<strong>{:,.2f} {}</strong>',
            obj.total, obj.currency
        )
    total_amount.short_description = 'Total'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        
        # Make reference readonly after creation
        if obj and obj.pk:
            readonly.append('document_type')
        
        return readonly


@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ['document', 'item_number', 'description_short', 'unit', 'quantity', 'unit_price', 'total_price']
    list_filter = ['unit']
    search_fields = ['document__reference', 'description']
    readonly_fields = ['total_price']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'


@admin.register(DocumentHistory)
class DocumentHistoryAdmin(admin.ModelAdmin):
    list_display = ['document', 'action', 'user', 'timestamp', 'status_change']
    list_filter = ['action', 'timestamp']
    search_fields = ['document__reference', 'user__username', 'details']
    readonly_fields = ['document', 'action', 'user', 'timestamp', 'details', 'old_status', 'new_status']
    
    def status_change(self, obj):
        if obj.old_status and obj.new_status:
            return f"{obj.old_status} → {obj.new_status}"
        return "-"
    status_change.short_description = 'Status Change'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False