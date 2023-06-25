import decimal
from datetime import datetime, timedelta

from django.core.mail import EmailMultiAlternatives
from django.http import Http404
from django.template.loader import get_template
from django_filters import rest_framework as filters
from num2words import num2words
from rest_framework import status, permissions, viewsets, pagination, mixins, decorators
from rest_framework.response import Response
from rest_framework.views import APIView

from Eggoz.settings import FROM_EMAIL, CURRENT_ZONE
from base import models
from base.api import serializers
from base.api.serializers import CitySerializer, UploadDataSerializer
from base.models import City, UserRetailerFilters
from base.models.UploadData import DownloadLog, ApiLog
from base.models.Video import VideoCategory, Video
from base.response import BadRequest, Created
from base.scripts.upload_cluster_data import upload_cluster_data
from base.util.convert_pdf import create_pdf_async
from custom_auth.models import UserProfile
from distributionchain.models import DistributionPersonProfile
from finance.models import FinanceProfile
from saleschain.models import SalesPersonProfile


class PaginationWithNoLimit(pagination.PageNumberPagination):
    page_size = 5000


class PaginationWithLimit(pagination.PageNumberPagination):
    page_size = 100


class PaginationWithThousandLimit(pagination.PageNumberPagination):
    page_size = 5000


class PaginationWithTenThousandLimit(pagination.PageNumberPagination):
    page_size = 10000


# class CityListView(APIView):
#     # Allow any user (authenticated or not) to access this url
#     permission_classes = (permissions.AllowAny,)
#
#     def get(self, request, format=None):
#         queryset = City.objects.all().order_by('city_name')
#         serializer = CitySerializer(queryset, many=True)
#         return Response(serializer.data)
#
#     def post(self, request, format=None):
#         serializer = CitySerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CityDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """

    def get_object(self, pk):
        try:
            return City.objects.get(pk=pk)
        except City.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        city = self.get_object(pk)
        serializer = CitySerializer(city)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        city = self.get_object(pk)
        serializer = CitySerializer(city, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        city = self.get_object(pk)
        city.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CityListView(APIView):
    # Allow any user (authenticated or not) to access this url
    permission_classes = (permissions.AllowAny,)

    def get(self, request, format=None):
        queryset = City.objects.all().order_by('city_name')
        serializer = CitySerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadClusterDataViewSet(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = UploadDataSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data.get('csv_file')
        # let's check if it is a csv file
        csv_file_name = csv_file.name
        if not csv_file_name.endswith('.csv'):
            return BadRequest({"error": "File is not valid"})
        file_response = upload_cluster_data(csv_file)
        if file_response.get("status") == "success":
            return Created(file_response)
        else:
            return BadRequest(file_response)


class ZoneViewSet(viewsets.ModelViewSet):
    """
    list:
    Get paginated list of zones

    retrieve:
    Get single zone by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.ZoneSerializer
    queryset = models.Zone.objects.all().order_by('zone_name')

    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

    @decorators.action(detail=False, methods=['post'], url_path="create_zone")
    def create_zone(self, request, *args, **kwargs):
        data = request.data

        zone_name = data.get('zone_name', None)
        if not zone_name:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "Zone name required"}]})

        job_serializer = self.serializer_class(data=data)
        job_serializer.create(data=data)
        return Created()


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get paginated list of city(should filter by zone)

    retrieve:
    Get single city by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.CitySerializer
    queryset = models.City.objects.all().order_by('city_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('zone', 'is_ecommerce')


class CityListViewSet(viewsets.ModelViewSet):
    """
    list:
    Get paginated list of city(should filter by zone)

    retrieve:
    Get single city by id
    """
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.CitySerializer
    queryset = models.City.objects.all().order_by('city_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('zone', 'is_ecommerce', 'is_visible')

    def list(self, request, *args, **kwargs):
        financePersonProfile = FinanceProfile.objects.filter(user=request.user).first()
        distributionPersonProfile = DistributionPersonProfile.objects.filter(user=request.user).first()

        salesPersonProfile = SalesPersonProfile.objects.filter(user=request.user).first()
        if financePersonProfile:
            zones = [zone.id for zone in financePersonProfile.zones.all()]
        elif salesPersonProfile:
            zones = [zone.id for zone in salesPersonProfile.zones.all()]
        elif distributionPersonProfile:
            zones = [zone.id for zone in distributionPersonProfile.zones.all()]
        else:
            zones = [1]

        queryset = self.filter_queryset(self.get_queryset()).filter(zone__in=zones, is_visible=True)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @decorators.action(detail=False, methods=['post'], url_path="create_city")
    def create_city(self, request, *args, **kwargs):
        data = request.data

        city_name = data.get('city_name')
        if not city_name:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "City name required"}]})

        state = data.get('state')
        if not state:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "State required"}]})

        country = data.get('country')
        if not country:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "Country required"}]})

        job_serializer = self.serializer_class(data=data)
        job_serializer.create(data=data)
        return Created()


class ClusterViewSet(viewsets.ModelViewSet):
    """
    list:
    Get paginated list of cluster(should filter by city)

    retrieve:
    Get single cluster by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.ClusterSerializer
    queryset = models.Cluster.objects.all().order_by('cluster_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('city', 'is_ecommerce')

    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

    @decorators.action(detail=False, methods=['post'], url_path="create_cluster")
    def create_cluster(self, request, *args, **kwargs):
        data = request.data

        cluster_name = data.get('cluster_name', None)
        if not cluster_name:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "Cluster name required"}]})

        job_serializer = self.serializer_class(data=data)
        job_serializer.create(data=data)
        return Created()


