# ## version 1.1, currently used, last update:2023/5/5
# import os
# import argparse
# import subprocess
# import pandas as pd

# ## 計算avinput中有多少樣本，未完成
# def countSample(input_path):

#     ## extract header of input vcf by linux grep command
#     cmd = 'grep -m 1 \"#CHROM\" ' + input_path
#     inputVcfHeader = subprocess.check_output(cmd,shell=True)
#     inputVcfHeader = str(inputVcfHeader,'UTF8')

#     ## split header
#     inputVcfHeader = inputVcfHeader.split('\t')

#     ## find samples
#     inputSamples = pd.Series(inputVcfHeader)[~pd.Series(inputVcfHeader).isin(['#CHROM','POS','ID','REF','ALT','QUAL','FILTER','INFO','FORMAT'])].tolist()
#     print("this is sample\n")
#     print(inputSamples)
#     print("**************")
#     if len(inputSamples)>1:
#         print('This file contains '+ str(len(inputSamples)) +' samples including '+ ', '.join(inputSamples)+'.\n')
#     else:
#         print('This file contains '+ str(len(inputSamples)) +' sample.\n')
    
    
#     return(len(inputSamples))



# ## 設定VIP路徑
# ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
# print(ROOT_PATH)
# os.chdir(ROOT_PATH)
# print("current directory:")
# print(os.getcwd())

# ## 設定annovar路徑
# annovar_path =  '/annovar/'

# ## 設定參數
# parser = argparse.ArgumentParser()
# parser.add_argument('-input',
#                     help='input vcf or avinput file name')
# print("test***********")
# print(parser)

# parser.add_argument('-output',
#                     help='output path')
# print(parser)
# print("test***********")
# args = parser.parse_args()
# print(args)
# input_path = args.input
# output_path = args.output
# print(input_path)
# print(output_path)
# ## example: python3 annovar_pipeline0_3.py -input example.vcf -output example_ann.txt




# if len(input_path) == 0:
#     print("please input a vcf or avinput file!\n")
#     print("Example: python3 annovar_pipeline0_3.py -input example.vcf -output example_ann.txt\n")

# else:
#     file_type = os.path.splitext(input_path)[-1]





#     # 主要是看vcf還是avinput,如果是vcf 看它是單個樣本還是多個樣本 如果是單個樣本使用annovar:-withzyg的參數來設定,如果是多個樣本使用-allsample -withfreq的參數來設定,兩種設定最後都會轉成avinput
#     ## input file type為vcf
#     if file_type == '.vcf':
#         print('Input vcf: ' + input_path + '\n')        
#         print('---check the number of samples-----------------\n')
#         print(countSample(input_path))
#         ## 計算vcf內有多少樣本
#         if(countSample(input_path)>1):
#             tmp_avinput = '_tmp.avinput'.join(input_path.rsplit('.vcf', 1))
#             ## use argument -allsample -withfreq to extract information from multi-sample vcf
#             cmd = 'perl ' + annovar_path + 'convert2annovar.pl -format vcf4 ' + input_path + ' -allsample -withfreq -include -outfile ' + tmp_avinput 
#             print(cmd)
#         else:
#             tmp_avinput = '_tmp.avinput'.join(input_path.rsplit('.vcf', 1))
#             ## single sample
#             cmd = 'perl ' + annovar_path + 'convert2annovar.pl -format vcf4 ' + input_path + ' -outfile ' + tmp_avinput + ' -withzyg -include'
#             print(cmd)
        
#         print('---generate avinput----------------------------\n')
#         ## 透過annovar convert2annovar.pl將vcf轉換成avinput格式
#         os.system(cmd)
#         if os.path.isfile(tmp_avinput):
#             print('Create annovar avinput: ' + tmp_avinput + '\n')

#     ## input file type為avinput
#     elif file_type == '.avinput':
#         print("Input avinput: ", input_path, "\n")
#         tmp_avinput = input_path

#     ## invalid input file type
#     else:
#         print('please input a vcf or avinput file!\n')

