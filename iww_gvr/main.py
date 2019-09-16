
#######################################
#####  Python modules to load  ########
#######################################
import numpy as np
import math
from decimal import Decimal

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import matplotlib as mpl

dep_path='./' # adjust this path to the location of the meshtal_mod.py module 
import os
import re
import sys
from sys import path
path.append(dep_path)  

from copy import deepcopy # To copy a ww class instance in soft() and not modify the original ww
from iww_gvr import meshtal_module # It needs to be compatible with Python 3!!!
#from evtk.hl import gridToVTK # https://pypi.org/project/pyevtk/, pip install pyevtk
from pyevtk.hl import gridToVTK # https://pypi.org/project/pyevtk/, pip install pyevtk for alvaro works like this
from tqdm import tqdm        # Progress bars
from scipy import ndimage as nd # Filling holes in zoneDEF 'auto'
# import plotly.graph_objects as go # for interactive plotting
import time

from itertools import chain # used to desnest list

#######################################
#####  Weight Window  class ###########
#######################################

class ww_item:
    # Class constructor 
    def __init__(self, filename, X, Y, Z, nbins, No_Particle, ww1, eb1, ww2, eb2, dict):
        #>>> ww_item properties
        # - self.d    : dictionary
        # - self.X    : X discretization vector
        # - self.Y    : Y discretization vector
        # - self.Z    : Z discretization vector
        # - self.name : filename
        # - self.bins : No. of voxel per particle
        # - self.degree: covering model parameter
        #   -> self.degree[0] = zoneID (flagging of cells within the domain)
        #   -> self.degree[1] = factor (fraction of cell within the domain)
        # - self.vol  : voxel volume [cm3]
        # - self.dim  : voxel dimension [dX,dY,dZ] cm
        # - self.par  : ww set contained [1 or 2]
        # - self.min  : minimum values list        [for e in eb[0]@min|ParNo1,for e in eb[1]@min|ParNo2]
        # - self.max  : maximum values list        [for e in eb[0]@max|ParNo1,for e in eb[1]@max|ParNo2]
        # - self.eb   : ww energy bin list         [[]|ParNo1,[]|ParNo2]
        # --> @@@ Nested liste of numpy array@@@
        # [REMOVED] self.ww   : ww set list                [[]|ParNo1,[]|ParNo2]
        # [REMOVED] self.wwm  : ww set numpy array         [[k,j,i]|ParNo1,[k,j,i]|ParNo2] 
        # - self.wwe  : ww set list                [[[]e_i,[]e_i+1, ...,[]e_n]|ParNo1,[[]e_i,[]e_i+1, ...,[]e_n]|ParNo2]
        # - self.wwme : ww set numpy array         [[[k,j,i]e_i,[k,j,i]e_i+1, ....,,[k,j,i]e_n]|ParNo1,[[k,j,i]e_i,[k,j,i]e_i+1, ....,,[k,j,i]e_n ]|ParNo2]    
        # - self.ratio: max ratio of voxel with nearby values (shape as self.wwme)
        
        self.d  = dict
        
        self.X  = X
        self.Y  = Y
        self.Z  = Z
        
        self.name=filename
        
        self.bins=nbins
        
        self.degree=[]
        
        self.vol = (self.X[-1]-self.X[0])*(self.Y[-1]-self.Y[0])*(self.Z[-1]-self.Z[0])/self.bins
        
        self.dim = [(self.X[-1]-self.X[0])/(len(self.X)-1),(self.Y[-1]-self.Y[0])/(len(self.Y)-1),(self.Z[-1]-self.Z[0])/(len(self.Z)-1)]
        
        self.par = No_Particle    
        
        if self.par > 1:
            ww=[ww1,ww2]
            self.eb=[eb1,eb2]
         
        else:
            ww=[ww1]
            self.eb=[eb1]
        
        self.wwe = []
        values   = []
        
        for j in range (0,int(self.par)):
            for i in range (0,len(self.eb[j])):
                values.append(ww[j][((i+0)*int(self.bins)):((i+1)*int(self.bins))])
                
            self.wwe.append(values)
            values = []            

        self.wwme = []
        for j in range (0,int(self.par)):
            for i in range (0,len(self.eb[j])):
                vector=np.array(self.wwe[j][i])
                values.append(vector.reshape(len(self.Z)-1,len(self.Y)-1,len(self.X)-1))
                
            self.wwme.append(values)
            values = []
        
 
        self.ratio = []
        for j in range (0,int(self.par)):
            for i in range (0,len(self.eb[j])):
                vector=np.ones(int(self.bins))
                values.append(vector.reshape(len(self.Z)-1,len(self.Y)-1,len(self.X)-1))
                
            self.ratio.append(values)
            values = []
        
        self.min = []
        self.max = []
        for j in range (0,int(self.par)):
            self.min.append([min(l) for l in self.wwe[j]])
            self.max.append([max(l) for l in self.wwe[j]])
        
    # Function to print the information of the ww 
    def info(self):

        print ('\n The following WW file has been analysed:  '+self.name+'\n')

        Part_A='From'
        Part_B='To' 
        Part_C='No. Bins'

        print('{:>10}'.format('') + '\t'+Part_A.center(15,"-")+'\t'+Part_B.center(15,"-")+'\t'+Part_C.center(15,"-"))

        line_X='{:>10}'.format('X -->')  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Xo']))  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Xf'])) +'\t'+ '{:^15}'.format(len(self.X)-1)  
        line_Y='{:>10}'.format('Y -->')  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Yo']))  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Yf'])) +'\t'+ '{:^15}'.format(len(self.Y)-1) 
        line_Z='{:>10}'.format('Z -->')  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Zo']))  +'\t'+ '{:^15}'.format('{:8.2f}'.format(self.d['B2_Zf'])) +'\t'+ '{:^15}'.format(len(self.Z)-1)  

        print (line_X)
        print (line_Y)
        print (line_Z)

        print('\n The file contain {0} particle/s and {1} voxels!'.format(int(self.par),int(self.bins)*int(self.par)))
               
        if   (self.par  == 1):
            print('\n ***** Particle No.1 ****')
            print(' Energy[{0}]: {1}\n\n'.format(len(self.eb[0]),self.eb[0]))
        elif (self.par  == 2):
            print('\n ***** Particle No.1 ****')
            print(' Energy[{0}]: {1}'.format(len(self.eb[0]),self.eb[0]))

            print('\n ***** Particle No.2 ****')
            print(' Energy[{0}]: {1}\n\n'.format(len(self.eb[1]),self.eb[1]))
           
    # Function to normalize, (hole-)fill and soften the ww.    
    def soft(self,zoneID):
        flag = True
        while flag:
             soft = input(' Insert the softening factor: ')
             if ISnumber(soft):
                soft = float(soft)
                flag = False
             else: 
                print(' Please insert a number!')
                flag = True
        
        flag = True
        while flag:
             norm = input(' Insert the normalization factor: ')
             if ISnumber(norm):
                norm = float(norm)
                flag = False
             else: 
                print(' Please insert a number!')
                flag = True
        
        if   self.par  == 2:
            flag = True
            while flag:
                 NoParticle = input(' Insert the No.Particle to modify[0,1]: ')
                 if NoParticle == '0' or NoParticle == '1':
                    NoParticle = int(NoParticle)
                    flag = False
                 else: 
                    print(' Please insert 0 or 1!')
                    flag = True
        else:
            NoParticle = int(0)
        
        ww_out=[]
        ww_mod=self.wwme
        
        if len(zoneID) >1: # Hole-filling
            for g in range (0,len(self.eb[NoParticle])):
                z = np.tile(zoneID,(len(self.Z)-1,1,1)) # A 3d zoneID
                holes = ww_mod[NoParticle][g]==0
                holes = holes*z
                holes=holes==1
                ww_mod[NoParticle][g] = fill(ww_mod[NoParticle][g], holes)
                
        #if len(zoneID) >1 :                                         # Hole-filling
        #    value =[]
        #    ww_mod=self.wwme
        #    for g in range (0,len(self.eb[NoParticle])):
        #        for k in range (2, len(self.Z)-2):
        #            for j in range (2, len(self.Y)-2):
        #                for i in range (2, len(self.X)-2):
        #                    if self.wwme[NoParticle][g][k,j,i]==0:
        #                        if zoneID[j,i]==1:
        #                            BOX=[]
        #                            BOX=self.wwme[NoParticle][g][(k-2):(k+2),(j-2):(j+2),(i-2):(i+2)]
        #                            No_Values=np.size(np.nonzero(BOX)) 
        #                                
        #                            if No_Values>0:
        #                                del value
        #                                # *** To impose the average within the BOX matrix ***
        #                                value=np.sum(np.sum(BOX))/No_Values
        #                                # ** To impose the minimum value ***
        #                                # value = np.min(BOX[np.nonzero(BOX)]) 
        #                                ww_mod[NoParticle][g][k,j,i]=value            
                    
            
            # Modification of wwme
            for e in range (0,len(self.eb[NoParticle])):
                self.wwme[NoParticle][e]=np.power(ww_mod[NoParticle][e]*norm, soft)
            
            # Modification of wwe (denesting list wihth the itertools)
            for e in range (0,len(self.eb[NoParticle])): 
                step1 = self.wwme[NoParticle][e].tolist()
                step2 = list(chain(*step1))
                self.wwe[NoParticle][e] = list(chain(*step2))
                
        else:
            # Modification of wwme
            for e in range (0,len(self.eb[NoParticle])):
                self.wwme[NoParticle][e]=np.power(self.wwme[NoParticle][e]*norm, soft)
             
            # Modification of wwe (denesting list wihth the itertools)
            for e in range (0,len(self.eb[NoParticle])): 
                step1 = self.wwme[NoParticle][e].tolist()
                step2 = list(chain(*step1))
                self.wwe[NoParticle][e] = list(chain(*step2))
                
        return self
    
    # Function to add a ww set to the ww
    def add(self):
        flag = True
        while flag:
             soft = input(' Insert the softening factor: ')
             if ISnumber(soft):
                soft = float(soft)
                flag = False
             else: 
                print(' Please insert a number!')
                flag = True
        
        flag = True
        while flag:
             norm = input(' Insert the normalization factor: ')
             if ISnumber(norm):
                norm = float(norm)
                flag = False
             else: 
                print(' Please insert a number!')
                flag = True
                
        value = []
        # Modification of wwme
        for e in range (0,len(self.eb[0])):
            value.append(np.power(self.wwme[0][e]*norm, soft))
        
        self.wwme.append(value)
        
        value = []
        # Modification of wwe (denesting list wihth the itertools)
        for e in range (0,len(self.eb[0])): 
            step1 = self.wwme[1][e].tolist()
            step2 = list(chain(*step1))
            value.append(list(chain(*step2)))
        
        self.wwe.append(value)
        
        self.par=2
        self.d['B1_ni'] = 2
        self.d['B2_par']= False
        
        self.eb.append(self.eb[0])
        
        self.min.append([min(l) for l in self.wwe[1]])
        self.max.append([max(l) for l in self.wwe[1]])
        
        self.ratio.append(self.ratio[0])
        
        return self
    
    # Function to remove a ww set to the ww
    def remove(self):
        flag = True
        while flag:
             NoParticle = input(' Insert the weight windows set to remove[0,1]: ')
             if ISnumber(NoParticle):
                NoParticle = int(NoParticle)
                flag = False
             else: 
                print(' Please insert a number!')
                flag = True
        
            
        del self.min[NoParticle]
        del self.max[NoParticle]
        
        del self.wwe[NoParticle]
        del self.eb[NoParticle]
        
        del self.wwm[NoParticle]
        del self.wwme[NoParticle]        
        
        self.par = 1
        self.d['B1_ni'] = 1
        
        return self

