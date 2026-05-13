"""
Admin site branding — imported in AppConfig.ready() via gymfit_project/__init__.py
"""
from django.contrib import admin


def configure_admin():
    admin.site.site_header = "Coach Jafri PT — Admin"
    admin.site.site_title = "Coach Jafri PT"
    admin.site.index_title = "Coaching Dashboard"
