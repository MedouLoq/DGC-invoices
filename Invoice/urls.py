from django.urls import path
from . import views

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ============================================================================
    # DASHBOARD
    # ============================================================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ============================================================================
    # QUOTATIONS
    # ============================================================================
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
    path('quotations/create/', views.document_create, {'document_type': 'quotation'}, name='quotation_create'),
    path('quotations/<int:pk>/convert/', views.quotation_convert_to_invoice, name='quotation_convert'),
    
    # ============================================================================
    # INVOICES
    # ============================================================================
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.document_create, {'document_type': 'invoice'}, name='invoice_create'),
    
    # ============================================================================
    # DOCUMENTS (COMMON)
    # ============================================================================
    path('documents/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('documents/<int:pk>/edit/', views.document_edit, name='document_edit'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('documents/<int:pk>/approve/', views.document_approve, name='document_approve'),
    path('documents/<int:pk>/reject/', views.document_reject, name='document_reject'),
    path('documents/<int:pk>/status/', views.document_change_status, name='document_change_status'),
    path('documents/<int:pk>/preview/', views.document_preview, name='document_preview'),
    path('documents/<int:pk>/pdf/', views.document_pdf, name='document_pdf'),
    
    # ============================================================================
    # CUSTOMERS
    # ============================================================================
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/data/', views.get_customer_data, name='get_customer_data'),
    
    # ============================================================================
    # SETTINGS
    # ============================================================================
    path('settings/company/', views.company_settings, name='company_settings'),
]