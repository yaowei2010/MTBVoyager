import pandas as pd
import numpy as np
import time
import math
import re
class preprocessor():
    def __init__(self, avinput_table, VAF_cutoff=0.2, DP_cutoff=20, PassOnly="False"):  
        self.avinput_table = avinput_table
        self.VAF_cutoff = float(VAF_cutoff)
        self.DP_cutoff = int(DP_cutoff)
        self.PassOnly = False if PassOnly == "False" else True
    
    def calculateVAF(self, x):
    ### This function is to calculate VAF for each variant including multiallelic variant.
        if x['format'] == '.':
            return math.nan
        else:
            tmp_header = x['header'].split(':')
            tmp_format = x['format'].split(':')
            tmp_dict = dict(zip(tmp_header, tmp_format))

            if 'VAF' in tmp_header:
                return float(tmp_dict['VAF'])

            elif len(set(['AD', 'DP']).intersection(set(tmp_header))) == 2:
                if tmp_dict['GT'] == "1/0":
                    tmp_dict['GT'] = "0/1"
                
                GT = re.split('[|]|/', tmp_dict['GT'])

                # 检查 GT 中的每个元素是否是数字
                if all(g.isdigit() for g in GT):
                    GT_array = np.array([int(g) for g in GT])
                else:
                    # 如果有非数字字符，返回 math.nan
                    return math.nan

                AD = tmp_dict['AD'].split(',')
                AD_array = np.array([int(a) for a in AD])

                if len(GT_array) != len(AD_array):
                    GT_array = np.array([i for i in range(max(len(GT_array), len(AD_array)))])

                DP = int(tmp_dict['DP'])

                ### Determine the index of multiallelic allele,
                ### 1 indicate the first alternative allele,
                ### 2 indicate the second alternative allele, and so on.
                ### If multiallelic variant is detected , index ++,  else index = 1

                allele_ind = 1
                if (~math.isnan(x['pre_pos']) and (x['ori_pos'] == x['pre_pos']) and (len(AD_array) > 2)):
                    allele_ind = allele_ind + 1

                ### extract allele count by getting the index of allele
                countOfThisAllele = AD_array[np.where(GT_array == allele_ind)]
                if len(countOfThisAllele) > 1:
                    ### homozygous condition
                    return countOfThisAllele.max() / DP if countOfThisAllele.max() != 0 else math.nan

                elif len(countOfThisAllele) == 1 and not all(countOfThisAllele == 0):
                    ### heterozygous condition
                    return countOfThisAllele.item() / DP

                else:
                    return math.nan

            else:
                print("Warning: AD and DP are not detected! Original format will be returned.")
                return math.nan        

    
    def extractAD(self,x):
        AD = x.split(':')[1]
        return(AD)    
    
    
    def start_processing(self):
        print("Avinput preprocessing start:")
        output = self.avinput_table.copy()
        header=['Chr','Start','End','Ref','Alt','GT','QUAL','DP','ori_pos','FILTER','header']
        header.append('format')
        print("*******************start_processing")
        print(header)
        output.columns = header
        output['pre_pos'] = output['ori_pos'].shift()
        print(output)
        print("***************************")

        ## filtering by Depth
        output['DP'] = pd.to_numeric(output['DP'], errors='coerce')
        output = output.dropna(subset=['DP'])
        output['DP'] = output['DP'].astype(int)
        output = output[output['DP'] >= self.DP_cutoff]
        
        print(output)
        print("***********")
        ## filtering by Variant allele frequency
        output['VAF'] = output.apply(self.calculateVAF,1)
        print(output['VAF'])
        output['VAF'] = round(output['VAF'],2)
        output['AD']  = output['format'].apply(self.extractAD)
        output = output[output['VAF'] >= self.VAF_cutoff]
            
        ## filtering by FILTER, if PassOnly is true
        if(self.PassOnly):
            print("filter: pass only")
            output = output[output['FILTER'] == "PASS"]
            
        ## filtering base without A,T,C,G,or "-"
        output = output[output.Alt.str.contains('A|T|C|G|-')]
        print("output********")
        print(output)
        ## drop unused columns
        output = output.drop(columns = ['ori_pos','header','format','pre_pos','FILTER'])
        
        return output
        
        
        
    