class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get paginated list of sector(should filter by cluster)

    retrieve:
    Get single sector by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.SectorSerializer
    queryset = models.Sector.objects.all().order_by('sector_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('cluster', 'is_ecommerce')


class VideoCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.VideoCategorySerializer
    queryset = VideoCategory.objects.all()


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.VideoSerializer
    queryset = Video.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('videoCategory',)


class EcommerceZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get paginated list of zones

    retrieve:
    Get single zone by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.EcommerceZoneSerializer
    queryset = models.Zone.objects.filter(is_ecommerce=True).order_by('zone_name')


class EcommerceCityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get paginated list of city(should filter by zone)

    retrieve:
    Get single city by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.CitySerializer
    queryset = models.City.objects.filter(is_ecommerce=True).order_by('city_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('zone', 'is_ecommerce')


class EcommerceSectorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
    Get paginated list of ecommerce sectors

    retrieve:
    Get single ecommerce sector by id
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.EcommerceSectorSerializer
    queryset = models.EcommerceSector.objects.filter(is_ecommerce=True).order_by('sector_name')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('city', 'is_ecommerce', 'pinCode')

    @decorators.action(detail=False, methods=['get'], url_path="service_in_pincode")
    def service_in_pincode(self, request, *args, **kwargs):
        pincode = request.GET.get('pinCode', None)
        if pincode:
            service_in_pincode = False
            queryset = self.filter_queryset(self.get_queryset())
            if queryset:
                service_in_pincode = True
            return Response({"service_in_pincode": service_in_pincode, "pinCode": pincode})
        else:
            return BadRequest({'error_type': "Validation Error",
                               'errors': [{'message': "pinCode Not Valid"}]})


class EcommerceSectorUpdateViewSet(viewsets.ModelViewSet):
    """
    list:
    Get paginated list of ecommerce sectors

    retrieve:
    Get single ecommerce sector by id
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.EcommerceSectorSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('city', 'is_ecommerce')

    @decorators.action(detail=False, methods=['post'], url_path="sector_update")
    def sector_update(self, request, *args, **kwargs):
        data = request.data
        print(data)
        sector_id = data.get('sector_id', None)
        if sector_id:
            sector = models.EcommerceSector.objects.get(id=sector_id)
        else:
            return BadRequest({'error_type': "ValidationError",
                               'errors': [{'message': "sector name invalid"}]})
        ecomm_sector_serializer = self.serializer_class(data=data)
        ecomm_sector_serializer.ecomm_update_sector(instance=sector, data=data)
        return Created()


class UserFilterViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.UserRetailerFilterSerializer
    queryset = UserRetailerFilters.objects.all().order_by('id')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('beat', 'salesPerson')

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = UserRetailerFilters.objects.all().order_by('id')
        print(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @decorators.action(detail=False, methods=['post'], url_path="send_sample_mail")
    def send_sample_mail(self, request, *args, **kwargs):
        purchase_details = []
        total_amount = 0

        purchase_detail = {
            "item_description": "10 W",
            "hsn_sac": "0407",
            "sku_type": "10",
            "quantity": 2,
            "promo_quantity": 0,
            "sku_mrp": round(decimal.Decimal(140.000), 2),
            "sku_rate": round(decimal.Decimal(105.000), 2)
        }

        purchase_detail['amount'] = round(
            purchase_detail['sku_rate'] * purchase_detail['quantity'], 2)
        purchase_details.append(purchase_detail)
        purchase_details.append(purchase_detail)
        purchase_details.append(purchase_detail)
        total_amount = round(total_amount + purchase_detail['amount'], 2)
        address = {
            "address_name": "address_name",
            "building_address": "building_address",
            "street_address": "street_address",
            "city_name": "Gurgaon",
            "locality": "Sector 49",
            "landmark": "Vipul D Block",
            "name": "Paul",
            "pinCode": "122018",
            "phone_no": "+918639420804",
            "slot": "slot Morning",
            "delivery_person": " ",
        }
        order_data = {"order_id": "OD-1234", "address": address,
                      "order_date": datetime.now(tz=CURRENT_ZONE),
                      "delivery_date": datetime.now(tz=CURRENT_ZONE) + timedelta(days=1),
                      "reference_id": "cash_free_transaction.transaction_id",
                      "mode": 'CASHFREE',
                      "order_total_amount": decimal.Decimal(200.000),
                      "order_total_in_words": num2words(decimal.Decimal(200.000)),
                      "purchase_details": purchase_details}

        html_template = get_template('invoice/order_confirmation_email.html')
        html_message = html_template.render({"request_uri": request.build_absolute_uri(),
                                             'order_data': order_data})
        name = "Order123"
        pdf = create_pdf_async('invoice/order_pdf.html', {"request_uri": request.build_absolute_uri(),
                                                          'order_data': order_data},
                               [])
        pdf_name = "invoice-%s" % name + ".pdf"

        msg = EmailMultiAlternatives(
            subject="Subscription has  been placed confirmed",
            body="Kindly find the attached Subscription Invoice Details",
            from_email=FROM_EMAIL, to=['paul.manohar@eggoz.in'])
        msg.attach_alternative(html_message, "text/html")
        msg.attach(pdf_name, pdf, 'application/pdf')

        try:
            msg.send()
        except Exception as e:
            print(e)
            pass
        return Response({"sent successfully"})

    @decorators.action(detail=False, methods=['post'], url_path="send_sample_mail_two")
    def send_sample_mail_two(self, request, *args, **kwargs):
        purchase_details = []
        total_amount = 0

        purchase_detail = {
            "item_description": "10 W",
            "hsn_sac": "0407",
            "sku_type": "10",
            "quantity": 2,
            "promo_quantity": 0,
            "sku_mrp": round(decimal.Decimal(140.000), 2),
            "sku_rate": round(decimal.Decimal(105.000), 2)
        }

        purchase_detail['amount'] = round(
            purchase_detail['sku_rate'] * purchase_detail['quantity'], 2)
        purchase_details.append(purchase_detail)
        purchase_details.append(purchase_detail)
        purchase_details.append(purchase_detail)
        total_amount = round(total_amount + purchase_detail['amount'], 2)
        address = {
            "address_name": "address_name",
            "building_address": "building_address",
            "street_address": "street_address",
            "city_name": "Gurgaon",
            "locality": "Sector 49",
            "landmark": "Vipul D Block",
            "name": "Paul",
            "pinCode": "122018",
            "phone_no": "+918639420804",
            "slot": "slot Morning",
            "delivery_person": " ",
        }
        order_data = {"order_id": "OD-1234", "address": address,
                      "order_date": datetime.now(tz=CURRENT_ZONE),
                      "delivery_date": datetime.now(tz=CURRENT_ZONE) + timedelta(days=1),
                      "reference_id": "cash_free_transaction.transaction_id",
                      "mode": 'CASHFREE',
                      "order_total_amount": decimal.Decimal(200.000),
                      "order_total_in_words": num2words(decimal.Decimal(200.000)),
                      "purchase_details": purchase_details}

        html_template = get_template('invoice/order_confirmation_email.html')
        html_message = html_template.render({"request_uri": request.build_absolute_uri(),
                                             'order_data': order_data})
        name = "Order123"
        pdf = create_pdf_async('invoice/order_pdf.html', {"request_uri": request.build_absolute_uri(),
                                                          'order_data': order_data},
                               [])
        pdf_name = "invoice-%s" % name + ".pdf"

        msg = EmailMultiAlternatives(
            subject="Subscription has  been confirmed",
            body="Kindly find the attached Subscription Invoice Details",
            from_email=FROM_EMAIL, to=['paul.manohar@eggoz.in'])
        msg.attach_alternative(html_message, "text/html")
        msg.attach(pdf_name, pdf, 'application/pdf')

        try:
            msg.send()
        except Exception as e:
            print(e)
            pass
        return Response({"sent successfully"})

    @decorators.action(detail=False, methods=['post'], url_path="save_filter")
    def save_filter(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        print(user)
        print(data)
        admin = UserProfile.objects.filter(user=user, department__name__in=['Admin']).first()
        sales_profile = UserProfile.objects.filter(user=user, department__name__in=['Sales']).first()

        if sales_profile or admin:
            if admin:
                pass
            else:
                print(data)
                salesPersonProfile = SalesPersonProfile.objects.filter(user=user).first()
                user_filter_serializer = self.get_serializer(data=data)
                user_filter_serializer.is_valid(raise_exception=True)

                urf = UserRetailerFilters.objects.filter(salesPerson=salesPersonProfile.id).first()
                if urf:
                    urf.beat = data.get('beat', urf.beat)
                    urf.commission = int(data.get('commission', urf.commission))
                    urf.retailer_status = data.get('retailer_status', urf.retailer_status)
                    urf.save()
                else:
                    user_filter_serializer.save(salesPerson=salesPersonProfile.id)

                return Created({"success": "Beat Assigned Created Successfully"})


class DownloadViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.DownloadLogSerializer
    queryset = DownloadLog.objects.all().order_by('-id')


class ApiLogViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.ApiLogSerializer
    queryset = ApiLog.objects.all().order_by('-id')


class DemandClassificationViewSet(viewsets.GenericViewSet,mixins.ListModelMixin):
    permission_classes = (permissions.AllowAny,)
    pagination_class = PaginationWithNoLimit
    serializer_class = serializers.DemandClassificationSerializer
    queryset = models.DemandClassification.objects.all()