#######################################
#### Functions for WW manipulation ####
#######################################

# Function to open and parse the ww file hence creating a ww class item
def load(InputFile):
    # To Import ww file

    # Line counter
    L_COUNTER = 0

    BLOCK_NO= 1 # This parameter define the BLOCK position in the file

    # Variables for BLOCK No.1
    B1_if = 0
    B1_iv = 0
    B1_ni = 0
    B1_nr = 0
    B1_ne = []  

    # Variables for BLOCK No.2
    B2_nfx = 0  
    B2_nfy = 0
    B2_nfz = 0
    B2_Xo  = 0
    B2_Yo  = 0
    B2_Zo  = 0
    B2_Xf  = 0
    B2_Yf  = 0
    B2_Zf  = 0
    B2_ncx = 0
    B2_ncy = 0
    B2_ncz = 0
    
    B2_X = False
    B2_Y = False
    B2_3 = False
    vec_coarse = [[],[],[]]
    vec_fine = [[],[],[]]
    
    # Variables for BLOCK No.3
    B3_eb1 = [] 
    ww1    = []

    B3_eb2 = [] 
    ww2    = []
    
    nlines = 0 # For the bar progress
    for line in open(InputFile).readlines(  ): nlines += 1
    bar = tqdm(unit=' lines read',desc=' Reading',total=nlines) 
    # Function to load WW
    with open(InputFile, "r") as infile:
        for line in infile:
            if BLOCK_NO==1:       
                # print ("Block No.1")
                if   (L_COUNTER==0):
                    info    = line[50:] 
                    line    = line[:50]

                    split=line.split()

                    B1_if = int(split[0])
                    B1_iv = int(split[1])
                    B1_ni = int(split[2])
                    B1_nr = int(split[3])

                    L_COUNTER += 1

                elif   (L_COUNTER==1):

                    split=line.split()

                    for item in split:
                        B1_ne.append(item)

                    if (B1_ni == 2) and (int(B1_ne[0])==0): 
                        B2_par= True   # ww2 set imposed in the ww1 position *** only photon case ***
                        B1_ni = 1      # As if only set was contained
                        B1_ne[0]=B1_ne[1]
                        del      B1_ne[1]
                    else:
                        B2_par=False  # ww2 set imposed in the ww2 position
                    
                    BLOCK_NO=2  # TURN ON SWITCH FOR BLOCK No. 2

                    L_COUNTER=0 # CLEAN L_COUNTER      

            elif BLOCK_NO==2:
                split=line.split()
                split = [float(i) for i in split]
                if   (L_COUNTER==0):
                    # print ("Block No.2")

                    B2_nfx = int(float(split[0]))
                    B2_nfy = int(float(split[1]))
                    B2_nfz = int(float(split[2]))
                    B2_Xo  = float(split[3])
                    B2_Yo  = float(split[4])
                    B2_Zo  = float(split[5])

                    L_COUNTER += 1

                elif   (L_COUNTER==1):
                    # print(line)
                    B2_ncx = float(split[0])
                    B2_ncy = float(split[1])
                    B2_ncz = float(split[2])
                    L_COUNTER += 1
                    B2_X = True
                                
                elif B2_X:
                    if len(split) == 4:
                        if vec_coarse[0] == []:
                            vec_coarse[0].append(split[0])                            
                        vec_fine[0].append(split[1])
                        vec_coarse[0].append(split[2])
                    if len(split) == 6:
                        if vec_coarse[0] == []:
                            vec_coarse[0].append(split[0]) 
                        vec_fine[0].append(split[1])
                        vec_coarse[0].append(split[2])
                        vec_fine[0].append(split[4])
                        vec_coarse[0].append(split[5])                        
                    if split[-1] == 1.0000 and len(split) != 6:
                        B2_X = False
                        B2_Y = True  
                  
                elif B2_Y:
                    if len(split) == 4:
                        if vec_coarse[1] == []:
                            vec_coarse[1].append(split[0])                            
                        vec_fine[1].append(split[1])
                        vec_coarse[1].append(split[2])
                    if len(split) == 6:
                        if vec_coarse[1] == []:
                            vec_coarse[1].append(split[0])
                        vec_fine[1].append(split[1])
                        vec_coarse[1].append(split[2])
                        vec_fine[1].append(split[4])
                        vec_coarse[1].append(split[5])                        
                    if split[-1] == 1.0000:
                        B2_Y = False
                        B2_Z = True
                        
                elif B2_Z:
                    if len(split) == 4:
                        if vec_coarse[2] == []:
                            vec_coarse[2].append(split[0])                            
                        vec_fine[2].append(split[1])
                        vec_coarse[2].append(split[2])
                    if len(split) == 6:
                        if vec_coarse[2] == []:
                            vec_coarse[2].append(split[0])
                        vec_fine[2].append(split[1])
                        vec_coarse[2].append(split[2])
                        vec_fine[2].append(split[4])
                        vec_coarse[2].append(split[5])                        
                    if split[-1] == 1.0000:
                        B2_Z = False
                        BLOCK_NO   = 3  # TURN ON SWITCH FOR BLOCK No. 3   
                        
                        nbins = float(B2_nfx) * float(B2_nfy) * float(B2_nfz)
                        X = [vec_coarse[0][0]]
                        for i in range(1,len(vec_coarse[0])):
                            X = np.concatenate((X,np.linspace(X[-1],vec_coarse[0][i],vec_fine[0][i-1]+1)[1:]))
                        B2_Xf = X[-1]
                        
                        Y = [vec_coarse[1][0]]
                        for i in range(1,len(vec_coarse[1])):
                            Y = np.concatenate((Y,np.linspace(Y[-1],vec_coarse[1][i],vec_fine[1][i-1]+1)[1:])) 
                        B2_Yf = Y[-1]
                        
                        Z = [vec_coarse[2][0]]
                        for i in range(1,len(vec_coarse[2])):
                            Z = np.concatenate((Z,np.linspace(Z[-1],vec_coarse[2][i],vec_fine[2][i-1]+1)[1:]))
                        B2_Zf = Z[-1]
                        
                        L_COUNTER = 0
                        
            elif BLOCK_NO==3:
                split=line.split()
                if L_COUNTER == 0:
                    for item in split:
                        B3_eb1.append(float(item))

                    if len(B3_eb1)  == int(B1_ne[0]):
                        L_COUNTER +=1

                elif L_COUNTER == 1:
                    for item in split:
                        ww1.append(float(item))
                    if len(ww1)  == (nbins*int(B1_ne[0])):
                        L_COUNTER +=1       

                elif L_COUNTER == 2:
                    for item in split:
                        B3_eb2.append(float(item))

                    if len(B3_eb2)  == int(B1_ne[1]):
                        L_COUNTER +=1

                elif L_COUNTER == 3:
                    for item in split:
                        ww2.append(float(item))
                    if len(ww2)  == (nbins*int(B1_ne[1])):
                        L_COUNTER +=1
    
            bar.update()
    bar.close()    
    # WW dictionary
    dict    = {}
        
    dict    = {'B1_if':B1_if, 'B1_iv':B1_iv, 'B1_ni':B1_ni, 'B1_nr':B1_nr, 
                'B1_ne':B1_ne,'B2_Xo':B2_Xo,'B2_Yo':B2_Yo,'B2_Zo':B2_Zo,
                'B2_Xf':B2_Xf,'B2_Yf':B2_Yf,'B2_Zf':B2_Zf, 'B2_par':B2_par,
                'vec_coarse':vec_coarse, 'vec_fine':vec_fine}
    
    if B1_ni > 1:
        ww = ww_item (InputFile, X, Y, Z, nbins, B1_ni, ww1, B3_eb1, ww2, B3_eb2, dict)
    else:        
        ww = ww_item (InputFile, X, Y, Z, nbins, B1_ni, ww1, B3_eb1, 0, 0, dict)       
    return ww

