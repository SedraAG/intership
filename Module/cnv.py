import numpy as np
import pandas as pd
from Bio import SeqIO
import seaborn as sns
from matplotlib import pyplot as plt
import seaborn as sns
from Bio.SeqUtils import GC
plt.style.use('ggplot')
from scipy.interpolate import interp1d
import statsmodels.api as sm
import argparse

# calculate the end index of each chr in df
# requires 2 different columns: chr_ind to group the df by it and any other column 

def add_column(df,name):
    if (not (name in df)):
        df[name] = np.nan


def index_of_chr(df,chr_ind,chr):
    indices = df.groupby([chr_ind]).count()[chr]
    my_list = []
    for i in range (1,len(indices)+1):
        if i == 1:
            my_list.append(indices[i])
        else:
            indices[i] = indices[i] + indices[i-1]
            my_list.append(indices[i])    
    return my_list
    


# s is the start of the bin and e is the end of the bin and a is the sequence
# of the chromosome wehre the bin is located

def countGC(start,end,sequence):
    """ calculate the GC-cotent  of a sequnce
    
    ignores N-bases in calculations"""
    content = sequence[start:end]
    na = content.count("A")
    nt = content.count("T")
    ng = content.count("G")
    nc = content.count("C")
    nat = na + nt
    ncg = ng + nc
    return (ncg/((ncg+nat)+1)) # +1 to avoid dividing by zero

def countGC1(start,end,sequence):
    """ calculate the GC-cotent  of a sequnce

    includes N-bases in calculations"""
    content = sequence[start:end]
    return GC(content)*100

# the difference between countGC and countGC1 is that countGC does not include the NNN..
# bases in the calculations, so we only calculate (C+G)/(A+G+C+T), while countGC1
# includes the N bease in the calculations. (G+C)/(A+G+C+T+N)calculate GC_content of
# each bin in each chromosom and add them all together in one list

def countCGall(chr_list,indices,df):
    """ calculate the GC-cotent  of a sequnce
    
    ignores N-bases in calculations"""
    chr_cg = []
    for i in range (22):  # for each chr
        chromosom = chr_list[i]
        index = indices[i]       
        if i == 0 :
            for j in range (0,index):
                chr_cg.append(countGC(df.bin_start[j],df.bin_end[j],chromosom))   
        else:
            last_index = indices[i-1]
            for j in range (last_index, index):
                chr_cg.append(countGC(df.bin_start[j], df.bin_end[j], chromosom))
    return chr_cg


def countCGall1(chr_list,indices,df):
    """ calculate the GC-cotent  of a sequnce
    
    includes N-bases in calculations"""
    chr_cg = []
    for i in range (22):
        chromosom = chr_list[i]
        index = indices[i]    
        if i == 0 :
            for j in range (0,index):
                chr_cg.append(countGC1(df.bin_start[j],df.bin_end[j],chromosom))   
        else:
            last_index = indices[i-1] 
            for j in range (last_index, index):
                chr_cg.append(countGC1(df.bin_start[j],df.bin_end[j],chromosom))
    return chr_cg


def normalise_to_fixed_value(df,counts,fixed_value,type):
    if fixed_value == "mean":
        mean_normalised_counts = counts * (2 / counts.mean())
        df["mean_normalised" + type +"_counts"] = mean_normalised_counts
    elif fixed_value == "median":
        median_normalised_counts = counts * (2 / counts.median())
        df["median_normalised" + type +"_counts"] = median_normalised_counts
    elif fixed_value == "mode":
        mode_normalised_counts = counts * (2/counts.mode().mean())
        df["mode_normalised" + type +"_counts"] = mode_normalised_counts

# requires colum 'chr_ind' 

def estimate_copy_number(df,fixed_value,column):
    if (fixed_value=='mean'): 
        copy_nr_mean=df.groupby(['chr_ind']).mean().round(decimals=0)
        return copy_nr_mean[column]
    elif (fixed_value=='median'):
        copy_nr_median=df.groupby(['chr_ind']).median().round(decimals=0)
        return copy_nr_median[column]
    elif (fixed_value=='mode'):
        copy_nr_median=df.groupby(['chr_ind']).median().round(decimals = 0)
        return copy_nr_median

# GC-content normalisation:
# for the correlation curve:
# we cut the big interval into 360 samller intervall (i variabel in the for  loop) 
# and calculate the GC-conten median in each interval and add the value to the list 
# cg_window.
# the size of the window is also variable (we have 0,025)
# we also add the median of the counts to the median_counts list



# rs: range start
# re: range end
# steps: ~how many points 
# pl
def smoothplot(df,rs,re,window_size):
    median_counts = []
    cg_window = []
    for i in range (rs,re,window_size):
        median_counts.append(df.loc[(df.GC_content >= (i/10000)-0.01) &
                                     (df.GC_content <= (i/10000)+0.015)].counts.median())
        cg_window.append(df.loc[(df.GC_content >= (i/10000)-0.01) &
                                     (df.GC_content <= (i/10000)+0.015)].GC_content.median())
    return median_counts, cg_window

