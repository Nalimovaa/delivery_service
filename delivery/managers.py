from django.db import models, transaction


class CDEKTariffManager(models.Manager):

    def bulk_update_or_create(self, tariffs):
        """
        Массовое создание и обновление тарифов CDEK.

        :param tariffs: Список (или любой iterable) словарей с данными тарифов.
        """

        with transaction.atomic():
            # Пример existing:
            # {
            #     233: <CDEKTariff object>,
            #     234: <CDEKTariff object>,
            # }
            # Можно сразу existing[233] вместо CDEKTariff.objects.get(...)
            existing = {
                tariff.tariff_code: tariff
                for tariff in self.select_for_update()  # CDEKTariff.objects.select_for_update() из коробки (заблокируем строки для обновления во время транзакции)
            }

            create_objects = []  # Список объектов для создания
            update_objects = []  # Список объектов для обновления

            for tariff in tariffs:  # берем тариф из списка тарифов, полученных из API CDEK

                code = tariff["tariff_code"]  # получаем код тарифа из словаря

                if code in existing:  # Если такой тариф уже есть в БД
                    obj = existing[code]  # Получаем объект Django (<CDEKTariff object>) из existing

                    # Обновляем поля существующего объекта на основе данных из API CDEK
                    obj.tariff_name = tariff["tariff_name"]
                    obj.delivery_mode = tariff["delivery_mode"]
                    obj.delivery_mode_name = tariff["delivery_mode_name"]
                    obj.weight_min = tariff["weight_min"]
                    obj.weight_max = tariff["weight_max"]
                    obj.length_max = tariff["length_max"]
                    obj.width_max = tariff["width_max"]
                    obj.height_max = tariff["height_max"]
                    obj.is_active = True

                    update_objects.append(obj)  # Добавляем объект в список для обновления

                else:
                    create_objects.append(self.model(**tariff))  # Если такого тарифа нет в БД, создаем новый объект

            if create_objects:
                self.bulk_create(create_objects)  # Создаем новые объекты в БД одним большим sql-запросом

            if update_objects:
                self.bulk_update(  # Обновляем существующие объекты в БД одним большим sql-запросом
                    update_objects,
                    fields=[
                        "tariff_name",
                        "delivery_mode",
                        "delivery_mode_name",
                        "weight_min",
                        "weight_max",
                        "length_max",
                        "width_max",
                        "height_max",
                        "is_active",
                    ],
                )


class CDEKCityManager(models.Manager):
    """ Менеджер модели CDEKCity для массового создания и обновления населенных пунктов CDEK."""

    def bulk_update_or_create(self, cities):
        """
        Массовое создание и обновление населенных пунктов CDEK.

        :param cities: Список или любой iterable словарей с данными
            населенных пунктов.
        """

        with transaction.atomic():
            # Пример existing:
            # {
            #     44: <CDEKCity object>,
            #     121: <CDEKCity object>,
            # }
            existing = {
                city.code: city
                for city in self.select_for_update()
            }

            create_objects = []
            update_objects = []

            for city in cities:
                code = city["code"]

                if code in existing:
                    obj = existing[code]

                    # Обновляем данные населенного пункта
                    # на основе актуального ответа API CDEK.
                    obj.city_uuid = city["city_uuid"]
                    obj.city = city["city"]
                    obj.fias_guid = city["fias_guid"]
                    obj.country_code = city["country_code"]
                    obj.country = city["country"]
                    obj.region = city["region"]
                    obj.region_code = city["region_code"]
                    obj.sub_region = city["sub_region"]
                    obj.longitude = city["longitude"]
                    obj.latitude = city["latitude"]
                    obj.time_zone = city["time_zone"]
                    obj.payment_limit = city["payment_limit"]
                    obj.is_active = True

                    update_objects.append(obj)

                else:
                    create_objects.append(
                        self.model(**city)
                    )

            if create_objects:
                self.bulk_create(create_objects)

            if update_objects:
                self.bulk_update(
                    update_objects,
                    fields=[
                        "city_uuid",
                        "city",
                        "fias_guid",
                        "country_code",
                        "country",
                        "region",
                        "region_code",
                        "sub_region",
                        "longitude",
                        "latitude",
                        "time_zone",
                        "payment_limit",
                        "is_active",
                    ],
                )


