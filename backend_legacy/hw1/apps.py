from django.apps import AppConfig


class Hw1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hw1'


    # def ready(self):
    #     from .views import create_patient_table
    #     create_patient_table()