# from django.shortcuts import render
from django.shortcuts import render, redirect

# Create your views here.
import os
# from django.http import HttpResponse
import random
import string
import requests
from .models import existJobs
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import os
import random
import string

from django.shortcuts import render
import os
import random
import string
from django.core.files.storage import FileSystemStorage
import subprocess

from django.db import connection

def create_patient_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id VARCHAR(50),
                name VARCHAR(100),
                dob VARCHAR(20),
                gender VARCHAR(10),
                history TEXT,
                jobID VARCHAR(20),
            
            )
        """)

def save_info(request):
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id', '')  
        name = request.POST.get('name', '')  
        dob = request.POST.get('dob', '')  
        gender = request.POST.get('gender', '')  
        history = request.POST.get('history', '') 
        allele_frequency = request.POST.get('allele_frequency', '') 
        panel_name = request.POST.get('panel_name', '') 
        genes = request.POST.get('genes', '') 
    

        cwd = os.getcwd()
        print('*************************cwd')
        print(cwd)

        newJobID = ''.join(random.sample(string.ascii_letters, 10))
        folder_path = os.path.join('media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, 'info.txt')
        
        log_file_path = os.path.join(folder_path, 'logFile.txt')
        with open(log_file_path, 'w') as logfile:
           pass 

        with open(file_path, 'w') as file:
            file.write(f'Subject ID: {subject_id}\n')
            file.write(f'Name: {name}\n')
            file.write(f'Date of Birth: {dob}\n')
            file.write(f'Gender: {gender}\n')
            file.write(f'History/Description: {history}\n')

            
            file.write('******************************************filter setup page\n')
            file.write(f'allele_frequency: {allele_frequency}\n')
            file.write(f'panel_name: {panel_name}\n')
            file.write(f'genes: {genes}\n')

        myfile = request.FILES.get('myfile')  

        
        
        

        if myfile:
            file_path = os.path.join(folder_path, myfile.name)
            with open(file_path, 'wb') as file:  
                for chunk in myfile.chunks():
                    file.write(chunk)
            print(file_path)#media/patient/ILZqTykfeg/22W00407_S2_gpu_HF.vcf
            print(folder_path)#media/patient/ILZqTykfeg
            uploadFile_url = file_path
            resultFile_url = folder_path + "/" + subject_id + "_ann.txt"
            newJob = existJobs.jobs.create(
            jobID=newJobID,
            subject_id=subject_id,
            name=name,
            dob=dob,
            gender=gender,
            history=history,
            uploadFile_url=uploadFile_url,
            resultFile_url=resultFile_url

            # 其他欄位也可以根據需要添加
        )
            # if file_path.endswith(".vcf"):
            #     print(uploadFile_url)
            #     print(resultFile_url)
            #     # command = ann_command + " -vcf=" + uploadFile_url + " -out=" + resultFile_url + ">" + logFile + "&"
            #     ann_command = "python3 annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
            #     print(ann_command)
            #     command = "nohup " + ann_command + ">" + log_file_path + "&"
            # else:
            #     print(uploadFile_url)
            #     print(resultFile_url)
            #     # command = ann_command + " -avinput=" + uploadFile_url + " -out=" + resultFile_url + ">" + logFile + "&"
            #     ann_command = "python3 annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
            #     print(ann_command)
            #     command = "nohup " + ann_command + ">" + log_file_path + "&"
        # if command:
        #     print("command exist")
        #     os.system(command)

        if newJob:
            # os.system(command)
            
            # os.system('nohup sh /home/cadilac/137_share/147_backup/VIP/media/test.sh&')
            ##myPID = subprocess.check_output(grep_PID, shell=True)

            grep_PID = "pgrep -fo '" + newJob.jobID + "'"
            myPID = subprocess.check_output(grep_PID, shell=True)
            myPID = int(myPID)

            existJobs.jobs.filter(jobID=newJobID).update(processID=myPID)
            existJobs.jobs.filter(jobID=newJobID).update(status="running")

            return redirect('/input/success', locals())
        else:
            return redirect('/input/failed', locals())


        
def search_page(request):
    
    return render(request, "test.html", locals())

if __name__ == "__main__":
    save_info()