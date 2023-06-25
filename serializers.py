from rest_framework import serializers

from base.models import City, Zone, Cluster, Sector, EcommerceSector, UserRetailerFilters, DemandClassification
from base.models.UploadData import DownloadLog, ApiLog
from base.models.Video import VideoCategory, VideoTag, Video


class ZoneSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Zone
        fields = ('id', 'zone_name')

    def create(self, data):
        zone_name = data.get('zone_name')
        is_ecommerce = data.get('is_ecommerce', False)

        obj = Zone.objects.create(zone_name=zone_name, is_ecommerce=is_ecommerce)
        obj.save()
        return obj


class DownloadLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = DownloadLog
        fields = '__all__'


class ApiLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ApiLog
        fields = '__all__'


class EcommerceZoneSerializer(serializers.ModelSerializer):
    cities = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = ('id', 'zone_name', 'cities', 'zone_image')

    def get_cities(self,obj):
        cities = obj.cities.filter(is_ecommerce=True)
        return EcommerceCitySerializer(cities,many=True).data


class EcommerceCitySerializer(serializers.ModelSerializer):
    ecommerceSectors = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('id', 'city_name', 'state', 'country','ecommerceSectors')

    def get_ecommerceSectors(self,obj):
        ecommerceSectors = obj.ecommerceSectors.filter(is_ecommerce=True)
        return EcommerceSectorSerializer(ecommerceSectors,many=True).data


class EcommerceSectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = EcommerceSector
        fields = ('id', 'sector_name', 'city', 'cluster', 'distributor')

    def ecomm_update_sector(self, instance, data):
        sector_name = data.get('sector_name', None)
        distributor = data.get('distributor', None)
        if distributor:
            instance.distributor_id = distributor
        if sector_name:
            instance.sector_name = sector_name
        instance.save()
        return instance


class CitySerializer(serializers.ModelSerializer):

    class Meta:
        model = City
        fields = ('id', 'city_name', 'state', 'country', 'zone')

    def create(self, data):
        city_name = data.get('city_name')
        state = data.get('state')
        country = data.get('country')
        city_string = data.get('city_string', 'G')
        ecomm_city_string = data.get('ecomm_city_string', 'GGN')
        zone = data.get('zone', None)
        is_ecommerce = data.get('is_ecommerce', False)
        is_visible = data.get('is_visible', True)

        obj = City.objects.create(city_name=city_name, state=state, country=country,
                                    city_string=city_string, ecomm_city_string=ecomm_city_string,
                                    zone_id=zone, is_ecommerce=is_ecommerce, is_visible=is_visible)
        obj.save()
        return obj


class ClusterSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Cluster
        fields = ('id', 'cluster_name')

    def create(self, data):
        cluster_name = data.get('cluster_name')
        city = data.get('city', None)
        is_ecommerce = data.get('is_ecommerce', False)

        obj = Zone.objects.create(cluster_name=cluster_name, city_id=city,
                                    is_ecommerce=is_ecommerce)
        obj.save()
        return obj


class SectorSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Sector
        fields = ('id', 'sector_name')


class UploadDataSerializer(serializers.Serializer):
    csv_file = serializers.FileField(required=True)


class UploadDataZoneSerializer(serializers.Serializer):
    csv_file = serializers.FileField(required=True)
    zone = serializers.IntegerField(required=True)


class UploadDueDataSerializer(serializers.Serializer):
    cities = serializers.ListField(required=True)
    date = serializers.CharField(required=True)

class UploadCitiesSerializer(serializers.Serializer):
    cities = serializers.ListField(required=True)


class UploadAmountsSerializer(serializers.Serializer):
    salesPersonId = serializers.ListField(required=True)
    minOrderId = serializers.IntegerField(required=True)


class VideoCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = VideoCategory
        fields = '__all__'

class VideoTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = VideoTag
        fields = '__all__'

class VideoSerializer(serializers.ModelSerializer):
    video_tags = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = '__all__'

    def get_video_tags(self,obj):
        video_tags = obj.video_tags.all()
        return VideoTagSerializer(video_tags,many=True).data


class UserRetailerFilterSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRetailerFilters
        fields = '__all__'


class DemandClassificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = DemandClassification
        fields = '__all__'