# Function to export the ww set in VTK or to the MCNP input format
def write(wwdata,wwfiles,index):
    
    print(write_menu)
     
    ans,fname = answer_loop('write')
    
    if ans == 'end':
        sys.exit('\n Thanks for using this utility tools! See you soon!')
    else:
        outputFile = wwfiles[index]+'_2write'
        ww=wwdata[index]
        
    if   ans == 'vtk'  :   # To export to VTK
        
        # Create and fill the "cellData" dictionary 
        dictName = []
        dictValue= []
        for j in range (0,int(ww.par)):
            for i in range (0,len(ww.eb[j])):
                dictValue.append(ww.wwe[j][i])  
                
                if ww.d['B2_par']==True:
                    dictName.append('WW_ParNo'+str(j+2)+'_E='+str(ww.eb[j][i])+'_MeV')
                else:
                    dictName.append('WW_ParNo'+str(j+1)+'_E='+str(ww.eb[j][i])+'_MeV')
        
        if max([e.max() for e in ww.ratio[0]]) != 1: # To be improved just to check if matrix is all one.
            for j in range (0,int(ww.par)):
                for e in range (0,len(ww.eb[j])):
                    dictValue.append(ww.ratio[j][e])                            
                    if ww.d['B2_par']==True:
                        dictName.append('[RATIO]_WW_ParNo'+str(j+2)+'_E='+str(ww.eb[j][i])+'_MeV')
                    else:
                        dictName.append('[RATIO]_WW_ParNo'+str(j+1)+'_E='+str(ww.eb[j][i])+'_MeV')
                    
        for i in range (0,len(dictValue)):
            dictValue[i]=np.reshape(dictValue[i],int(ww.bins)) 
        
        zipDict  =   zip(dictName, dictValue)
        cellData =   dict(zipDict)

        # Export to VTR format
        gridToVTK("./"+wwfiles[index], np.array(ww.X), np.array(ww.Y), np.array(ww.Z), cellData )
        print(' VTK... written!')
        
    elif ans == 'wwinp':   # To export to WW MCNP format
        with open(outputFile, "w") as outfile:
        
            line_A='{:>10}'.format('{:.0f}'.format(ww.d['B1_if']))
            line_B='{:>10}'.format('{:.0f}'.format(ww.d['B1_iv']))
            if ww.d['B2_par']==True:
                line_C='{:>10}'.format('{:.0f}'.format(ww.d['B1_ni']+1))
            else:
                line_C='{:>10}'.format('{:.0f}'.format(ww.d['B1_ni'])) 
            line_D='{:>10}'.format('{:.0f}'.format(ww.d['B1_nr']))  
            outfile.write(line_A+line_B+line_C+line_D+'\n')
            
            
            if    (ww.par == 1) and ww.d['B2_par']==False:
                line_A='{:>10}'.format('{:.0f}'.format(len(ww.eb[0])))
                line_B='{:>10}'.format('')
            elif  (ww.par == 1) and ww.d['B2_par']==True:
                line_A='{:>10}'.format('{:.0f}'.format(0))
                line_B='{:>10}'.format('{:.0f}'.format(len(ww.eb[0])))        
            else: 
                line_A='{:>10}'.format('{:.0f}'.format(len(ww.eb[0])))
                line_B='{:>10}'.format('{:.0f}'.format(len(ww.eb[1])))
                
            outfile.write(line_A+line_B+'\n')  
            
            line_A= '{:>9}'.format('{:.2f}'.format(len(ww.X)-1))
            line_B='{:>13}'.format('{:.2f}'.format(len(ww.Y)-1))
            line_C='{:>13}'.format('{:.2f}'.format(len(ww.Z)-1))
            line_D='{:>13}'.format('{:.2f}'.format(ww.d['B2_Xo']))
            line_E='{:>13}'.format('{:.2f}'.format(ww.d['B2_Yo']))
            line_F='{:>12}'.format('{:.2f}'.format(ww.d['B2_Zo']))
            outfile.write(line_A+line_B+line_C+line_D+line_E+line_F+'    \n')
            
            line_A= '{:>9}'.format('{:.2f}'.format(len(ww.d['vec_coarse'][0])-1))
            line_B='{:>13}'.format('{:.2f}'.format(len(ww.d['vec_coarse'][1])-1))
            line_C='{:>13}'.format('{:.2f}'.format(len(ww.d['vec_coarse'][2])-1))
            line_D='{:>13}'.format('{:.2f}'.format(1))  
            outfile.write(line_A+line_B+line_C+line_D+'    \n')
            
            l=[]
            for i in range(len(ww.d['vec_coarse'][0])):
                l.append(ww.d['vec_coarse'][0][i])
                try:
                    l.append(ww.d['vec_fine'][0][i])
                except:
                    pass
            s = ''

            for i in l:
                s = s + ' {: 1.5e}'.format(i)
                if len(s.split()) == 6:
                    outfile.write(s+'\n')
                    s = ' {: 1.5e}'.format(1)
                if len(s.split()) == 3:
                    s = s +' {: 1.5e}'.format(1)
            outfile.write(s+'\n')
            
            l=[]
            for i in range(len(ww.d['vec_coarse'][1])):
                l.append(ww.d['vec_coarse'][1][i])
                try:
                    l.append(ww.d['vec_fine'][1][i])
                except:
                    pass
            s = ''
            for i in l:
                s = s + ' {: 1.5e}'.format(i)
                if len(s.split()) == 6:
                    outfile.write(s+'\n')
                    s = ' {: 1.5e}'.format(1)
                if len(s.split()) == 3:
                    s = s +' {: 1.5e}'.format(1)
            outfile.write(s+'\n')
            
            l=[]
            for i in range(len(ww.d['vec_coarse'][2])):
                l.append(ww.d['vec_coarse'][2][i])
                try:
                    l.append(ww.d['vec_fine'][2][i])
                except:
                    pass
            s = ''
            for i in l:
                s = s + ' {: 1.5e}'.format(i)
                if len(s.split()) == 6:
                    outfile.write(s+'\n')
                    s = ' {: 1.5e}'.format(1)
                if len(s.split()) == 3:
                    s = s +' {: 1.5e}'.format(1)
            outfile.write(s+'\n')
            
           
            # ********* Writing of WW values *********
            for par in range (0,ww.par):
                jj       = 0
                value    = 0
                line_new = []
                counter  = 0       
                
                # Writing of energy bins
                for item in ww.eb[par]:
                                     
                    if  jj<5: 
                        line_new='{:>13}'.format('{:.4e}'.format(item))
                        outfile.write(line_new)
                        jj=jj+1
                        if counter == len(ww.eb[par])-1:
                             outfile.write('\n')
                             jj=0
                             counter  = 0  
                    else:
                        line_new='{:>13}'.format('{:.4e}'.format(item))
                        outfile.write(line_new)
                        outfile.write('\n')
                        jj=0
                    counter = counter + 1
                
                jj       = 0
                value    = 0
                line_new = []
                counter  = 0 
                
                # Writing of ww bins
                for e in range (0,len(ww.eb[par])):
                    bar = tqdm(unit=' lines',desc=' Writing energy bin',total=len(ww.wwe[par][e]))
                    for item in ww.wwe[par][e]:
                        bar.update()
                        # print(type(item))
                        # print(item)
                        value    = float(item)
                        if  jj<5: 
                            line_new='{:>13}'.format('{:.4e}'.format(value))
                            outfile.write(line_new)
                            jj=jj+1
                            
                            if counter == len(ww.wwe[par][e])-1:
                                outfile.write('\n')
                                jj=0
                                counter  = 0
                            else:
                                counter = counter + 1
                                                         
                        else:
                            line_new='{:>13}'.format('{:.4e}'.format(value))
                            outfile.write(line_new)
                            outfile.write('\n')
                            jj=0
                            
                            if counter == len(ww.wwe[par][e])-1:
                                # outfile.write('\n')
                                jj=0
                                counter  = 0 
                            else:
                                counter = counter + 1
                    bar.close()
        print(' File... written!')

