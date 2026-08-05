# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models



class existJobs(models.Model):
    jobID = models.CharField(max_length=20)
    subject_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    dob = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    history = models.TextField(blank=True)
    uploadFile_url = models.URLField(blank=True)
    resultFile_url = models.URLField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    processID = models.CharField(max_length=20, default='')  # 提供默认值
    status = models.CharField(max_length=20,default='pending')

    
    jobs = models.Manager()