#     print("---run annovar---------------------------------\n")
#     ## 透過annovar table_annovar.pl進行註解









    
#     tmp_annovar = '_annovar'.join(input_path.rsplit('.avinput', 1))
#     annovar_cmd = "perl " + annovar_path + "table_annovar.pl " + tmp_avinput + " " + annovar_path + \
#                   "humandb/ -buildver hg19 --polish --intronhgvs 20 -out " + tmp_annovar + " -remove -protocol refGeneWithVer,bed,avsnp150,ClinGen_annotation,gnomad211_genome,twnaf_annovarin,popfreq_all_20150413,LOVD_all,clinvar_20221231,intervar_20180118,dbscsnv11,spidex,cosmic70,dbnsfp35a -operation gx,r,f,f,f,f,f,f,f,f,f,f,f,f -bedfile hg19_hgmd_20201.bed --argument \'-hgvs,-colsWanted 4,,,,,,,,,,,,\' -nastring . --thread 16 --otherinfo -xref " + annovar_path + "example/gene_fullxref.txt "
#     print(annovar_cmd)
    
#     os.system(annovar_cmd)

#     annovar_result = tmp_annovar + ".hg19_multianno.txt"








#     ## 將結果重新命名
#     os.system("mv " + annovar_result + " " + output_path)

#     ## 檢查檔案是否存在
#     if os.path.isfile(output_path):
#         print('Create annotated table: ' + output_path + '\n')

#     print("Job finished!\n")

"""
annovar_pipeline0_3.py (hg19, NO promoter)
=========================================
- Input: .vcf or .avinput
- If .vcf:
    - multi-sample: convert2annovar.pl -allsample -withfreq -include
    - single-sample: convert2annovar.pl -withzyg -include
- Run table_annovar.pl with your original hg19 protocol list
- Output: move <prefix>.hg19_multianno.txt -> -output

Notes:
- All internal helper functions are prefixed with "_"
- Use subprocess.run(check=True) instead of os.system to surface errors
"""

import os
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple
import json
from datetime import datetime

import pandas as pd


# -------------------------
# internal helpers (prefixed with _)
# -------------------------
def _vcf_to_avinput(input_vcf: str, annovar_dir: str, out_avinput: str) -> None:
    """
    Convert VCF to avinput.
    Important: filter out symbolic/SV records (e.g. <CNV>, BND) because convert2annovar -withzyg needs GT.
    """
    n, samples = _count_samples_in_vcf(input_vcf)

    # 1) filter SNV/INDEL only (exclude <CNV>, BND, etc.)
    filtered_vcf = input_vcf.rsplit(".vcf", 1)[0] + ".snv_indel.vcf"
    filt_cmd = (
        f'bcftools view -i \'TYPE="snp" || TYPE="indel"\' "{input_vcf}" '
        f'-Ov -o "{filtered_vcf}"'
    )
    print("[CMD]", filt_cmd)
    _run_shell(filt_cmd)

    # 2) convert to avinput
    if n > 1:
        cmd = (
            f'perl "{annovar_dir}/convert2annovar.pl" -format vcf4 "{filtered_vcf}" '
            f'-allsample -withfreq -include -outfile "{out_avinput}"'
        )
        print(f"[INFO] VCF contains {n} samples: {', '.join(samples)}")
    else:
        cmd = (
            f'perl "{annovar_dir}/convert2annovar.pl" -format vcf4 "{filtered_vcf}" '
            f'-withzyg -include -outfile "{out_avinput}"'
        )
        print(f"[INFO] VCF contains {n} sample")

    print("[CMD]", cmd)
    _run_shell(cmd)

    if not os.path.isfile(out_avinput):
        raise RuntimeError(f"Failed to generate avinput: {out_avinput}")

def _status_marker_path(jobid: str) -> str:
    return f"/miRTI/media/patient/{jobid}/pipeline_status.json"

