## version 1.1, currently used, last update:2023/5/5
import os
import argparse
import subprocess
import pandas as pd

## 計算avinput中有多少樣本，未完成
def countSample(input_path):

    ## extract header of input vcf by linux grep command
    cmd = 'grep -m 1 \"#CHROM\" ' + input_path
    inputVcfHeader = subprocess.check_output(cmd,shell=True)
    inputVcfHeader = str(inputVcfHeader,'UTF8')

    ## split header
    inputVcfHeader = inputVcfHeader.split('\t')

    ## find samples
    inputSamples = pd.Series(inputVcfHeader)[~pd.Series(inputVcfHeader).isin(['#CHROM','POS','ID','REF','ALT','QUAL','FILTER','INFO','FORMAT'])].tolist()
    print("this is sample\n")
    print(inputSamples)
    print("**************")
    if len(inputSamples)>1:
        print('This file contains '+ str(len(inputSamples)) +' samples including '+ ', '.join(inputSamples)+'.\n')
    else:
        print('This file contains '+ str(len(inputSamples)) +' sample.\n')
    
    
    return(len(inputSamples))



## 設定VIP路徑
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
print(ROOT_PATH)
os.chdir(ROOT_PATH)
print("current directory:")
print(os.getcwd())

## 設定annovar路徑
annovar_path =  '/annovar/'

## 設定參數
parser = argparse.ArgumentParser()
parser.add_argument('-input',
                    help='input vcf or avinput file name')
print("test***********")
print(parser)

parser.add_argument('-output',
                    help='output path')
print(parser)
print("test***********")
args = parser.parse_args()
print(args)
input_path = args.input
output_path = args.output
print(input_path)
print(output_path)
## example: python3 annovar_pipeline0_3.py -input example.vcf -output example_ann.txt




if len(input_path) == 0:
    print("please input a vcf or avinput file!\n")
    print("Example: python3 annovar_pipeline0_3.py -input example.vcf -output example_ann.txt\n")

else:
    file_type = os.path.splitext(input_path)[-1]





    # 主要是看vcf還是avinput,如果是vcf 看它是單個樣本還是多個樣本 如果是單個樣本使用annovar:-withzyg的參數來設定,如果是多個樣本使用-allsample -withfreq的參數來設定,兩種設定最後都會轉成avinput
    ## input file type為vcf
    if file_type == '.vcf':
        print('Input vcf: ' + input_path + '\n')        
        print('---check the number of samples-----------------\n')
        print(countSample(input_path))
        ## 計算vcf內有多少樣本
        if(countSample(input_path)>1):
            tmp_avinput = '_tmp.avinput'.join(input_path.rsplit('.vcf', 1))
            ## use argument -allsample -withfreq to extract information from multi-sample vcf
            cmd = 'perl ' + annovar_path + 'convert2annovar.pl -format vcf4 ' + input_path + ' -allsample -withfreq -include -outfile ' + tmp_avinput 
            print(cmd)
        else:
            tmp_avinput = '_tmp.avinput'.join(input_path.rsplit('.vcf', 1))
            ## single sample
            cmd = 'perl ' + annovar_path + 'convert2annovar.pl -format vcf4 ' + input_path + ' -outfile ' + tmp_avinput + ' -withzyg -include'
            print(cmd)
        
        print('---generate avinput----------------------------\n')
        ## 透過annovar convert2annovar.pl將vcf轉換成avinput格式
        os.system(cmd)
        if os.path.isfile(tmp_avinput):
            print('Create annovar avinput: ' + tmp_avinput + '\n')

    ## input file type為avinput
    elif file_type == '.avinput':
        print("Input avinput: ", input_path, "\n")
        tmp_avinput = input_path

    ## invalid input file type
    else:
        print('please input a vcf or avinput file!\n')

    print("---run annovar---------------------------------\n")
    ## 透過annovar table_annovar.pl進行註解









    
    tmp_annovar = '_annovar'.join(input_path.rsplit('.avinput', 1))
    annovar_cmd = "perl " + annovar_path + "table_annovar.pl " + tmp_avinput + " " + annovar_path + \
                  "humandb/ -buildver hg19 --polish --intronhgvs 20 -out " + tmp_annovar + " -remove -protocol refGeneWithVer,bed,avsnp150,ClinGen_annotation,gnomad211_genome,twnaf_annovarin,popfreq_all_20150413,LOVD_all,clinvar_20221231,intervar_20180118,dbscsnv11,spidex,cosmic70,dbnsfp35a -operation gx,r,f,f,f,f,f,f,f,f,f,f,f,f -bedfile hg19_hgmd_20201.bed --argument \'-hgvs,-colsWanted 4,,,,,,,,,,,,\' -nastring . --thread 16 --otherinfo -xref " + annovar_path + "example/gene_fullxref.txt "
    print(annovar_cmd)
    
    os.system(annovar_cmd)

    annovar_result = tmp_annovar + ".hg19_multianno.txt"








    ## 將結果重新命名
    os.system("mv " + annovar_result + " " + output_path)

    ## 檢查檔案是否存在
    if os.path.isfile(output_path):
        print('Create annotated table: ' + output_path + '\n')

    print("Job finished!\n")
