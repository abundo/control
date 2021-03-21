from django.contrib import admin

# Register your models here.
from .models import Device, InterfaceTag, Interface, Parent, Tag

admin.site.register(Device)
admin.site.register(Interface)
admin.site.register(InterfaceTag)
admin.site.register(Parent)
admin.site.register(Tag)
