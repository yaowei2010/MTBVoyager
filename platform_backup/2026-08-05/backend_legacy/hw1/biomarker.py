import os
import pandas as pd
from SigProfilerAssignment import Analyzer as Analyze
import matplotlib.pyplot as plt
def extract_DP_and_VF(tmp):
    #print(tmp)
    tmp_content=tmp['Otherinfo13'].split(':')
    tmp_header=tmp['Otherinfo12'].split(':')
    tmp_dict = {key: val for key, val in zip(tmp_header, tmp_content)}
    return int(tmp_dict['DP']), float(tmp_dict['VF'])
def variant_type(tmp):
    if((tmp['Ref']=='-') | (tmp['Alt']=='-')):
        return('INDEL')
    elif((tmp['Ref'] in ['A','T','C','G']) & (tmp['Alt'] in ['A','T','C','G'])):
        return('SNP')
    else:
        return('MNP')
    


def mutation_signature(request):
    if request.method == 'POST':
        #data = json.loads(request.body.decode('utf-8'))
        #newjobID = data.get('newjobid', '')
        newjobid='WGUIvPqaMA'
        folder_path = f"/miRTI/media/patient/{newjobid}"
        vcf_files = [file for  file in os.listdir(folder_path) if file.endswith(".vcf")]
        mut_filestore = f"miRTI/media/patient/{newjobid}/mutSig"
        if mut_filestore:
            activities_path = f"{mut_filestore}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"


            with open(activities_path, 'r') as activities_file:
                activities_content = activities_file.readlines()

            activities_data = []
            headers = activities_content[0].strip().split('\t')
            for line in activities_content[1:]:
                values = line.strip().split('\t')
                activities_data.append(dict(zip(headers, values)))
            

            try:
                response_data = {
                    'activities': activities_data,
                    'pie_chart_url': f"/media/patient/{newjobid}/mutSig/pie_chart.pdf",
                }
                return JsonResponse(response_data, safe=False)
            except Exception as e:
                error_response = {'error': str(e)}
                return JsonResponse(error_response, status=500)


        if vcf_files:
            print(f"找到 VCF 檔案: {vcf_files}")

                # 遍歷每個找到的 .vcf 檔案
            for vcf_file in vcf_files:
                uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

                    # 使用 os.path.basename 解析出檔案名稱
                file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
                file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main
                new_file_name = f"{file_name_without_ext}_vep_annovar_merge.csv"
                new_file_name1=f"{file_name_without_ext}_vep_annovar_merge1.csv"
                    # 打印相關訊息
                print(f'file_name : {file_name}')
                print(f'file_name_withouttxt: {file_name_without_ext}')
                print(f'uploadFile_target: {new_file_name}')
                print('---------------------VEP start-------------')
            else:
                print("該資料夾中沒有 .vcf 檔案")

        test_variants = pd.read_csv(f'/miRTI/media/patient/{newjobid}/{file_name_without_ext}_annovar_final.txt', sep="\t")
        if 'DP' in test_variants.columns and 'VAF' in test_variants.columns:
            print("Columns 'DP' and 'VAF' already exist.")
        else:

            test_variants[['DP', 'VAF']] = test_variants.apply(lambda x: pd.Series(extract_DP_and_VF(x)), axis=1)


        filter_gnomad=test_variants['AF'].apply(lambda x: -1 if x=='.' else float(x))<0.01
        filter_1000G=test_variants['1000g2015aug_all'].apply(lambda x: -1 if x=='.' else float(x))<0.01
        filter_VAF=test_variants['VAF']>=0
        filter_DP=test_variants['DP']>=0


        filtered_variant=test_variants[filter_gnomad & filter_1000G & filter_VAF & filter_DP]
        print(filtered_variant[['Chr', 'Start', 'Ref', 'Alt']])
        print(filtered_variant.shape)  

        filtered_variant['variant_type']=filtered_variant.apply(lambda x: variant_type(x),axis=1)
        filtered_variant['variant_type'].value_counts()

        aa=filtered_variant[['Chr','Start','Ref','Alt']]
        aa['sample']='sample'

        # result_path=r"C:\Users\user\Desktop\林醫師VCF團隊\20241223task\sigProfilerAssignment\sigProfilerAssignment\data\22C00022_TSO500\mutSig"
        result_path=f'/miRTI/media/patient/{newjobid}/mutSig'


        if not os.path.exists(result_path):
            os.mkdir(result_path)
        aa[['Chr','Start','sample','Ref','Alt']].to_csv(f"{result_path}/filtered.vcf",sep='\t',index=None,header=None)

        Analyze.cosmic_fit(samples=result_path, 
                        output=f"{result_path}/Assignment",
                        input_type="vcf",
                        context_type="96",
                        genome_build="GRCh37",
                        make_plots=True,
                        sample_reconstruction_plots=True,
                        exclude_signature_subgroups=None,
                        cosmic_version=3.4)

        aetiology=pd.read_csv('/miRTI/hw1/mutational_signature/aetiology_map.tsv',sep='\t')
        tmp_signature_assignment=pd.read_csv(f"{result_path}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt",sep='\t')
        tmp_signature_assignment={tmp_signature_assignment.columns[i]:tmp_signature_assignment.iloc[0,i] for i in range(1,tmp_signature_assignment.shape[1]) }
        tmp_signature_assignment={i:round(tmp_signature_assignment[i]/sum(tmp_signature_assignment.values()),2)  for i in tmp_signature_assignment.keys()}

        plotdata=pd.DataFrame.from_dict({'signature':tmp_signature_assignment.keys(),'freq':tmp_signature_assignment.values()})
        plotdata=plotdata[plotdata['freq']!=0]
        plotdata=pd.merge(plotdata,aetiology,on='signature',how='left')
        plotdata.loc[plotdata['aetiology'].isnull(),'aetiology']='Possible sequencing artefact'

        labels = list(tmp_signature_assignment.keys())
        sizes = list(tmp_signature_assignment.values())
        fig1, ax1 = plt.subplots()
        ax1.pie(plotdata['freq'], labels=plotdata['signature']+'\n'+plotdata['aetiology'], autopct='%1.1f%%', startangle=90)
        plt.savefig(f"{result_path}/pie_chart.pdf", format="pdf", bbox_inches="tight")
        plt.close()



# --------------------------------------------------讀取txt檔案 就是mutation signature分布--------------------------------------
        activities_path = f"{mut_filestore}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"


        with open(activities_path, 'r') as activities_file:
            activities_content = activities_file.readlines()

        activities_data = []
        headers = activities_content[0].strip().split('\t')
        for line in activities_content[1:]:
            values = line.strip().split('\t')
            activities_data.append(dict(zip(headers, values)))
        

        try:
            response_data = {
                'activities': activities_data,
                'pie_chart_url': f"/media/patient/{newjobid}/mutSig/pie_chart.pdf",
            }
            return JsonResponse(response_data, safe=False)
        except Exception as e:
            error_response = {'error': str(e)}
            return JsonResponse(error_response, status=500)