def _write_status_marker(jobid: str, status: str, extra: dict | None = None):
    p = _status_marker_path(jobid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    payload = {
        "jobid": jobid,
        "status": status,  # finished / failed
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        payload.update(extra)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def _run_shell(cmd: str) -> None:
    p = subprocess.run(cmd, shell=True, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        # 把 convert2annovar 真正吐的錯誤印出來
        raise RuntimeError(f"[CMD FAIL] rc={p.returncode}\nCMD={cmd}\n--- output ---\n{p.stdout}")



def _count_samples_in_vcf(vcf_path: str) -> Tuple[int, List[str]]:
    """Count samples by reading #CHROM header line once."""
    cmd = f'grep -m 1 "^#CHROM" "{vcf_path}"'
    header = subprocess.check_output(cmd, shell=True).decode("utf-8").rstrip("\n").split("\t")
    fixed = {"#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"}
    samples = [x for x in header if x not in fixed]
    return len(samples), samples





def _run_table_annovar(
    avinput_path: str,
    annovar_dir: str,
    humandb_dir: str,
    out_prefix: str,
    thread: int,
) -> str:
    """
    Run your original hg19 table_annovar settings (NO promoter).
    Returns produced multianno path.
    """
    protocol = (
        "refGeneWithVer,bed,avsnp150,ClinGen_annotation,gnomad211_genome,twnaf_annovarin,"
        "popfreq_all_20150413,LOVD_all,clinvar_20221231,intervar_20180118,dbscsnv11,spidex,cosmic70,dbnsfp35a"
    )
    operation = "gx,r,f,f,f,f,f,f,f,f,f,f,f,f"
    # 你原本的 argument：'-hgvs,-colsWanted 4,,,,,,,,,,,,'
    argument = "-hgvs,-colsWanted 4,,,,,,,,,,,,"

    # 你原本有寫 --bedfile hg19_hgmd_20201.bed，這裡保留
    cmd = (
        f'perl "{annovar_dir}/table_annovar.pl" "{avinput_path}" "{humandb_dir}/" '
        f'-buildver hg19 --polish --intronhgvs 20 '
        f'-out "{out_prefix}" -remove '
        f'-protocol {protocol} '
        f'-operation {operation} '
        f'-bedfile hg19_hgmd_20201.bed '
        f'--argument "{argument}" '
        f'-nastring . --thread {thread} --otherinfo '
        f'-xref "{annovar_dir}/example/gene_fullxref.txt"'
    )

    print("[CMD]", cmd)
    _run_shell(cmd)

    multianno = f"{out_prefix}.hg19_multianno.txt"
    if not os.path.isfile(multianno):
        raise RuntimeError(f"ANNOVAR output not found: {multianno}")
    return multianno


# -------------------------
# main
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-input", required=True, help="input vcf or avinput file path")
    parser.add_argument("-output", required=True, help="output annotated table path")
    parser.add_argument("--annovar_dir", default="/annovar", help="ANNOVAR directory (default: /annovar)")
    parser.add_argument("--humandb", default="/annovar/humandb", help="ANNOVAR humandb directory")
    parser.add_argument("--thread", type=int, default=16, help="ANNOVAR threads (default: 16)")
    parser.add_argument("--jobid", required=True, help="job id for status marker")

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    annovar_dir = args.annovar_dir.rstrip("/")
    humandb_dir = args.humandb.rstrip("/")
    thread = args.thread

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")
    if not os.path.isdir(annovar_dir):
        raise FileNotFoundError(f"ANNOVAR dir not found: {annovar_dir}")
    if not os.path.isdir(humandb_dir):
        raise FileNotFoundError(f"humandb dir not found: {humandb_dir}")

    # work dir: script folder (keep behavior similar to your original)
    root_path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_path)
    print("[INFO] ROOT_PATH:", root_path)
    print("[INFO] CWD:", os.getcwd())

    # ensure output dir
    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # 1) prepare avinput
    ext = os.path.splitext(input_path)[-1].lower()
    if ext == ".vcf":
        print(f"[INFO] Input VCF: {input_path}")
        tmp_avinput = input_path.rsplit(".vcf", 1)[0] + "_tmp.avinput"
        _vcf_to_avinput(input_path, annovar_dir, tmp_avinput)
        print(f"[OK] Create annovar avinput: {tmp_avinput}")
    elif ext == ".avinput":
        print(f"[INFO] Input avinput: {input_path}")
        tmp_avinput = input_path
    else:
        raise ValueError("Please input a .vcf or .avinput file")

    # 2) run annovar
    print("[INFO] Run ANNOVAR table_annovar (hg19, NO promoter)...")
    out_prefix = os.path.join(out_dir, Path(output_path).stem + "_annovar")
    multianno_path = _run_table_annovar(
        avinput_path=tmp_avinput,
        annovar_dir=annovar_dir,
        humandb_dir=humandb_dir,
        out_prefix=out_prefix,
        thread=thread,
    )

    # 3) move to output
    os.replace(multianno_path, output_path)
    if os.path.isfile(output_path):
        print(f"[OK] Create annotated table: {output_path}")

    print("[DONE] Job finished!")


if __name__ == "__main__":
    # 先偷看 jobid，避免 main() 爆掉時拿不到
    _jobid = None
    try:
        import sys
        if "--jobid" in sys.argv:
            _jobid = sys.argv[sys.argv.index("--jobid") + 1]
    except Exception:
        _jobid = None

    try:
        main()
        if _jobid:
            _write_status_marker(_jobid, "finished")
    except Exception as e:
        if _jobid:
            _write_status_marker(_jobid, "failed", {"error": str(e)})
        raise



