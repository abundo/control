"""
app URL Configuration
"""
from django.urls import path
from . import api, device, views

urlpatterns = [
    path('report/bbe', views.report_bbe),
    path('api/netbox', api.netbox),
    path('api/device/<str:name>', api.devices),
    path('api/device', api.devices),
    path('api/device_refresh_cache/<str:name>', api.devices_refresh_cache),
    path('api/device_refresh_cache', api.devices_refresh_cache),
    path("api/log/<int:id_>", api.log),
    path("api/log/", api.log),
    path("api/", api.home),
    path("api/cmd/send/<str:cmd>", api.cmd_send),

    path('device/verify/<str:name>', device.verify),
    path('sync', views.sync),
    path('dhcpd_leases', views.dhcpd_leases),
    path('', views.home),
]
