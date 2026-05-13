from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# ── Admin branding ────────────────────────────────────────────────────────────
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Coach Jafri PT — Admin")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Coach Jafri PT")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Coaching Dashboard")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("payments/", include("payments.urls")),
    path("memberships/", include("memberships.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
