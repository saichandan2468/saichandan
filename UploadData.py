from django.db import models
from uuid_upload_path import upload_to

from base import UPLOAD_TYPE_CHOICES
from base.models.ModelWithMetaData import ModelWithMetadata
from base.util.json_serializer import CustomJsonEncoder
from custom_auth.models import User
from django.db.models import JSONField


# class UploadData(models.Model):
#     file = models.FileField(upload_to=upload_to)
#     user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="uploadFiles")
#     created_at = models.DateTimeField(auto_now_add=True)
#     upload_type = models.CharField(max_length=50, choices=UPLOAD_TYPE_CHOICES)


class DownloadLog(ModelWithMetadata):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="downloadUser")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True)


# TODO to be used from frontend
class ApiLog(ModelWithMetadata):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="apiUser")
    response = JSONField(blank=True, null=True, default=dict, encoder=CustomJsonEncoder)
    content_length = models.BigIntegerField(default=0)
    api_type=models.CharField(default="", max_length=250)
    status = models.CharField(default="", max_length=250)
    ip=models.CharField(default="", max_length=250)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True)