# normalization for GC content:
# the function gc_correction normalises the read counts to the GC-content and has the 
# parameters: 
# df:the data frame
# GC_content: the column on df which contains the gc_content
# counts: the column on df, which contains read counts 
# start: the samllest value in GC-content * decimal_place
# end: the greatest value in GC-content * decimal_place
# step: distance between the points that should be taken
# decimal_place: in our case is 10000, because we have values from 0.345 to 0.52 
# and we want the for loop to iterate through all the points with distance
# of 0.0005 = decimal_step
# window_size: the size of the window from where we calculate the median

def gc_ncorrection(df,GC_content,start,end,step,decimal_place,window_size):
    window_size = window_size / 2
    gc_normlised_counts = np.zeros(len(df))
    decimal_step = step / decimal_place
    df['gc_normalised_normal_counts'] = gc_normlised_counts
    for i in range (start,end,step):
        df.loc[((GC_content >= (i/decimal_place)) & 
        (GC_content < ((i/decimal_place) + decimal_step))),'gc_normalised_normal_counts'] = df.loc[(GC_content >= (i/decimal_place)) & (GC_content < ((i/decimal_place) + decimal_step))].normal_counts / (df.loc[(GC_content >= ((i/decimal_place) - window_size)) & (GC_content < ((i/decimal_place) + decimal_step + window_size))].normal_counts.median()) * 2551.4

def gc_ccorrection(df,GC_content,start,end,step,decimal_place,window_size):
    window_size = window_size / 2
    gc_normlised_counts = np.zeros(len(df))
    decimal_step = step / decimal_place
    df['gc_normlised_cancer_counts'] = gc_normlised_counts
    for i in range (start,end,step):
        df.loc[((GC_content >= (i/decimal_place)) & (GC_content < ((i/decimal_place) + decimal_step))),'gc_normlised_cancer_counts'] = df.loc[(GC_content >= (i/decimal_place)) & (GC_content < ((i/decimal_place) + decimal_step))].cancer_counts / (df.loc[(GC_content >= ((i/decimal_place) - window_size)) & (GC_content < ((i/decimal_place) + decimal_step + window_size))].cancer_counts.median())* 1804.3

def gc_correction(df,GC_content,start,end,step,decimal_place,window_size):
    window_size = window_size / 2
    gc_normlised_counts = np.zeros(len(df))
    decimal_step = step / decimal_place
    df['gc_normlised_mixed_counts'] = gc_normlised_counts
    for i in range (start,end,step):
        df.loc[((GC_content >= (i/decimal_place)) & (GC_content < ((i/decimal_place) + decimal_step))),'gc_normlised_mixed_counts'] = df.loc[(GC_content >= (i/decimal_place)) & (GC_content < ((i/decimal_place) + decimal_step))].mixed_counts / (df.loc[(GC_content >= ((i/decimal_place) - window_size)) & (GC_content < ((i/decimal_place) + decimal_step + window_size))].mixed_counts.median())*2   



def gc_correction_withh_lowess(df, counts, frac):
    lowess=sm.nonparametric.lowess(df[counts],df['GC_content'],frac=frac)
    return (df[counts]/list(zip(*lowess))[1])*2

    
def comma_sep_data_processing(path):
    return(pd.read_csv(path))


def space_sep_data_processing(path):
    return(pd.read_csv(path,sep = '\s+'))

def simple_scatter_plot(x,y,x_label,y_label,titel):
    plt.scatter(x, y, s = 25)
    plt.title(titel, fontdict=None,fontsize=30, loc='center', pad=None)
    plt.xlabel(x_label, size = 25)
    plt.ylabel(y_label, size = 25)
    plt.show()




def main():
    parser  = argparse.ArgumentParser()
    parser.add_argument('-H','--normal_counts_file',metavar='', type = argparse.FileType('r'), help = "file path to counts df")
    parser.add_argument('-C','--cancer_counts_file',metavar='', type = argparse.FileType('r'), help = "file path to counts df")
    parser.add_argument('-B','--bins_file',metavar='', type = argparse.FileType('r'), help = "file path to bins")
    args = parser.parse_args()
    normal_df = comma_sep_data_processing(args.normal_counts_file)
    normal_df = normal_df.rename({'0': 'normal_counts'}, axis = 1)
    cancer_df = comma_sep_data_processing(args.cancer_counts_file)
    cancer_df = cancer_df.rename({'0': 'cancer_counts'}, axis = 1)
    bin_df = space_sep_data_processing(args.bins_file)
    df = pd.merge(bin_df,normal_df,on = 'bin_ind', how = 'inner')
    df = pd.merge(df,cancer_df,on = 'bin_ind', how = 'inner')
    df = df.drop(df[df.normal_counts > 10000].index)
    simple_scatter_plot(df['bin_ind'], df['cancer_counts'],'bins','cancer counts','Primary plot with genosomes')
    #remove genosomes
    df = df.drop(df[df.chr_ind == 20].index)
    df = df.drop(df[df.chr_ind == 21].index)
    simple_scatter_plot(df['bin_ind'], df['cancer_counts'],'bins','cancer counts','Primary plot without genosomes')






if __name__== "__main__" :
    main()