# Function for analysing the WW file
def analyse(self, zoneID, factor):
    RATIO_EVA = []
    
    for p in range (0,self.par):
        # cdef list RATIO         = []
        # RATIO_MAX     = []
        
        ww_neg        = []
        ww_neg_pos    = []
        
        ww_noZERO     = []
        ww_noZERO_pos = []
        
        for e in range (0,len(self.eb[p])):    
        
            ww_noZERO_pos = np.where(self.wwme[p][e] > 0)
            ww_noZERO.append(len(ww_noZERO_pos[0])/(self.bins*factor))
                
            ww_neg_pos = np.where(self.wwme[p][e] < 0)
                
            for item in range (0,len(ww_neg_pos[0])):
                # Appending the position
                # ww_neg.append([ww_neg_pos[0][item],ww_neg_pos[1][item],ww_neg_pos[2][item]])     
                
                # Appending only the number
                ww_neg.append(self.wwme[p][e][ww_neg_pos[0][item],ww_neg_pos[1][item],ww_neg_pos[2][item]])          
            
            
            bar = tqdm(unit=' Z slices',desc=' Ratios',total=int(len(self.Z))-1)    
            # To be improved
            extM = extend_matrix(self.wwme[p][e])
            for k in range (1, (int(len(self.Z)))):
                for j in range (1, (int(len(self.Y)))):
                    for i in range (1, (int(len(self.X)))):
                        if (extM[k,j,i]>0):
                            self.ratio[p][e][k-1,j-1,i-1] = max([extM[k+1,j,i],extM[k-1,j,i],extM[k,j+1,i],extM[k,j-1,i], extM[k,j,i+1], extM[k,j,i-1]])/extM[k,j,i]
                bar.update()
                            #RATIO=[]
            bar.close()
            
            ### <<<<  it works but it is slower >>>>>>####
            # it   =  np.nditer(self.wwme[p][e], flags=['multi_index'])
            # 
            # while not it.finished:
            #     k = it.multi_index[0]
            #     j = it.multi_index[1]
            #     i = it.multi_index[2]
            #     
            #     try:
            #         if it[0]>0:
            #                        
            #             self.ratio[p][e][k,j,i] = max([self.wwme[p][e][k+1,j,i],self.wwme[p][e][k-1,j,i],self.wwme[p][e][k,j+1,i],self.wwme[p][e][k,j-1,i], self.wwme[p][e][k,j,i+1], self.wwme[p][e][k,j,i-1]])/self.wwme[p][e][k,j,i]
            #                        
            #             
            #     except:
            #         self.ratio[p][e][k,j,i] = 1
            #     
            #     it.iternext()
                
        
        
        # RATIO_MAX=max([e.max() for e in self.ratio[p]])
        # RATIO_MAX=[e.max() for e in self.ratio[p]]
        #RATIO_MAX=max(RATIO_MAX)
        #print(RATIO_MAX)
        RATIO_EVA.append([[e.max() for e in self.ratio[p]],sum(ww_noZERO)/len(self.eb[p]),ww_neg])
            
        ww_neg=[]
        ww_neg_pos=[]    
    
    # To create the ratio histogram analysis
    for e in range (0, len(self.ratio[p])):
        font = {'family': 'serif',
        'color':  'darkred',
        'weight': 'normal',
        'size': 16,
        }

        
        x_axis = np.logspace(0, 6, num=21)
        y_axis = []
        
        for i in range (0,len(x_axis)-1):
            y_axis.append(len(np.where(np.logical_and(self.ratio[p][e]>=x_axis[i], self.ratio[p][e]<x_axis[i+1]))[0]))
                
        fig, ax = plt.subplots()
        ax.bar(x_axis[:-1], y_axis, width=np.diff(x_axis),log=True,ec="k", align="edge")
        ax.set_xscale("log")
        plt.xlabel('max ratio with nearby cells', fontdict=font)
        plt.ylabel('No.bins', fontdict=font)
        plt.title (self.name+'_ParNo.'+str(p+1)+'_'+'E'+'='+str(self.eb[p][e])+'MeV', fontdict=font)
        
        # Tweak spacing to prevent clipping of ylabel
        plt.subplots_adjust(left=0.15)
        fig.savefig(self.name+'_ParNo.'+str(p+1)+'_'+'E'+'='+str(self.eb[p][e])+'MeV'+'_Ratio_Analysis.jpg')
        
    # Print in screen the ww analysis
    print ('\n The following WW file has been analysed:  '+self.name)

    for i in range (0,self.par):
        if (len(RATIO_EVA[i][2]) > 0):
            flag ='YES'
            flag = flag +'['+ str(len(RATIO_EVA[i][2]))+ ']' + ' <<' +str(RATIO_EVA[i][2]) +  '>>'
        else:
            flag ='NO'
        
        title = 'Par.No ' + str(i+1)
        print('\n '+title.center(40,"-")+'\n')
        
        print(' Min Value       : ' + str(self.min[i]))
        print(' Max Value       : ' + str(self.max[i]))
        print(' Max Ratio       : ' + str(RATIO_EVA[i][0]))
        print(' No.Bins>0 [%]   : ' + '{:5.2f}'.format(RATIO_EVA[i][1]*100))
        print(' Neg.Value       : ' + flag )
        print(' Voxel Dim[X,Y,Z]: ' +  str(self.dim) + ' cm')
        print(' Voxel Vol[cm3]  : ' + '{:1.4e}'.format(self.vol)+ '\n')
        print(' '+'-'*40+'\n')
        
    return self, RATIO_EVA

