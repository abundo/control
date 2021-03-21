# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models, connection
from django.utils import timezone


class Device(models.Model):
    name = models.CharField(max_length=255, default="")
    manufacturer = models.CharField(max_length=255, blank=True, default="")
    model = models.CharField(max_length=255, blank=True, default="")
    comments = models.TextField(blank=True, default="")
    role = models.CharField(max_length=255, blank=True, default="")
    site_name = models.CharField(max_length=255, blank=True, default="")
    platform = models.CharField(max_length=255, blank=True, default="")
    ipv4_prefix = models.CharField(max_length=18, default="", blank=True)
    ipv6_prefix = models.CharField(max_length=43, default="", blank=True)
    enabled = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True, default="")
    alarm_timeperiod = models.CharField(max_length=255, blank=True, default="")
    alarm_destination = models.CharField(max_length=255, blank=True, default="")
    alarm_interfaces = models.BooleanField(default=False)
    connection_method = models.CharField(max_length=255, blank=True, default="")
    monitor_grafana = models.BooleanField(default=False)
    monitor_icinga = models.BooleanField(default=False)
    monitor_librenms = models.BooleanField(default=False)
    backup_oxidized = models.BooleanField(default=False)
    field_src = models.CharField(max_length=10, db_column='_src', default="", blank=True)

    class Meta:
        db_table = 'device'
    
    def __str__(self):
        return f"{self.name} | {self.role}"


class Parent(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, default=-1)
    parent = models.CharField(max_length=255, blank=True, default="")
    field_src = models.CharField(max_length=10, db_column='_src', default="", blank=True)

    class Meta:
        db_table = 'parent'

    def __str__(self):
        return self.parent


class Tag(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, default=-1)
    tag = models.CharField(max_length=255, blank=True, null=True)
    field_src = models.CharField(max_length=10, db_column='_src', default="", blank=True)

    class Meta:
        db_table = 'tag'

    def __str__(self):
        return self.tag


class Interface(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, default=-1)
    name = models.CharField(max_length=255, default="")
    role = models.CharField(max_length=255, blank=True, default="")
    ipv4_prefix = models.CharField(max_length=18, default="", blank=True)
    ipv6_prefix = models.CharField(max_length=43, default="", blank=True)
    enabled = models.BooleanField(default=False)
    field_src = models.CharField(max_length=10, db_column='_src', default="", blank=True)

    class Meta:
        db_table = 'interface'

    def __str__(self):
        return f"{self.name} | {self.role} | {self.ipv4_prefix}"


class InterfaceTag(models.Model):
    interface = models.ForeignKey(Interface, on_delete=models.CASCADE, default=-1)
    tag = models.CharField(max_length=255, blank=True, default="")
    field_src = models.CharField(max_length=10, db_column='_src', default="", blank=True)

    class Meta:
        db_table = 'interfacetag'

    def __str__(self):
        return self.tag


class Cache(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.TextField(null=False)
    name = models.CharField(max_length=255, default="", blank=True)

    class Meta:
        db_table = 'cache'

    def __str__(self):
        return f"name={self.name}, data={self.data}"


class Control(models.Model):
    sync_name = models.CharField(max_length=255, blank=True, default="") 
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'control'

    def __str__(self):
        return f"{self.sync_name} | {self.timestamp}"


class SerialField(models.IntegerField):
    def db_type(self, connection):
        return 'serial'


def get_next_log_serialid_seq():
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('log_serialid_seq')")
        result = cursor.fetchone()
        return result[0]


# Loosely based on RFC5424
class Log_Entry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    serialid = SerialField(default=get_next_log_serialid_seq, editable=False, unique=True)
    facility = models.IntegerField(null=True)
    severity = models.IntegerField(null=True)
    hostname = models.CharField(max_length=255, blank=True, default="")
    appname = models.CharField(max_length=48, blank=True, default="")
    procid = models.CharField(max_length=128, blank=True, default="")
    msgid = models.TextField(max_length=64, blank=True, default="")
    msg = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        # managed = False
        db_table = "log"
