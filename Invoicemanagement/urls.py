# project/urls.py (Main project URLs)

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Redirect root to dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    
    # App URLs
    path('', include('Invoice.urls')),  # Adjust 'invoices' to your app name
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = "DGC Invoice Management"
admin.site.site_title = "DGC Admin"
admin.site.index_title = "Welcome to DGC Invoice Management System"