# Function to the define the zone of covering of the ww
def zoneDEF(self,degree):

    if degree == 'all': # The ww is completely contained in the model domain
        zoneID=[]
        zoneID=np.ones((int(len(self.Y)-1),int(len(self.X)-1)))
        
        factor = 1
    
    elif degree == 'auto':
        zoneID = np.zeros((int(len(self.Y)-1),int(len(self.X)-1)))
        non_zero_index = [i[3:] for i in np.argwhere(self.wwme)] # creates a list of indices of j,i if there is a non-zero value
        non_zero_index = np.unique(non_zero_index,axis=0)        # deletes repeated indices
        for j, i in non_zero_index:
            zoneID[j][i] = 1
        zoneID = nd.binary_fill_holes(zoneID).astype(int) # Fills all the holes in zoneID
        # plot the ZONE
        cmap = plt.get_cmap('jet', 1064)
        # tell imshow about color map so that only set colors are used
        img = mpl.pyplot.imshow(zoneID, cmap = cmap, norm=colors.Normalize(0, 1))
        factor = sum (sum(zoneID))/ (int(len(self.Y)-1)*int(len(self.X)-1))
        print(' zoneID automatically generated!')
        
    else:             # The ww is partialy contained in the model domain
        
        # PR - Evaluation of the WW
        zoneID=[]
        zoneID=np.zeros((int(len(self.Y)),int(len(self.X))))

        for j in range (0, int(len(self.Y))):
            for i in range (0, int(len(self.X))):
                if np.absolute(np.arctan(self.Y[j]/self.X[i]))<(degree/2/180*math.pi):
                    zoneID[j,i]=1

        # plot the ZONE
        cmap = plt.get_cmap('jet', 1064)

        # tell imshow about color map so that only set colors are used
        img = mpl.pyplot.imshow(zoneID, cmap = cmap, norm=colors.Normalize(0, 1))

        # problem here -->> mpl.pyplot.show(block = False) 

        # Factor which evaluates the simulation domain
        factor = sum (sum(zoneID))/ (int(len(self.Y))*int(len(self.X)))
    
    return zoneID, factor

# Function for "plot" option
def plot(self):
                
    while True:
        PLANE = input(" Select the plane[X,Y,Z] :")
        
        if PLANE == 'X' or PLANE == 'Y' or PLANE == 'Z':
            break
        else:
            print(' not expected keyword')

    while True:
        
        if    PLANE == 'X':
            INFO_QUOTE  = '[X-->' + str(self.X[0]) +', '+ str(self.X[-1]) +' cm]'
        elif PLANE == 'Y':
            INFO_QUOTE  = '[Y-->' + str(self.Y[0]) +', '+ str(self.Y[-1]) +' cm]'
        elif PLANE == 'Z':    
            INFO_QUOTE  = '[Z-->' + str(self.Z[0]) +', '+ str(self.Z[-1]) +' cm]'    
        
        while True:
            PLANE_QUOTE = input(' Select the quote ' + INFO_QUOTE + ':')
            if  ISnumber(PLANE_QUOTE):    
                PLANE_QUOTE = float (PLANE_QUOTE)
                break
            else:
                print(' Please insert a numerical value')
            
        if PLANE == 'X':
            if self.X[0] <= PLANE_QUOTE <= self.X[-1]:
                break
            else:
                print(' Value outside the range')
        elif PLANE == 'Y':
            if self.Y[0] <= PLANE_QUOTE <= self.Y[-1]:
                break
            else:
                print(' Value outside the range')          
        elif PLANE == 'Z':
            if self.Z[0] <= PLANE_QUOTE <= self.Z[-1]:
                break
            else:
                print(' Value outside the range')          

    if self.par == 1:
        PAR_Select = 0

        if len(self.eb[PAR_Select]) > 1:
            while True:
                ENERGY = input(" Select the energy [MeV]:")
                
                if self.eb[PAR_Select][0] <= float(ENERGY) <= self.eb[PAR_Select][-1]:
                    break
                else:
                    print(' Value outside the range')
        else:
            ENERGY=self.eb[PAR_Select][0]

    else:
        while True:
            PAR_Select = input(" Select the particle [0,1] :")
            PAR_Select = int(PAR_Select)

            if PAR_Select == 0 or PAR_Select == 1:
                break
            else:
                print(' Wrong value')        
    
        if len(self.eb[PAR_Select]) > 1:
            while True:
                ENERGY = input(" Select the energy [MeV]:")
                
                if self.eb[PAR_Select][0] <= float(ENERGY) <= self.eb[PAR_Select][-1]:
                    break
                else:
                    print(' Value outside the range')
        else:
            ENERGY=self.eb[PAR_Select][0]  
    
    plot_ww(self, PAR_Select, PLANE, PLANE_QUOTE,ENERGY)

