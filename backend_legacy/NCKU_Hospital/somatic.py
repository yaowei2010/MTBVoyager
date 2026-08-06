import pandas as pd
import os
import argparse
import re
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from typing import List, Tuple, Union
import vcfpy
import subprocess
import json

def argments():
    parser = argparse.ArgumentParser(description="This is the tool to filter variant with vcffiles")
    parser.add_argument('-i', '--input', required=True, help="input your vcf result file")
    parser.add_argument('-d', '--db', required=False, help="input your database file list directory")
    parser.add_argument('-o', '--outdir', required=True, help="input your output directory name")
    args = parser.parse_args()
    return args

## function for implement the genome

def extract_base(fasta_file:dict, chr: str, start: int, end: int) -> str:
    seq_record = fasta_file[chr]
    return str(seq_record.seq[start-1:end])

def flatten_genomic_change(fasta_file:dict, string: str) -> List[Union[str, int]]:
    # SNP
    if '>' in string:
        tmp_string = string.split(':')
        chr = tmp_string[0]
        change_sign = tmp_string[1].index('>')
        ref = tmp_string[1][change_sign-1]
        alt = tmp_string[1][change_sign+1]
        position = int(tmp_string[1][2:-3])
        return [chr, position, position, ref, alt]
    
    # INDEL
    elif re.search(r'del[A-Z]+ins[A-Z]+', string):
        tmp_string = string.split(':')
        chr = tmp_string[0]
        tmp_string = re.split(r'del|ins', tmp_string[1])
        ref = tmp_string[1]
        alt = tmp_string[2]
        tmp_position = re.sub(r'g.', '', tmp_string[0])
        tmp_position = [int(pos) for pos in tmp_position.split('_')]
        return [chr, tmp_position[0], tmp_position[1], ref, alt]

    # delins
    elif 'delins' in string:
        tmp_string = re.split(r':|_|delins', string)
        chr = tmp_string[0]
        start = int(re.sub(r'g.', '', tmp_string[1]))
        end = start if len(tmp_string) != 4 else int(tmp_string[2])
        alt = tmp_string[2] if len(tmp_string) != 4 else tmp_string[3]
        #print(chr, start, end)
        ref = extract_base(fasta_file, chr, start, end)
        return [chr, start, end, ref, alt]

    # del or ins
    elif 'del' in string or 'ins' in string:
        tmp_string = string.split(':')
        chr = tmp_string[0]
        change_sign = 'del' if 'del' in tmp_string[1] else 'ins'
        tmp_string = re.split(change_sign, tmp_string[1])
        
        if change_sign == 'del':
            ref = tmp_string[1]
            alt = '-'
            # bug
            tmp_position = re.sub(r'g.', '', tmp_string[0]).split('_')
            start = int(tmp_position[0])
            if len(tmp_position) > 1:
                end = int(tmp_position[1])
            else:
                end = int(tmp_position[0])
            if re.search(r'\d+', ref):
                ref = extract_base(fasta_file, chr, start, end)
            end = start + len(ref) - 1
            return [chr, start, end, ref, alt]
        else:
            ref = '-'
            alt = tmp_string[1]
            tmp_position = int(re.sub(r'g.', '', tmp_string[0]))
            return [chr, tmp_position, tmp_position, ref, alt]
    # duplication
    elif 'dup' in string:
        tmp_string = re.split(r'dup|_|:', string)
        chr = tmp_string[0]
        tmp_position = int(re.sub(r'g.', '', tmp_string[1])) - 1
        ref = '-'
        alt = tmp_string[-1]
        return [chr, tmp_position, tmp_position, ref, alt]
    
    else:
        print(f"error in {string}")
        return [None] * 5

def left_trim(ref: str, alt: str) -> dict:
    ref_seq = list(ref)
    alt_seq = list(alt)
    stop = 0
    for j in range(min(len(ref_seq), len(alt_seq))):
        if ref_seq[j] == alt_seq[j]:
            stop = j + 1
        else:
            break
    
    trim_ref = ref[stop:]
    trim_alt = alt[stop:]
    trim_length = stop
    return {"trim_ref": trim_ref, "trim_alt": trim_alt, "trim_length": trim_length}

