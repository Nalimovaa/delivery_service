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