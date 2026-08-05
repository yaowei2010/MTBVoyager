import pandas as pd
import re
class WES_layering():
    def __init__(self, annotation_table, genotype_table, gene_panel, MAF_cutoff, review_status,phenotypeDrivenRanking=None):
        ## 註解後的表格
        self.annotation_table = annotation_table
        
        ## 基因型及品質的表格
        self.genotype_table = genotype_table
        
        ## 欲探勘之基因套組
        self.gene_panel = gene_panel

        ## Populational Allele frequency的門檻
        self.maf_cutoff = float(MAF_cutoff)

        ## Clinvar的證據強度，待移除
        self.review_status = int(review_status)

        ## 包含phenotype driven ranking分數的表格
        self.phenotypeDrivenRanking = phenotypeDrivenRanking
        
    def load_ACMG(self):
        ACMG_gene = ['ATP7B', 'KCNH2', 'MSH6', 'RET', 'TSC1', 'VHL', 'WT1', 'MYH7', 'KCNQ1',
                     'OTC', 'FBN1', 'SDHD', 'APOB', 'MLH1', 'GLA', 'RYR2', 'APC', 'CACNA1S',
                     'PTEN', 'PMS2', 'RYR1', 'TMEM43', 'SDHAF2', 'SMAD4', 'MSH2', 'ACTC1',
                     'BRCA1', 'SDHC', 'MYL2', 'NF2', 'SDHB', 'MUTYH', 'DSP', 'ACTA2', 'DSG2',
                     'DSC2', 'PRKAG2', 'BMPR1A', 'MYBPC3', 'TP53', 'TGFBR1', 'STK11', 'BRCA2',
                     'TSC2', 'MYH11', 'SMAD3', 'COL3A1', 'LDLR', 'TNNI3', 'RB1', 'SCN5A',
                     'TGFBR2', 'LMNA', 'TPM1', 'PKP2', 'TNNT2', 'MEN1', 'PCSK9', 'MYL3']
        return ACMG_gene
    
    def load_OMIM(self):
        OMIM_table = pd.read_csv('hw1/DB/HPO_merge_omim_summary_V6.csv', engine='python')
        OMIM_table = OMIM_table.rename(columns={'Gene.Symbols1':'Gene.refGene','Mim.Number':'OMIM_number','phenotype_summary':'Phenotype'})
        OMIM_table = OMIM_table[['Gene.refGene','OMIM_number','Phenotype']].drop_duplicates()
        return OMIM_table
    
    ## 調整Populational Allele frequency
    def adjust_AF(self, x):
        if x == '.':
            ## 沒有紀錄則回傳-1
            return -1
        else:
            AF = x
        return AF
    
    ## 調整Taiwan biobank的Allele frequency
    def adjust_TBB_AF(self, x):
        if x == '.':
            ## 沒有紀錄則回傳-1
            return -1
        elif re.search("[|]",x):
            ## 舊版資料庫中包含其他訊息，需透過split將字串切割出來
            AF = x.split('|')[2].split(':')[1]
        else:
            ## 新版資料庫中僅包含頻率，無需處理
            AF = x
        return AF
    
    ## 整合drug response，待移除
    def summarize_drug_response_evidence(self,x):
        evidence = x['Level of Evidence']
        type = x['Clinical Annotation Types']
        cemical = x['Related Chemicals']

        summary_string = evidence + '(' + type + ')'
        x['response_summary'] = summary_string

        return x
   
    ## 整合預測軟體分數
    def summarize_prediction(self, x):
        Polyphen2_HVAR = x['Polyphen2_HVAR_pred']
        VEST3   = x['VEST3_score']
        MetaSVM = x['MetaSVM_pred']
        MetaLR  = x['MetaLR_pred']
        CADD    = x['CADD_phred']
        MuTaster= x['MutationTaster_pred']
        SIFT    = x['SIFT_pred']
        DANN    = x['DANN_score']
        deleterious_agreed = 0
        deleterious_tools = 0

        ADA_score = x['dbscSNV_ADA_SCORE']
        RF_score = x['dbscSNV_RF_SCORE']
        spidex = x['dpsi_zscore']
        splicing_effect_agreed = 0
        splicing_effect_tools = 0

        if Polyphen2_HVAR != '.':
            deleterious_tools += 1
            if Polyphen2_HVAR in ['D','P']:
                deleterious_agreed += 1

        if VEST3 != '.':
            deleterious_tools += 1
            if float(VEST3) > 0.5:
                deleterious_agreed += 1    

        if MetaSVM != '.':
            deleterious_tools += 1
            if MetaSVM in ['D']:
                deleterious_agreed += 1

        if MetaLR != '.':
            deleterious_tools += 1
            if MetaLR in ['D']:
                deleterious_agreed += 1 

        if CADD != '.':
            deleterious_tools += 1
            if float(CADD) > 20:
                deleterious_agreed += 1
                
        if MuTaster != '.':
            deleterious_tools +=1
            if MuTaster in ['D','A']:
                deleterious_agreed += 1
                
        if SIFT != '.':
            deleterious_tools +=1
            if SIFT in ['D']:
                deleterious_agreed += 1
                
        if DANN != '.':
            deleterious_tools +=1
            if float(DANN) >0.95:
                deleterious_agreed += 1

        if ADA_score != '.':
            splicing_effect_tools += 1
            if float(ADA_score) >= 0.6:
                splicing_effect_agreed += 1

        if RF_score != '.':
            splicing_effect_tools += 1
            if float(RF_score) >= 0.6:
                splicing_effect_agreed += 1

        if spidex != '.':
            splicing_effect_tools += 1
            if abs(float(spidex)) >= 2:
                splicing_effect_agreed +=1

        x['deleterious_agreed'] = deleterious_agreed
        x['deleterious_tools'] = deleterious_tools
        x['splicing_effect_agreed'] = splicing_effect_agreed
        x['splicing_effect_tools'] = splicing_effect_tools
        return x
    
    ## 找尋具有drug response的變異
    def drug_response(self,input_variant):
        pharmGKB_table = pd.read_csv('hw1/DB/clinical_ann_metadata.tsv', 
                                     sep='\t', error_bad_lines = False)
        # print(pharmGKB_table.head())
        
        #### select variants with evidence Level 1 ####
        drug_response_db = pharmGKB_table[pharmGKB_table['Level of Evidence'].isin(['1A','1B'])]

        drug_response_variant = input_variant[input_variant['avsnp150'].isin(list(drug_response_db['Location']))]
        
        drug_response_db = drug_response_db.rename(columns={'Location':'avsnp150'})
        drug_response_demo = pd.merge(drug_response_variant,drug_response_db,how='inner',on='avsnp150')
        
        drug_response_demo = drug_response_demo.apply(self.summarize_drug_response_evidence,axis=1)
        drug_response_demo = drug_response_demo.rename(columns={'Related Chemicals':'Chemicals'})

        print("drug**************************8****************")
        print(drug_response_variant)
        print("drug_response_demo")
        print(drug_response_demo)
        
        return drug_response_variant,drug_response_demo
    
    ## 找尋已知具有致病性的變異，待加入HGMD後更新


    def known_pathogenic(self, input_variant, criteria):  
        #### select pathogenic variants recorded in Clinvar or LOVD without conflicting interpretation ####
        review_star_dict = {'no_assertion_provided': 0, 
                            'no_assertion_criteria_provided': 0,
                            'no_assertion_for_the_individual_variant': 0,
                            'criteria_provided,_conflicting_interpretations': 1,
                            'criteria_provided,_single_submitter': 1,
                            'criteria_provided,_multiple_submitters,_no_conflicts': 2,
                            'reviewed_by_expert_panel': 3,
                            'practice_guideline': 4}
        review_status_table = pd.DataFrame.from_dict(review_star_dict, orient='index', columns=['review_status'])
        print("Review status table:")
        print(review_status_table)

        ## select indices of known pathogenic variants in clinvar
        clinvar_pathogenic_index = input_variant.index[input_variant['CLNSIG'].str.contains('[P|p]athogenic', regex=True) &\
                                                    ~input_variant['CLNSIG'].str.contains('[C|c]onflicting', regex=True) &\
                                                    input_variant['CLNREVSTAT'].isin(review_status_table.index[review_status_table['review_status'] >= criteria])]
        print("ClinVar pathogenic index(ClinVar已知的致病基因):")
        print(clinvar_pathogenic_index)

        ## select indices of known benign variants in clinvar
        clinvar_benign_index = input_variant.index[input_variant['CLNSIG'].str.contains('[B|b]enign', regex=True) &\
                                                    ~input_variant['CLNSIG'].str.contains('[C|c]onflicting', regex=True) &\
                                                    input_variant['CLNREVSTAT'].isin(review_status_table.index[review_status_table['review_status'] >= 2])]
        print("ClinVar benign index(ClinVar已知的良性基因):")
        print(clinvar_benign_index)

        ## select indices of known pathogenic variants in clinvar
        if criteria >= 2:
            lovd_pathogenic_index = input_variant.index[input_variant['LOVD_all_clinical'].str.contains('[P|p]athogenic', regex=True) &  \
                                                        ~input_variant['LOVD_all_clinical'].str.contains('[B|b]enign|VUS', regex=True)]
        else:
            lovd_pathogenic_index = input_variant.index[input_variant['LOVD_all_clinical'].str.contains('[P|p]athogenic', regex=True)]
        print("LOVD pathogenic index(LOVD已知的致病基因):")
        print(lovd_pathogenic_index)

        ## concate indices of known pathogenic and exclude known benign variants
        known_pathogenic_index = clinvar_pathogenic_index.union(lovd_pathogenic_index) #聯集clinvar
        known_pathogenic_index = known_pathogenic_index[~known_pathogenic_index.isin(clinvar_benign_index)] #踢出已經知道良性的基因
        print("Known pathogenic index:")
        print(known_pathogenic_index)

        # 根據選擇的 pathogenic variants 的索引，打印已知 pathogenic variants 的信息
        known_pathogenic_variant = input_variant.loc[known_pathogenic_index,]
        print("Known pathogenic variants:")
        print(known_pathogenic_variant)

        known_pathogenic_variant = known_pathogenic_variant.apply(self.summarize_prediction, axis=1)
        return known_pathogenic_variant

    
    def predict_suspect(self, input_variant):
        tool_set =['Polyphen2_HVAR_pred','VEST3_score','MetaSVM_pred','MetaLR_pred',
                   'CADD_phred','MutationTaster_pred','SIFT_pred','DANN_score',
                   'dbscSNV_ADA_SCORE','dbscSNV_RF_SCORE','dpsi_zscore']
        ## exclude variants with no prediction scores and keep truncating variant
        input_variant = input_variant[(~input_variant[tool_set].isin(['.']).all(1))|input_variant['ExonicFunc.refGene'].isin(['stopgain','stoploss','startgain','startloss'])]
        
        input_variant = input_variant.apply(self.summarize_prediction,axis=1)
        candidate_index = input_variant.index[(input_variant['deleterious_agreed']>=2)| \
                                              (input_variant['splicing_effect_agreed'] >= 2)|(input_variant['ExonicFunc.refGene'].isin(['stopgain','stoploss','startgain','startloss']))]
        suspect_variant = input_variant.loc[candidate_index]

        ### exclude benign variants
        clinvar_non_benign_index = suspect_variant.index[~(suspect_variant['CLNSIG'].str.contains('[B|b]enign',regex=True) &  \
suspect_variant['CLNREVSTAT'].isin(['criteria_provided,_multiple_submitters,_no_conflicts','reviewed_by_expert_panel','practice_guideline']))]
        
        suspect_variant = suspect_variant.loc[clinvar_non_benign_index]
        
        return suspect_variant
    



    
    def inheritance_matching(self, input_variant):
        homo_variant = input_variant[input_variant['GT'] == 'hom']
        
        input_variant = input_variant[input_variant['GT']=='het']
        result={}
        for i in input_variant['Gene.refGene'].unique():
            n_class1 = input_variant[(input_variant['Gene.refGene']==i) & (input_variant['class']==1)].shape[0]
            n_class2 = input_variant[(input_variant['Gene.refGene']==i) & (input_variant['class']==2)].shape[0]
            n_class3 = input_variant[(input_variant['Gene.refGene']==i) & (input_variant['class']==3)].shape[0]
            result[i]=[n_class1,n_class2,n_class3]
        
        if len(result)==0:
            result=[None,None,None]
        result = pd.DataFrame.from_dict(result)
        result = result.transpose()
        result.columns = ['class1','class2','class3']
        
        two_hit_candidate = result[(result.sum(1)>=2) & (result.sum(1)!=result['class3'])]
        two_hit_variant = input_variant[input_variant['Gene.refGene'].isin(two_hit_candidate.index.to_list())]
        return homo_variant, two_hit_variant
        
    def layering(self):
        print("WES_layering start !")
        annot_table = self.annotation_table #vcf檔案


        gt_input    = self.genotype_table  #將vcf去過filter
        
        pheno_genes = self.gene_panel   

        ACMG_genes  = self.load_ACMG()
        OMIM_table  = self.load_OMIM()


        print("WES_latering OMIM test**************************************")
        print(OMIM_table)
        print("WES_latering test**************************************")


        phenotypeDrivenRanking = self.phenotypeDrivenRanking


        print("phenotypeDrivenRanking is :")
        print(phenotypeDrivenRanking)
        
        #### Preprocessing: ####
        ## 1. merge genotype, quality and depth of each variant 
        # print("WES_latering ANNOT_table test**************************************")
        # print(annot_table)
        # print("WES_latering test**************************************")
        # print("WES_latering GT_INPUT  test**************************************")
        # print(gt_input)
        # print("WES_latering test**************************************")
        
    

        
        # 將vcf去跟篩選過得vcf去merge起來 所以就會得到一個新的annot_table
        annot_table = pd.merge(annot_table,gt_input,how="inner",on=['Chr','Start','End','Ref','Alt'])


        print("WES_latering test**************************************")
        print(annot_table)
        print("WES_latering test**************************************")
        ## 2. adjust the format of allele frequency調整等位基因頻率的格式

        #  將refGeneWithVer改名為refGene,然後AF、1000G_ALL、taiwanbiobank等欄位如果資料是 . 就換成 -1 如果本身有值就還是維持本身的值
        annot_table.columns = [re.sub("refGeneWithVer$","refGene",i) for i in annot_table.columns] ## adjust column names
        
        annot_table['AF'] = annot_table['AF'].apply(self.adjust_AF).astype(float)
        annot_table['1000G_ALL'] = annot_table['1000G_ALL'].apply(self.adjust_AF).astype(float)
        annot_table['TaiwanBioBank'] = annot_table['TaiwanBioBank'].apply(self.adjust_TBB_AF).astype(float)

        # 最後去OMIM找數據  這個資料庫紀錄人類遺傳疾病的基因表現訊息 這個資料庫因為有gene的名稱的名稱 所以去跟過filter的資料去merge起來 因此有對到的資料後面會有多OMIM資料庫的訊息 如果沒有則顯示non

        annot_table = pd.merge(annot_table, OMIM_table, on='Gene.refGene', how='left')
        
        
        print("WES_latering test this is latest test**************************************")
        print(annot_table)
        print("WES_latering test**************************************")
        print("this is phenotypeDrivenRanking**********************************\n")




        if ~(phenotypeDrivenRanking is None):
            annot_table = annot_table.merge(phenotypeDrivenRanking[['Genes','Max_Score','Mean_Score']],left_on='Gene.refGene',right_on='Genes',how='left').fillna(-1)
            
            annot_table['Max_Score']=annot_table['Max_Score'].fillna(-1)
            annot_table['Mean_Score']=annot_table['Mean_Score'].fillna(-1)
            # x=annot_table
            # x.to_csv('/home/uuuwei0504/下載/VIP_germline-main/VIP/test/known_variants.csv',index=False)
        else:
            annot_table['Max_Score']=-1
            annot_table['Mean_Score']=-1

        
        
        
        #### Find drug response variants ####
        drug_response_variant,drug_response_demo = self.drug_response(annot_table)
        
        #### Find known pathogenic variant ####
        ## 1. filter variant with MAF > cutoff in gnomAD and 1000G
        filtered_table = annot_table[(annot_table['AF'] < self.maf_cutoff) & (annot_table['1000G_ALL'] < self.maf_cutoff)]
        # filtered_table先去對af去小於cutoff_frequency 然後在讓1000Gall小於cuf frequency
        
        ## 2. filter previously-layerd variants 
        filtered_table = filtered_table[~filtered_table.isin(drug_response_variant.to_dict('l')).all(1)]
        
        ## 3. start finding

        print("")
        #跟這這邊找到致病基因
        known_pathogenic_variant = self.known_pathogenic(filtered_table,self.review_status)
        known_pathogenic_variant['class']=1
        print("************known_variant")
        print(known_pathogenic_variant)

        pheno_genes = pheno_genes[0].split('、')
        known_pheno_variant = known_pathogenic_variant[known_pathogenic_variant['Gene.refGene'].isin(pheno_genes)]
        print(pheno_genes)
        print(f"共 {len(pheno_genes)} 個基因")
        print(pheno_genes)
        
        pheno_genes = [gene.strip() for gene in pheno_genes]
        print("This is known Pheno variant************************************************************")
        print("This is known Pheno variant************************************************************")
        print("This is known Pheno variant************************************************************")
        print("This is known Pheno variant************************************************************")
        print(known_pheno_variant)

        known_ACMG_variant = known_pathogenic_variant[known_pathogenic_variant['Gene.refGene'].isin(ACMG_genes)]
        known_other_variant = known_pathogenic_variant[~known_pathogenic_variant.index.isin(known_pheno_variant.index)&\
~known_pathogenic_variant.index.isin(known_ACMG_variant.index)]
        print("---------------THIS is known_pheno_variant")
        print(known_pheno_variant)
        print(known_ACMG_variant)
        print(known_other_variant)
        
        

        #### Find suspect variant by prediction tools ####
        ## 1. filter previously-layerd variants
        filtered_table = filtered_table[~filtered_table.isin(known_pathogenic_variant.to_dict('l')).all(1)]
        
        ## 2. start finding
        suspect_variant = self.predict_suspect(filtered_table)
        suspect_variant['class']=2
        suspect_pheno_variant = suspect_variant[suspect_variant['Gene.refGene'].isin(pheno_genes)]
        suspect_ACMG_variant = suspect_variant[suspect_variant['Gene.refGene'].isin(ACMG_genes)]
        suspect_other_variant = suspect_variant[~suspect_variant.index.isin(suspect_pheno_variant.index)&\
~suspect_variant.index.isin(suspect_ACMG_variant.index)]         
        #### Find the rest variant associated with gene panel ####
        filtered_table = filtered_table[~filtered_table.isin(suspect_variant.to_dict('l')).all(1)]
        filtered_table['class']=3
        other_pheno_variant = filtered_table[filtered_table['Gene.refGene'].isin(pheno_genes) & \
						~(filtered_table['Func.refGene'].isin(["intronic","intergenic"]))]
        other_pheno_variant = other_pheno_variant.apply(self.summarize_prediction,axis=1)
        
        #### Inheritance matching ####
        ## select nonsynonymous variants
        other_variant = filtered_table[(filtered_table['Func.refGene'].isin(['exonic'])) & \
                             ~(filtered_table['ExonicFunc.refGene'].isin(['synonymous SNV','unknown','.']))]
        other_variant = other_variant.apply(self.summarize_prediction,axis=1)
        
        ## combine all variant for further matching 
        variant_set = known_pathogenic_variant.append(suspect_variant, sort = False)
        variant_set = variant_set.append(other_variant, sort = False)
        
        homo_variant, two_hit_variant = self.inheritance_matching(variant_set)
        homo_pheno_variant = homo_variant[homo_variant['Gene.refGene'].isin(pheno_genes)]
        two_hit_pheno_variant = two_hit_variant[two_hit_variant['Gene.refGene'].isin(pheno_genes)]
        
        ### return with parameter dictionary
        parameters = {'known_pheno_variant'   : known_pheno_variant,
                      'known_ACMG_variant'    : known_ACMG_variant,
                      'known_other_variant'   : known_other_variant,
                      'suspect_pheno_variant' : suspect_pheno_variant,
                      'suspect_ACMG_variant'  : suspect_ACMG_variant,
                      'suspect_other_variant' : suspect_other_variant,
                      'drug_response_variant' : drug_response_variant,
                      'drug_response_demo'    : drug_response_demo,
                      'other_variant'   : other_pheno_variant,
                      'homo_pheno_variant'    : homo_pheno_variant,
                      'two_hit_pheno_variant' : two_hit_pheno_variant}
        return parameters
    
# if __name__ == "__main__":
        
        