def extract_transvar(arg: List[str]) -> List[dict]:
    header = arg[0].split('\t')
    context = arg[1:]
    result = [dict(zip(header, line.split('\t'))) for line in context]
    return result

## run ANNOVAR

def decompose_multiallelic(row):
    results = []
    i = 0
    for allele in row['ALT']:
        alt_allele = allele.value
        new_row = row.copy()
        new_row['ALT'] = alt_allele
        new_row['AF'] = row['AF'][i]
        new_row['FAO'] = row['FAO'][i]
        results.append(new_row)
        i +=1
    return results

def normalize_variant(row):
    global reference
    # INDEL case
    if len(row['REF']) != 1 or len(row['ALT']) != 1:
        transvar_input = f"{row['CHROM']}:{row['POS']}_{row['POS']}{row['REF']}>{row['ALT']}"
        transvar_result = subprocess.run(f"transvar ganno -i \"{transvar_input}\" --refseq", shell=True, capture_output=True, text=True).stdout
        if not transvar_result.strip() or transvar_result.strip() == "input\ttranscript\tgene\tstrand\tcoordinates(gDNA/cDNA/protein)\tregion\tinfo":
            return row
        else:
            if "left_align_gDNA" in transvar_result:
                tmp_str = re.search(r"left_align_gDNA=([^;]+);", transvar_result).group(1)
                chr = re.search(r"(\w+):", transvar_result).group(1)
                flattened = flatten_genomic_change(reference, f"{chr}:{tmp_str}")
                row["CHROM"], row["POS"], row["END"], row["REF"], row["ALT"] = flattened
            else:
                tmp_str = re.search(r"(\w+):(\w+)", transvar_result).group(2)
                if pd.isna(tmp_str):
                    return row
                else:
                    flattened = flatten_genomic_change(reference, tmp_str)
                    row["CHROM"], row["POS"], row["END"], row["REF"], row["ALT"] = flattened
    return row



def prepareAVINPUT(input_vcf, tmp_output_avinput):
    global reference
    #input_vcf = '/home/cadilac/137_share/147_backup/interpretation/00228512_OCPv1.vcf'
    reader = vcfpy.Reader.from_path(input_vcf)
    records = [record for record in reader if record.FILTER == ['PASS']]
    records = [record for record in records if record.ALT[0] != vcfpy.SymbolicAllele('CNV')]
    records = [record for record in records if not any(isinstance(alt, vcfpy.BreakEnd) for alt in record.ALT)]
    
    vcf_data = []
    for record in records:
        info_dict = {}
        info_dict.update({
            'CHROM': record.CHROM,
            'POS': record.POS,
            'ID': record.ID,
            'REF': record.REF,
            'ALT': record.ALT,
            'QUAL': record.QUAL,
            'FILTER': record.FILTER,
        })
        info_dict.update(record.INFO)
        for call in record.calls:
            sample_dict = call.data
            sample_dict.update(info_dict)
            vcf_data.append(sample_dict)

    # extract to tidy
    vcf_df = pd.DataFrame(vcf_data)

    # genotype
    sub_vcf = vcf_df[vcf_df['GT'] != '0/0']

    decomposed_vcf = []
    for _, row in sub_vcf.iterrows():
        if len(row['ALT'])>2:
            decomposed_vcf.extend(decompose_multiallelic(row))
        else:
            row['ALT'] = row['ALT'][0].value
            decomposed_vcf.append(row)

    decomposed_vcf_df = pd.DataFrame(decomposed_vcf)

    # Filter VF = 0
    decomposed_vcf_df['VF'] = decomposed_vcf_df['VF'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)
    decomposed_vcf_df = decomposed_vcf_df[decomposed_vcf_df['VF'] != 0]

    # Filter FDP == 'NA'
    decomposed_vcf_df['DP'] = pd.to_numeric(decomposed_vcf_df['DP'], errors='coerce')
    decomposed_vcf_df = decomposed_vcf_df.dropna(subset=['DP'])

    # Process FAO and FDP
    decomposed_vcf_df['AD'] = decomposed_vcf_df['AD'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)
    decomposed_vcf_df['AD'] = decomposed_vcf_df.apply(lambda row: round(row['DP'][0] * row['VF'][0]) if pd.isna(row['AD']) else row['AD'], axis=1)

    # Process END
    decomposed_vcf_df['END'] = decomposed_vcf_df['POS']
    columns = ["CHROM", "POS", "END", "REF", "ALT", "GT", "QUAL", "DP", "VF", "AD"]
    decomposed_vcf_df = decomposed_vcf_df[columns]
    decomposed_vcf_df.columns = ["CHROM", "POS", "END", "REF", "ALT", "GT", "QUAL", "FDP", "AF", "FAO"]


    decomposed_vcf_df['POS'] =  decomposed_vcf_df['POS'].apply(lambda x: f"{x:.0f}")
    decomposed_vcf_df['END'] =  decomposed_vcf_df['END'].apply(lambda x: f"{x:.0f}")

    # normalization
    decomposed_vcf_df = decomposed_vcf_df.apply(normalize_variant, axis=1)

    # update genotype to het and hom
    decomposed_vcf_df['GT'] = decomposed_vcf_df['GT'].apply(lambda x: 'het' if x == '0/1' else 'hom')

    # output
    decomposed_vcf_df.to_csv(tmp_output_avinput, sep='\t', index=False, header=False)
    return decomposed_vcf_df