# Function to plot the ww with specific user sets
def plot_ww(self, PAR_Select, PLANE, PLANE_QUOTE, ENERGY):
    if (PAR_Select>self.par):
        print(' Error --> No. particle outside range!')
        flag=False

    else:
        flag=True
               
        WW_P=[]

        PE = closest(self.eb[PAR_Select],float(ENERGY))
        PE_STR = str(self.eb[PAR_Select][PE])
        
        # WW_P=np.array(self.ww[PAR_Select][int(PE*self.bins):int((PE+1)*self.bins)])  
        WW_P=np.array(self.wwe[PAR_Select][PE])   
        
        WW_P=WW_P.reshape(len(self.Z)-1,len(self.Y)-1,len(self.X)-1)
        WW_P=np.flipud(WW_P)    


        if flag:
            fig = plt.figure()

            if (PLANE=='X'):
                if ((PLANE_QUOTE > self.X[-1] ) or ( PLANE_QUOTE < self.X[0])):
                    print(' Error --> X dimension outside range!')
                    flag=False
                else:
                    DIM = closest(self.X, PLANE_QUOTE)
                    extent = [self.Y[0],self.Y[-1],self.Z[0],self.Z[-1]]
                    vals = WW_P [:,:, DIM-1]   # Slice in X  
                    plt.xlabel("Y")
                    plt.ylabel("Z")
            
            elif (PLANE=='Y'):
                if ((PLANE_QUOTE > self.Y[-1] ) or ( PLANE_QUOTE < self.Y[0])):
                    print(' Error --> Y dimension outside range!')
                    flag=False
                else:
                    DIM = closest(self.Y, PLANE_QUOTE)
                    extent = [self.X[0],self.X[-1],self.Z[0],self.Z[-1]]                    
                    vals = WW_P [:, DIM-1,:]   # Slice in Y    
                    plt.xlabel("X")
                    plt.ylabel("Z")
            
            elif (PLANE=='Z'):
                if ((PLANE_QUOTE > self.Z[-1] ) or ( PLANE_QUOTE < self.Z[0])):
                    print(' Error --> Z dimension outside range!')
                    flag=False
                else:
                    DIM = closest(self.Z, PLANE_QUOTE)
                    extent = [self.X[0],self.X[-1],self.Y[0],self.Y[-1]]
                    vals = WW_P [DIM-1,:,:]  # Slice in Z
                    plt.xlabel("X")
                    plt.ylabel("Y")
                    
                    # Plotly solution to be completed
                    # za=[]
                    # 
                    # for i in range(0,len(self.Y)-1):
                    #     za.append(vals[i,:])
                    # 
                    # fig_plotly = go.Figure(data = go.Contour(z=za,y=self.Y,x=self.X,colorscale='Jet'))
                    # fig_plotly.write_html('first_figure.html', auto_open=True)
            if flag:
                
                # Using numpy features to find min and max
                f= np.array(vals.tolist())
                vmin = np.min(f[np.nonzero(f)])
                vmax = np.max(f[np.nonzero(f)])
                nColors = len(str(int(vmax/vmin)))*2
                if vmin > 0 :
                    cax=mpl.pyplot.imshow(vals, cmap = plt.get_cmap('jet', nColors), norm=colors.LogNorm(vmin, vmax), extent = extent)
                else:
                    cax=mpl.pyplot.imshow(vals, cmap = plt.get_cmap('jet', nColors), vmin = vmin, vmax = vmax, extent = extent)    
                              
                
                
                cbar=fig.colorbar(cax);

                plt.title(self.name+'@'+PLANE+'='+str(PLANE_QUOTE)+'cm')
                
                if PAR_Select == 0 and self.d['B2_par']==True:
                    fig.savefig(self.name+str(PAR_Select+1)+'_'+PLANE+'='+str(PLANE_QUOTE)+'cm'+'_'+'E'+'='+PE_STR+'MeV'+'_ParNo.'+'.jpg')
                else:
                    fig.savefig(self.name+str(PAR_Select)+'_'+PLANE+'='+str(PLANE_QUOTE)+'cm'+'_'+'E'+'='+PE_STR+'MeV'+'.jpg')  
                # problem here -->mpl.pyplot.show(block = False) 
                print (' Plot...Done!\n')

# Function to create a ww starting from the datafile imported and using the Global Variance Reduction    
def gvr_soft(gvrname):
    
    while True:
        try:
            beta = float(input(' Insert the maximum splitting ratio (''beta''): '))
            break
        except:
            print(' Please insert a number!')
            
    while True:
        try:
            soft = float(input(' Insert the softening factor: '))
            break
        except:
            print(' Please insert a number!')
            
    while True:
        try:
            fname = input(' Enter the meshtally file to load:')
            with open(fname,'r') as infile:
                if 'Mesh Tally Number' in infile.read(): # To improve
                    break
        except:
            print(' Not a valid file')
            
    mesh=meshtal_module.Meshtal(fname)
    print(' The following tallies have been found:\n')
    for key in mesh.mesh.keys():
        print(' ',key,' \n')
        #mesh.mesh[key].print_info() # Prints the information of all the tallies present
    
    while True:
        try:
            k = int(input(' Choose the mesh tally to use for the GVR: '))
            m = mesh.mesh[k]
            break
        except:
            print(' Not valid')
            
    X = m.dims[3]+m.origin[3]
    Y = m.dims[2]+m.origin[2]
    Z = m.dims[1]+m.origin[1]
    vec_coarse = [X,Y,Z]
    vec_fine = [[1 for i in range(len(vec_coarse[0])-1)],[1 for i in range(len(vec_coarse[1])-1)],[1 for i in range(len(vec_coarse[2])-1)]]
    nbins = (len(X)-1)*(len(Y)-1)*(len(Z)-1)
    nPar = 1
    eb = [100]
    m.readMCNP(mesh.f)
    ww1 = m.dat.flatten()        
    d = {'B1_if': 1,
         'B1_iv': 1,
         'B1_ne': ['1'],
         'B1_ni': 1,
         'B1_nr': 10,
         'B2_Xf': m.dims[3][-1]+m.origin[3],
         'B2_Xo': m.origin[3],
         'B2_Yf': m.dims[2][-1]+m.origin[2],
         'B2_Yo': m.origin[2],
         'B2_Zf': m.dims[1][-1]+m.origin[1],
         'B2_Zo': m.origin[1],
         'B2_par': False,
         'vec_coarse':vec_coarse,
         'vec_fine':vec_fine}
    gvr = ww_item(gvrname,X,Y,Z,nbins,nPar,ww1,eb,[],[],d) # A ww skeleton is generated with the info from the mesh file
    gvr.info()    
    
    while True:
        degree = input(' Insert the toroidal coverage of the model [degree, all, auto] for Hole Filling approach or [No]: ')
        try: 
            degree = float(degree)
            break
        except: pass
        if degree in ['all','No','auto']: break
    if degree == 'No': zoneID = []
    else: zoneID,factor = zoneDEF(gvr,degree)
            
    ww_inp = np.zeros(np.shape(gvr.wwme[0][0]))
    fluxinp_max = np.max(gvr.wwme[0][0])
    bar = tqdm(unit=' Z slices',desc=' GVR',total=len(gvr.Z)-1)
    for k in range (0, len(gvr.Z)-1):
        for j in range (0, len(gvr.Y)-1):
            for i in range (0, len(gvr.X)-1):
                ww_inp[k,j,i]=np.power(gvr.wwme[0][0][k,j,i]/fluxinp_max*(2/(beta+1)), soft) # Van Vick/A.Davis
        bar.update()
    bar.close()

    if len(zoneID) > 0: # Hole filling (Super efficient but the values are not averaged or interpolated)
        z = np.tile(zoneID,(len(gvr.Z)-1,1,1)) # A 3d zoneID
        holes = ww_inp==0
        holes = holes*z               # Only the places that are inside the zoneID and have a value of zero in ww_inp will be filled
        holes = holes==1
        ww_inp = fill(ww_inp,holes)   # The hole filling gives to the holes the same value as the nearest non-zero value            
    gvr.wwme[0][0] = ww_inp
    # Modification of wwe (denesting list wihth the itertools)
    step1 = gvr.wwme[0][0].tolist()
    step2 = list(chain(*step1))
    gvr.wwe[0][0] = list(chain(*step2))

    # Update of characteristics of weight window set
    emax=[gvr.eb[0][-1]]
    del gvr.eb
    del gvr.min, gvr.max
    
    gvr.min=[ww_inp.min()] # As there is only one bin in the gvr matrix
    gvr.max=[ww_inp.min()] # As there is only one bin in the gvr matrix
                    
    gvr.eb=[emax]
        
    gvr.par = 1
    gvr.d['B1_ni'] = 1        
    gvr.d['B1_ne'] = 1        

    return gvr

# THE WW SHOULD BE ANALYSED BEFORE USING. Function to mitigate long history par. by reducing the values that produce a too high ratio    
def mitigate(ww,maxratio):
    for p in range (0,ww.par):
        for e in range (0,len(ww.eb[p])):
            extM = extend_matrix(ww.wwme[p][e])
            while len(np.argwhere(ww.ratio[p][e]>=maxratio))>0:
                idxs = np.argwhere(ww.ratio[p][e]>=maxratio)
                print(' Found these many values with a ratio higher than the maximum: ',len(idxs))
                for idx in idxs:
                    neig = [extM[idx[0]+0,idx[1]+1,idx[2]+1],
                            extM[idx[0]+2,idx[1]+1,idx[2]+1],
                            extM[idx[0]+1,idx[1]+0,idx[2]+1],
                            extM[idx[0]+1,idx[1]+2,idx[2]+1],
                            extM[idx[0]+1,idx[1]+1,idx[2]+0],
                            extM[idx[0]+1,idx[1]+1,idx[2]+2]]
                    neig = [x for x in neig if x>0]
                    #ww.wwme[p][e][tuple(idx)] = (max(neig)+min(neig))/2.0
                    ww.wwme[p][e][tuple(idx)] = (max(neig))/(maxratio*0.9) # Reduce the ww value to one right below the maxim ratio allowed
                    ww.ratio[p][e][tuple(idx)] = max(neig)/ww.wwme[p][e][tuple(idx)]
    
    for NoParticle in range (0,ww.par):    
        # Modification of wwe (denesting list wihth the itertools)
        for e in range (0,len(ww.eb[NoParticle])): 
            step1 = ww.wwme[NoParticle][e].tolist()
            step2 = list(chain(*step1))
            ww.wwe[NoParticle][e] = list(chain(*step2))
        
# Function for "operate" option
def operate():
    clear_screen()
    print(operate_menu)
     
    ans,fname = answer_loop('operate')
    
    if ans == 'end':
        sys.exit('\n Thanks for using this utility tools! See you soon!')        
    else:
        index  = selectfile(wwfiles)
       
    if   ans == 'soft':
       
        flag = True
        while flag:
             HF = input(' Hole Filling approach [Yes, No]: ')
             if HF =='Yes' or HF =='No' :
                flag = False
                if HF == 'Yes':
                    if not wwdata[index].degree:
                        while True:
                            degree = input(" Insert the toroidal coverage of the model [degree, all, auto]: ")
                            
                            if degree.isdigit():
                                degree = float(degree)/2
                                break
                            elif degree == 'all':
                                break
                            elif degree == 'auto':
                                break
                            else:
                                print(' Please insert one of the options!')
                        zoneID, factor = zoneDEF(wwdata[index],degree)
                        wwdata[index].degree.append(zoneID)
                        wwdata[index].degree.append(factor)
                    else:
                        zoneID = wwdata[index].degree[0]
                        factor = wwdata[index].degree[1]
                else:
                    zoneID, factor = [], []
             else: 
                print(' Please insert Yes or No!')
                flag = True      
                
        
        copy = deepcopy(wwdata[index])
        
        ww_out = copy.soft(zoneID)
        ww_out.name = fname
        flag   = True 
        
        print(' Softening done!\n')

    elif ans == 'add':
       if wwdata[index].par == 2:
           print(' Impossible to add a weight window set: already 2 sets are present!\n')
           flag   = False
           ww_out = None
       else:  
           ww_out      = wwdata[index].add()
           ww_out.name = fname
           flag        = True
           print(' Additional weight window set incorporated!\n')           

    elif ans == 'mit':
        while True:
            maximum_ratio = input(' Insert maximum ratio allowed: ')
            try:
                maximum_ratio = float(maximum_ratio)
                break
            except:
                print(' Not a valid number')
            
        copy = deepcopy(wwdata[index])
        mitigate(copy,maximum_ratio)
        ww_out = copy
        ww_out.name = fname
        flag   = True 
        print(' Mitigation completed!')
        
    elif ans == 'rem':
    
       if wwdata[index].par == 1:
           print(' Impossible to remove a weight window set: only 1 set is present!\n')
           flag   = False
           ww_out = None
       else:  
           ww_out      = wwdata[index].remove()
           ww_out.name = fname
           flag        = True
           print(' Weight window set removed!\n')  
         
    return ww_out,fname, flag


#######################################
###### Menu Supporting Functions ######
#######################################

