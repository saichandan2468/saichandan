import datetime
from typing import Any

from django.db import models
from django.db.models import JSONField, Q

from base.models import TimeStampedModel
from base.permissions import ProductPermissions
from base.util.json_serializer import CustomJsonEncoder


class ModelWithMetadata(models.Model):
    private_metadata = JSONField(
        blank=True, null=True, default=dict, encoder=CustomJsonEncoder
    )
    metadata = JSONField(blank=True, null=True, default=dict, encoder=CustomJsonEncoder)

    class Meta:
        abstract = True

    def get_value_from_private_metadata(self, key: str, default: Any = None) -> Any:
        return self.private_metadata.get(key, default)

    def store_value_in_private_metadata(self, items: dict):
        if not self.private_metadata:
            self.private_metadata = {}
        self.private_metadata.update(items)

    def clear_private_metadata(self):
        self.private_metadata = {}

    def delete_value_from_private_metadata(self, key: str):
        if key in self.private_metadata:
            del self.private_metadata[key]

    def get_value_from_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def store_value_in_metadata(self, items: dict):
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(items)

    def clear_metadata(self):
        self.metadata = {}

    def delete_value_from_metadata(self, key: str):
        if key in self.metadata:
            del self.metadata[key]


# class PublishedQuerySet(models.QuerySet):
#     def published(self):
#         today = datetime.date.today()
#         return self.filter(
#             Q(publication_date__lte=today) | Q(publication_date__isnull=True),
#             is_published=True,
#         )
#
#     @staticmethod
#     def user_has_access_to_all(user):
#         return user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS)
#
#     def visible_to_user(self, user):
#         if self.user_has_access_to_all(user):
#             return self.all()
#         return self.published()
#
#
# class PublishableModel(models.Model):
#     publication_date = models.DateField(blank=True, null=True)
#     is_published = models.BooleanField(default=False)
#
#     objects = PublishedQuerySet.as_manager()
#
#     class Meta:
#         abstract = True
#
#     @property
#     def is_visible(self):
#         return self.is_published and (
#             self.publication_date is None
#             or self.publication_date <= datetime.date.today()
#         )
#
#
# class ExpiredQuerySet(models.QuerySet):
#     def expired(self):
#         today = datetime.date.today()
#         return self.filter(
#             Q(expiry_date__lte=today) | Q(expiry_date__isnull=True),
#             is_expired=True,
#         )
#
#     @staticmethod
#     def user_has_access_to_all(user):
#         return user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS)
#
#     def visible_to_user(self, user):
#         if self.user_has_access_to_all(user):
#             return self.all()
#         return self.expired()
#
#
# class ExpirableModel(TimeStampedModel):
#     start_date = models.DateField(blank=True, null=True)
#     expiry_date = models.DateField(blank=True, null=True)
#     is_expired = models.BooleanField(default=False)
#
#     objects = ExpiredQuerySet.as_manager()
#
#     class Meta:
#         abstract = True
#
#     @property
#     def is_visible(self):
#         return self.is_expired and (
#             self.expiry_date is None
#             or self.expiry_date <= datetime.date.today()
#         )