# annotation

def annotate_CGI(target, db_path):
    if any(target.columns.str.contains("CGI_annotation")):
        target = target.loc[:, ~target.columns.str.contains("CGI_annotation")]

    CGI_with_position = pd.read_csv(os.path.join(db_path,"hg19_CGI_with_pos_20200115.txt"), sep="\t", header = 0)
    CGI_without_position = pd.read_csv(os.path.join(db_path,"hg19_CGI_without_pos_20200115.txt"), sep="\t", header = 0)

    target = pd.merge(target, CGI_with_position, how='left', left_on=target.columns[:5].tolist(), right_on=CGI_with_position.columns[:5].tolist())
    target['CGI_annotation'] = target['CGI_annotation'].fillna(".")

    # Annotate based on CGI_without_position
    for i, row in CGI_without_position.iterrows():
        tmp_gene = row['Hugo_symbol']
        tmp_mut = row['Biomarker']

        if tmp_mut == "Truncating Mutations":
            ind = target[(target['Gene.refGene'] == tmp_gene) & (target['ExonicFunc.refGene'] == "stopgain")].index
            if len(ind) != 0:
                target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
        else:
            tmp_mut_split = tmp_mut.split()
            exon = f"{row['RefSeq']}:exon{int(tmp_mut_split[2])}"
            state = tmp_mut_split[3]

            if re.search("(I|i)nsertion", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['ExonicFunc.refGene'].str.contains("insertion"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
            elif re.search("(D|d)eletion", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['ExonicFunc.refGene'].str.contains("deletion"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
            elif re.search("splice", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['Func.refGene'].str.contains("splicing"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
    return target


def annotate_oncoKB(target, db_path):
    if any(target.columns.str.contains("oncoKB_annotation")):
        target = target.loc[:, ~target.columns.str.contains("oncoKB_annotation")]
    
    oncoKB_with_position = pd.read_csv(os.path.join(db_path, "hg19_oncoKB_with_position_20200110.txt"), sep="\t", header = 0)
    oncoKB_without_position = pd.read_csv(os.path.join(db_path, "hg19_oncoKB_without_position_20200110.txt"), sep="\t", header = 0)
    
    target = target.merge(oncoKB_with_position, left_on=target.columns[:5].tolist(), right_on=oncoKB_with_position.columns[:5].tolist(), how='left')
    target['oncoKB_annotation'] = target['oncoKB_annotation'].fillna('.')
    
    # Annotate oncoKB_without_position
    for i, row in oncoKB_without_position.iterrows():
        tmp_gene = row['Hugo Symbol']
        tmp_mut = row['Alteration']
        
        if tmp_mut == "Truncating Mutations":
            ind = target[(target['Gene.refGene'] == tmp_gene) & (target['ExonicFunc.refGene'] == "stopgain")].index
            if not ind.empty:
                target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
        else:
            tmp_mut_split = tmp_mut.split()
            exon = f"{row['RefSeq']}:exon{int(tmp_mut_split[1])}"
            state = tmp_mut_split[2]
            
            if re.search(r"(I|i)nsertion", state):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['ExonicFunc.refGene'].str.contains("insertion", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
            elif re.search(r"(D|d)eletion", state):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['ExonicFunc.refGene'].str.contains("deletion", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
            elif re.search(r"splice", state, re.IGNORECASE):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['Func.refGene'].str.contains("splicing", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
    return target

def process_predictions(target):
    # scoring
    def calculate_pre_sum(row):
        values = row.values
        if (values == ".").sum() == 5:
            return "Un_predict"
        else:
            return (values == "D").sum() / (values != ".").sum()
    
    prediction_tools = ["Polyphen2_HVAR_pred", "MetaSVM_pred", "CADD_phred", "VEST3_score", "MetaLR_pred"]
    test1 = target[prediction_tools].copy()
    test1["CADD_phred"] = test1["CADD_phred"].apply(lambda x: "T" if x == "." else ("D" if float(x) > 20 else "T"))
    
    # Polyphen2_HVAR_pred
    test1["Polyphen2_HVAR_pred"] = test1["Polyphen2_HVAR_pred"].replace({"B": "T", "P": "D"})
    
    # VEST3_score
    test1["VEST3_score"] = test1["VEST3_score"].apply(lambda x: "T" if x == "." else ("D" if float(x) > 0.5 else "T"))
    test1["pre_sum"] = test1.apply(calculate_pre_sum, axis=1)
    
    # merge
    target = target.copy()
    target["summarized_prediction"] = test1["pre_sum"]
    return target

# Merge AVINPUT and ANNOVAR result
def process_annovar_results(target, tmp_av, output):

    print(tmp_av['AF'])

    target['mergeidx'] = target.apply(lambda row: f"{row['Chr']}:{row['Start']}-{row['End']}:{row['Ref']}>{row['Alt']}", axis=1)

    if 'AF' in target.columns:
        target['AF'] = target['AF'].replace('.', 0).astype(float)
    
    print(tmp_av['AF'])
    # Got the VAF, FAO and DP   
    if tmp_av.shape[1] == 5:
        tmp_av.columns = ["Chr", "Start", "End", "Ref", "Alt"]
        tmp_av['GT'] = "het"
        tmp_av['QUAL'] = 1000
        tmp_av['DP'] = 2000
        tmp_av['VAF'] = 0.5
        tmp_av['FAO'] = 1000
        if not tmp_av.iloc[0]['Chr'].startswith('chr'):
            if tmp_av.iloc[0]['Chr'] in map(str, range(1, 23)) + ['X', 'Y']:
                tmp_av['Chr'] = 'chr' + tmp_av['Chr']
            else:
                tmp_av = tmp_av.iloc[1:]
    
    tmp_av.columns = ["Chr", "Start", "End", "Ref", "Alt", "GT", "QUAL", "DP", "VAF", "FAO"]
    tmp_av['mergeidx'] = tmp_av.apply(lambda row: f"{row['Chr']}:{row['Start']}-{row['End']}:{row['Ref']}>{row['Alt']}", axis=1)

    # merge
    tmp_result = pd.merge(target, tmp_av[["VAF", "DP", "FAO","mergeidx"]], left_on=["mergeidx"], right_on=["mergeidx"], how='outer')
    tmp_result.to_csv(output, sep='\t', index=False)
    return tmp_result
    


# Filter
def filter_biobank_af(x):
    if x == '.':
        return 0
    else:
        biobank_af = x.split('|')[2]
        AF = biobank_af[3:]
        return AF
    
def filter(source_df):
    # ------- Actionable ---------
    # Rule: any drugs in clinical database, oncoKB, COSMIC, CIVIC, MyCancerGenome, CGI
    actionable_df = source_df[~source_df['oncoKB_annotation'].isin(['.']) | ~source_df['CGI_annotation'].isin(['.']) | ~source_df['CIVIC_annotation'].isin(['.'])]

    # ------- Filter ---------
    # AF <= 0.01
    source_df['AF'] = source_df['AF'].apply(lambda x: 0 if x == '.' else x)
    source_df['AF'] = pd.to_numeric(source_df['AF'], errors='coerce')
    tmp_df = source_df[source_df['AF'] <= 0.01]
    # Biobank AF <= 0.01
    tmp_df['biobank_af'] = tmp_df['TaiwanBioBank'].apply(filter_biobank_af)
    df = tmp_df[tmp_df['biobank_af'].astype(float) <= 0.01]
    df = df.drop(columns=['biobank_af'])

    # Exonic
    func_list = ['exonic', 'splicing', 'exonic;splicing']
    df = df[df['Func.refGene'].isin(func_list)]

    # Nonsynonymous
    filter_df = df[~df['ExonicFunc.refGene'].isin(['synonymous SNV'])]

    # ----- Heredity -------
    tmp_heredity_df = filter_df[(filter_df['CLNREVSTAT'].isin(['reviewed_by_expert_panel']) &
                                 filter_df['CLNSIG'].isin(['Pathogenic', 'Likely_pathogenic'])) |
                                (filter_df['LOVD_all_clinical'].str.contains('pathogenic') &
                                 (~filter_df['LOVD_all_clinical'].str.contains('benign')) &
                                 (~filter_df['LOVD_all_clinical'].str.contains('VUS'))) |
                                filter_df['ClinGen_annotation'].str.contains('Pathogenic')]

    # non-actionable heredity variants
    heredity_df = tmp_heredity_df[~tmp_heredity_df.isin(actionable_df.to_dict('list')).all(1)]

    # Uncertain -> LOVD/ClinVar/Clingene not pathogenic(/likely) or not benign(/likely)
    tmp_un_df = filter_df[~filter_df.isin(actionable_df.to_dict('list')).all(1)&
                       ~filter_df.isin(heredity_df.to_dict('list')).all(1)]
    uncertain_df = tmp_un_df[~tmp_un_df['LOVD_all_clinical'].str.contains('benign')&
                             ~tmp_un_df['ClinGen_annotation'].str.contains('Benign')&
                             (~tmp_un_df['CLNSIG'].isin(['Benign', 'Likely_benign']))]

    # print(uncertain_df)
    # uncertain_df.to_csv('uncertain_df.csv', sep=',')

    internal_filter = uncertain_df[(uncertain_df['VAF'].astype(float) >= 0.05) &
                                   (uncertain_df['FAO'].astype(float) >= 10)]
    # ------ COSMIC -------
    COSMIC_df = internal_filter[~internal_filter['cosmic90_coding'].isin(['.'])]

    # Prediction
    non_cosmic_df = internal_filter[internal_filter['cosmic90_coding'].isin(['.'])]
    if 'summarized_prediction' in non_cosmic_df.columns:
        unpredict_df = non_cosmic_df[non_cosmic_df['summarized_prediction'] == 'Un_predict']
        tmp_predict_df = non_cosmic_df[~non_cosmic_df.isin(unpredict_df.to_dict('list')).all(1)]
        suspect_df = tmp_predict_df[tmp_predict_df['summarized_prediction'].astype(float) >= 0.71]
        suspect_df = pd.concat([suspect_df, unpredict_df], ignore_index=True)
    else:
        suspect_df = non_cosmic_df[non_cosmic_df['test1$pre_sum'].astype(float) >= 0.71]

    return actionable_df, heredity_df, COSMIC_df, suspect_df




if __name__ == '__main__':
    annovar_path = "/annovar"
    humandb = "/annovar/humandb"
    clinicaldb_path = "/annovar/somatic/clinicaldb/"

    args = argments()
    if os.path.isdir(os.path.join(args.outdir, 'tmpdir')):
        pass
    else:
        os.mkdir(os.path.join(args.outdir, 'tmpdir'))

    # Test flatten function
    fasta_file = '/annovar/humandb/ucsc_hg19.fa'
    reference = SeqIO.to_dict(SeqIO.parse(fasta_file, 'fasta'))
    with open(os.path.join(humandb, "annovar_to_approved_symbol.json"), 'r') as file:
       genedict = json.load(file)

    # Test usage
    # input_vcf = '//home/willis/project/mtb/bin/24C00131_main.vcf'
    # Setting essential parameters
    input_vcf = args.input
    basename = os.path.basename(input_vcf).split('.')[0]
    tmp_output_avinput = basename + '.output.avinput'
    tmp_annovar = basename + '_annotate'

    # Make ANNOVAR Input format AVINPUT file
    avinputdf = prepareAVINPUT(input_vcf, tmp_output_avinput)

    # Run the ANNOVAR program in server 
    annovar_cmd = (
        f"perl {annovar_path}/table_annovar.pl "
        f"{tmp_output_avinput} "
        f"{humandb} "
        f"-buildver hg19 -out {tmp_annovar} -remove "
        f"-protocol refGene,avsnp150,ClinGen_annotation,gnomad211_genome,Taiwan_Biobank,LOVD_all,clinvar_20240407,cosmic90_coding,dbnsfp35a,CIVIC_annotation,OCP_ver2 "
        f"-operation g,f,f,f,f,f,f,f,f,f,f "
        f"-nastring . --thread 8 --otherinfo "
    )    
    # Check command line for annovar and then run
    print(annovar_cmd)
    subprocess.run(annovar_cmd, shell=True)

    # Reading the result
    #tmp_annovar = "00228512_OCPv1_annotate"
    multianno = pd.read_csv(f"""{tmp_annovar}.hg19_multianno.txt""", sep = '\t', header = 0)
    annovardf = process_annovar_results(multianno, avinputdf, os.path.join(args.outdir, basename + '_annovar_final.txt'))
    annovardf['Gene'] = annovardf['Gene.refGene'].apply(lambda x: genedict(x) if x in genedict else x)

    # Annotate another clinical database
    CGIdf = annotate_CGI(annovardf, clinicaldb_path)
    Oncodf = annotate_oncoKB(CGIdf, clinicaldb_path)
    predictdf = process_predictions(Oncodf)
    predictdf = predictdf.dropna()
    predictdf.to_csv('tmp.test.txt', sep = '\t', index=False)
    # Somatic SNV Filtering from annotation predictdf
    actionable_df, heredity_df, COSMIC_df, suspect_df = filter(predictdf)
    actionable_num = len(actionable_df)
    heredity_num = len(heredity_df)
    cosmic_num = len(COSMIC_df)
    suspect_num = len(suspect_df)

    # Check point usage
    print('------------------------The Number of each section-------------------------')
    print(actionable_num, heredity_num, cosmic_num, suspect_num) 
    print('------------------------actionable-------------------------')
    print(actionable_df)
    print('------------------------Heredity-------------------------')
    print(heredity_df)
    print('------------------------COSMIC-------------------------')
    print(COSMIC_df)
    print('------------------------Suspect-------------------------')
    print(suspect_df)
    print('------------------------END-------------------------')

    # Actionable available ranking
    #### FDA Drugs avaliable
    #### Clincal trial avaliable
    ##### Check all the drug content in drugs databases
    



    # Potential Treatment Section
    