class CDEKDeliveryPointManager(models.Manager):
    """
    Менеджер модели CDEKDeliveryPoint для массового создания
    и обновления пунктов выдачи/приема CDEK.
    """

    def bulk_update_or_create(self, delivery_points):
        """
        Массовое создание и обновление ПВЗ CDEK.

        :param delivery_points:
            Список или любой iterable словарей с данными ПВЗ.
        """

        with transaction.atomic():
            # Пример existing:
            # {
            #     "SML4": <CDEKDeliveryPoint object>,
            #     "KACH1": <CDEKDeliveryPoint object>,
            # }
            existing = {
                delivery_point.code: delivery_point
                for delivery_point in self.select_for_update()
            }

            create_objects = []
            update_objects = []

            for delivery_point in delivery_points:
                code = delivery_point["code"]

                if code in existing:
                    obj = existing[code]

                    # Основные данные ПВЗ
                    obj.name = delivery_point["name"]
                    obj.uuid = delivery_point["uuid"]
                    obj.address_comment = delivery_point[
                        "address_comment"
                    ]
                    obj.nearest_station = delivery_point[
                        "nearest_station"
                    ]
                    obj.nearest_metro_station = delivery_point[
                        "nearest_metro_station"
                    ]
                    obj.work_time = delivery_point["work_time"]
                    obj.email = delivery_point["email"]
                    obj.note = delivery_point["note"]
                    obj.type = delivery_point["type"]
                    obj.owner_code = delivery_point["owner_code"]

                    # Возможности ПВЗ
                    obj.take_only = delivery_point["take_only"]
                    obj.is_handout = delivery_point["is_handout"]
                    obj.is_reception = delivery_point["is_reception"]
                    obj.is_dressing_room = delivery_point[
                        "is_dressing_room"
                    ]
                    obj.is_ltl = delivery_point["is_ltl"]
                    obj.have_cashless = delivery_point[
                        "have_cashless"
                    ]
                    obj.have_cash = delivery_point["have_cash"]
                    obj.have_fast_payment_system = (
                        delivery_point["have_fast_payment_system"]
                    )
                    obj.allowed_cod = delivery_point[
                        "allowed_cod"
                    ]

                    # Вложенные данные
                    obj.office_image_list = delivery_point[
                        "office_image_list"
                    ]
                    obj.work_time_list = delivery_point[
                        "work_time_list"
                    ]
                    obj.work_time_exception_list = (
                        delivery_point["work_time_exception_list"]
                    )

                    obj.status = delivery_point["status"]

                    # Данные location
                    obj.country_code = delivery_point[
                        "country_code"
                    ]
                    obj.region_code = delivery_point[
                        "region_code"
                    ]
                    obj.region = delivery_point["region"]
                    obj.city_code = delivery_point[
                        "city_code"
                    ]
                    obj.city = delivery_point["city"]
                    obj.postal_code = delivery_point[
                        "postal_code"
                    ]
                    obj.longitude = delivery_point[
                        "longitude"
                    ]
                    obj.latitude = delivery_point[
                        "latitude"
                    ]
                    obj.address = delivery_point["address"]
                    obj.address_full = delivery_point[
                        "address_full"
                    ]
                    obj.city_uuid = delivery_point[
                        "city_uuid"
                    ]

                    # Дополнительные возможности
                    obj.ltl_acceptance_partners = (
                        delivery_point["ltl_acceptance_partners"]
                    )
                    obj.ltl_issuance_partners = (
                        delivery_point["ltl_issuance_partners"]
                    )
                    obj.fulfillment = delivery_point[
                        "fulfillment"
                    ]

                    obj.is_active = True

                    update_objects.append(obj)

                else:
                    create_objects.append(
                        self.model(**delivery_point)
                    )

            if create_objects:
                self.bulk_create(create_objects)

            if update_objects:
                self.bulk_update(
                    update_objects,
                    fields=[
                        "name",
                        "uuid",
                        "address_comment",
                        "nearest_station",
                        "nearest_metro_station",
                        "work_time",
                        "email",
                        "note",
                        "type",
                        "owner_code",
                        "take_only",
                        "is_handout",
                        "is_reception",
                        "is_dressing_room",
                        "is_ltl",
                        "have_cashless",
                        "have_cash",
                        "have_fast_payment_system",
                        "allowed_cod",
                        "office_image_list",
                        "work_time_list",
                        "work_time_exception_list",
                        "status",
                        "country_code",
                        "region_code",
                        "region",
                        "city_code",
                        "city",
                        "postal_code",
                        "longitude",
                        "latitude",
                        "address",
                        "address_full",
                        "city_uuid",
                        "ltl_acceptance_partners",
                        "ltl_issuance_partners",
                        "fulfillment",
                        "is_active",
                    ],
                )