# Function which defines the main answer loop
def answer_loop(menu):
    pkeys = ['open','info','write','analyse','plot','operate','end','gvr']
    wkeys = ['wwinp','vtk','end']
    okeys = ['add','rem','soft','flip','mit','end']
    menulist = {'principal':pkeys, 'write':wkeys, 'operate':okeys}  
    while True:
        ans = input(" enter action :")
        ans = ans.split()
        ans0 = None
        ans1 = None
        
        if len(ans) > 0:
          ans0 = ans[0]
        else:
          ans0 = ans
          # if len(ans) > 1 :
          #   ans1 = ans[1]

        if menu == 'operate':
            if ans0 not in okeys:
                print(' bad operation keyword')
            else:
                ans1 = input(' Name of the result file:')
                break
        elif menu == 'write':
            if ans0 not in wkeys:
                print(' bad operation keyword')
            else:
                # ans1 = input(' Name of the result file:')
                break        
        elif ans0 in menulist[menu]: 
            break
        else:
            print(' not expected keyword')

    return ans0,ans1

# Function to enter the filename
def enterfilename(name,wwfiles):
    
    if len(wwfiles)>0:
        while True:
            fname = input(' enter ww file name:')
            if fname != '':
                if  fname in wwfiles:
                    print (' {} already appended! Load a different one.'.format(fname))
                elif os.path.isfile(fname) == False:
                    print (' {} not found'.format(fname))
                else:
                    break
    else:
        while True:
            fname = input(' enter ww file name:')
            if os.path.isfile(fname) == False:
               print (' {} not found'.format(fname))
            else:
               break
    return fname

# Function to select the file
def selectfile(wwfiles):

    print('\n Input files present:')
    counter = 1
    for f in wwfiles:
        print(" - [{}] {}".format(str(counter),f))
        counter = counter + 1
        
    while True:
        index=input(' enter ww index:' )
        if index.isdigit():
            index = int(index) - 1 
            if len(wwfiles) > index >= 0:
                break
            else:
                print(' Value not valid')
        else:
            print(' Value not valid')
    return index


#######################################
####      Supporting Functions     ####
#######################################

# Function to find the index of the closest list value of Number within the given list.
def closest(list, Number):
    aux = []
    for valor in list:
        aux.append(abs(Number-valor))

    return aux.index(min(aux))

# Function to check if the list contains only numbers.
def ISnumber(lis):
    for x in lis:
        try:
            float(x)
            return True
        except:
            return False

# Function to clean the screen (e.g cls)
def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
    
# Function that returns the same matrix but covered in zeros. m1==m2[1:-1,1:-1] Works for 2d and 3d arrays
def extend_matrix(matrix):
    shape = ()
    for dim in matrix.shape:
        shape = shape + (dim+2,)
    new_matrix = np.zeros(shape)
    try:
        new_matrix[1:-1, 1:-1] = matrix
    except:
        new_matrix[1:-1, 1:-1, 1:-1] = matrix
    return new_matrix

# Function that returns a matrix with its holes filled. Input(matrix, matrix with True where there is a hole to fix)    
def fill(data, invalid):
    """
    Replace the value of invalid 'data' cells (indicated by 'invalid') 
    by the value of the nearest valid data cell
    Input:
        data:    numpy array of any dimension
        invalid: matrix with True where there  is a hole to fix
    Output: 
        Return a filled array. 
    """    
    ind = nd.distance_transform_edt(invalid, 
                                    return_distances=False, 
                                    return_indices=True)
    return data[tuple(ind)]

#######################################
####     Selections Menu           ####
#######################################

principal_menu="""
 ***********************************************
        Weight window manipulator and GVR
 ***********************************************

 * Open weight window file   (open)   
 * Display ww information    (info)   
 * Write                     (write)
 * Analyse                   (analyse)
 * Plot                      (plot)   
 * Weight window operation   (operate)
 * GVR generation            (gvr)
 * Exit                      (end)    
"""                          
write_menu="""               
 * Write to wwinp            (wwinp)
 * Write to VTK              (vtk)
 * Exit                      (end)
"""                                                  
operate_menu="""             
 * Softening and normalize   (soft)
 * Mitigate long histories   (mit)
 * Add                       (add)
 * Remove                    (rem)
 * Flipping                  (flip) >> To be completed
 * Exit                      (end)
"""

#######################################
####     Operational Code          ####
#######################################

def main():
    clear_screen()
    print(principal_menu)
    ans,optname=answer_loop('principal')
    while True:
        # Load the ww
        if ans == 'open' :
            if len(wwfiles) == 0:
                fname  = enterfilename(optname,wwfiles)
                ww_out = load(fname)
                
                wwfiles.append(fname)
                wwdata.append(ww_out)
            else:
                fname  = enterfilename(optname,wwfiles)
                wwfiles.append(fname)
                
                ww_out =load(wwfiles[-1])
                wwdata.append(ww_out)
                
                # print(wwfiles)
                
        # Print ww information
        elif ans == 'info' :
            if len(wwfiles) == 0:
                print(' No weight window file')
            else:
                if len(wwfiles) == 1:
                    wwdata[-1].info()
                else:
                    index  = selectfile(wwfiles)
                    wwdata[index].info()

            # print(wwfiles)
        
        # Plot the ww
        elif ans == 'plot' :
            if len(wwfiles) == 1:
                plot(wwdata[-1])
            else:
                index  = selectfile(wwfiles)
                plot(wwdata[index])
            
            # print(wwfiles)
       
        # Analyse the ww
        elif ans == 'analyse' :
            if len(wwfiles) == 1:
                index  = 0
            else:
                index  = selectfile(wwfiles)
            
            if not wwdata[index].degree:
                while True:
                    degree = input(" Insert the toroidal coverage of the model [degree, all, auto]: ")
                    
                    if degree.isdigit():
                        degree = float(degree)/2
                        break
                    elif degree == 'all':
                        break
                    elif degree == 'auto':
                        break
                    else:
                        print(' Please insert one of the options!')
                
                zoneID, factor = zoneDEF(wwdata[index],degree)        
                
                wwdata[index].degree.append(zoneID)
                wwdata[index].degree.append(factor)            
            else:
                zoneID = wwdata[index].degree[0]
                factor = wwdata[index].degree[1]
            
            wwdata[index], RATIO_EVA = analyse(wwdata[index],zoneID, factor)
            # analyse(wwdata[index],zoneID, factor)
        
        # Export the ww
        elif ans == 'write'   :
            clear_screen()
            if len(wwfiles) == 1:
                index  = 0
            else:
                index  = selectfile(wwfiles)
            
            write(wwdata,wwfiles,index)
        
        # Generate GVR
        elif ans == 'gvr':
            if len(wwfiles) == 0:
                fname  = input(' Please write the name of the resulting GVR: ')
                ww_out = gvr_soft(fname)
                
                wwfiles.append(fname)
                wwdata.append(ww_out)
            else:
                fname  = input(' Please write the name of the resulting GVR: ')
                wwfiles.append(fname)
                
                ww_out =gvr_soft(fname)
                wwdata.append(ww_out)
        
        # Modify the ww
        elif ans == 'operate' :
          
          
          ww_out, fname, flag = operate()
          
          if flag:
              wwfiles.append(fname)
              wwdata.append(ww_out)
        
        elif ans == 'end' :
            sys.exit('\n Thanks for using this utility tools! See you soon!')
        else:
            break
        
        if ans == 'operate' or ans == 'write': 
            print(principal_menu)
        ans,optname=answer_loop('principal')
        clear_screen()
        print(principal_menu)

        
wwfiles   = []    # list storing filename
wwdata    = []    # list storing weight window class objects

if __name__== "__main__":
  main()