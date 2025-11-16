from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Document, DocumentItem, Customer, Company


class CustomUserCreationForm(UserCreationForm):
    """Enhanced user registration form"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Enhanced login form"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class DocumentForm(forms.ModelForm):
    """Main document form for both quotations and invoices"""
    
    class Meta:
        model = Document
        fields = [
            'document_type', 'date', 'status', 'currency', 'tva_rate',
            'customer', 'customer_name', 'customer_location', 
            'customer_phone', 'customer_po_ref',
            'work_delivery', 'payment_terms',
            'notes', 'footer_text'
        ]
        widgets = {
            'document_type': forms.HiddenInput(),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tva_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'customer': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_customer',
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer name',
                'required': True
            }),
            'customer_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer location (optional)'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+222 XX XX XX XX'
            }),
            'customer_po_ref': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer PO Reference (for invoices)',
                'id': 'id_customer_po_ref'
            }),
            'work_delivery': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., Immediately after confirmation - subjected to prior order',
                'id': 'id_work_delivery'
            }),
            'payment_terms': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., 100% After work completion',
                'id': 'id_payment_terms'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Internal notes (not shown on document)'
            }),
            'footer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional text for document footer'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make customer optional
        self.fields['customer'].required = False
        self.fields['customer'].empty_label = "--- Select Existing Customer (Optional) ---"
        
        # Customer name is required
        self.fields['customer_name'].required = True
        
        # Document type should not be required in the form (it comes from URL)
        self.fields['document_type'].required = False
        
        # Make quotation fields not required (will be validated in clean method)
        self.fields['work_delivery'].required = False
        self.fields['payment_terms'].required = False
        self.fields['customer_po_ref'].required = False
        
        # Set initial values from company defaults
        if not self.instance.pk:
            company = Company.get_company()
            self.fields['currency'].initial = company.default_currency
            self.fields['tva_rate'].initial = company.default_tva_rate
    
    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        
        # For quotations: clear invoice-specific fields
        if document_type == 'quotation':
            cleaned_data['customer_po_ref'] = ''
        
        # For invoices: clear quotation-specific fields
        if document_type == 'invoice':
            cleaned_data['work_delivery'] = ''
            cleaned_data['payment_terms'] = ''
        
        return cleaned_data
class DocumentItemForm(forms.ModelForm):
    """Individual document item form"""
    
    class Meta:
        model = DocumentItem
        fields = ['item_number', 'description', 'unit', 'quantity', 'unit_price']
        widgets = {
            'item_number': forms.HiddenInput(),  # Changed to HiddenInput
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Item description',
                'required': True
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select form-select-sm',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm quantity-input',
                'min': '1',
                'value': '1',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm unit-price-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
        }


# Create the formset for document items
DocumentItemFormSet = inlineformset_factory(
    Document,
    DocumentItem,
    form=DocumentItemForm,
    extra=0,  # Changed from 6 to 0 since we're creating rows in JavaScript
    min_num=1,  # Require at least 1 item
    validate_min=True,
    can_delete=True,
)


class CustomerForm(forms.ModelForm):
    """Customer creation/edit form"""
    
    class Meta:
        model = Customer
        fields = ['name', 'location', 'phone', 'email', 'address', 'tax_id']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer name',
                'required': True
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location/City'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+222 XX XX XX XX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'customer@example.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full address'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NIF / Tax ID'
            }),
        }


class CompanyForm(forms.ModelForm):
    """Company settings form"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'address', 'city', 'country', 'phone', 'email', 'nif',
            'bank_name', 'account_number', 'bank_code', 'department',
            'default_currency', 'default_tva_rate'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nif': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_code': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'default_currency': forms.Select(attrs={'class': 'form-select'}),
            'default_tva_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


class DocumentFilterForm(forms.Form):
    """Form for filtering documents in dashboard"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + list(Document.STATUS_CHOICES)
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by reference, customer...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )