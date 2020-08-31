#!/home/pafanasyev/software/anaconda3/bin/python

ver=200831

import sys
import os
import matplotlib.pyplot as plt
import argparse
import xml.etree.ElementTree as ET
import glob
import pathlib
import numpy as np
from xml.dom import minidom
#from scipy.stats import gaussian_kde
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances
import scipy.spatial as spatial
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from PIL import ImageFont
from PIL import ImageDraw 
class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def find_fullPath(searchDirectory, listOfFiles):
    '''
    Searches for the list of files in the given directory and returns the list with full path
    '''
    listOfFilesWithFullPath=[]
    allfiles=[]
    for (dirpath, dirnames, filenames) in os.walk(searchDirectory):
        allfiles += [os.path.join(dirpath, filename) for filename in filenames]
    for eachFile in listOfFiles:
        for i in allfiles:
            if eachFile in i:
                listOfFilesWithFullPath.append(i)
    return listOfFilesWithFullPath



def get_beamShiftArray_stagePositionArray(xmlfiles):
    '''
    Returns arrays from the .xml files:
    beamShiftArray, stagePositionArray, beamDiameterArray
    '''
    print("=> Analysing %d .xml files... "%len(xmlfiles))
    beamShifts = []
    stagePositions = []
    beamDiameters =[]
    for index, xmlfile in enumerate(xmlfiles):
        if len(xmlfiles) > 1000 and index % 300 ==0:  print("=> Working on %s file...     Progress: %d %% " %(xmlfile, 100*index/len(xmlfiles)))
        xmldoc = minidom.parse("%s" %xmlfile)
        
        beamshift_items = xmldoc.getElementsByTagName("BeamShift")[0]
        beamshiftx = beamshift_items.getElementsByTagName("a:_x")
        beamshifty = beamshift_items.getElementsByTagName("a:_y")
        beamShifts.append([float(beamshiftx[0].childNodes[0].nodeValue),float(beamshifty[0].childNodes[0].nodeValue)])
        
        stagepos_items = xmldoc.getElementsByTagName("Position")[0]
        stageposx = stagepos_items.getElementsByTagName("X")
        stageposy = stagepos_items.getElementsByTagName("Y")
        stagePositions.append([float(stageposx[0].childNodes[0].nodeValue),float(stageposy[0].childNodes[0].nodeValue)])
        
        beamdia_items = xmldoc.getElementsByTagName("optics")[0]
        beamdia = beamdia_items.getElementsByTagName("BeamDiameter")
        beamDiameters.append([float(beamdia[0].childNodes[0].nodeValue)])
        
    stagePositionArray = np.array(stagePositions)
    beamShiftArray = np.array(beamShifts)
    beamDiameterArray= np.array(beamDiameters)
    return beamShiftArray, stagePositionArray, beamDiameterArray

def get_beamDia(array):
    '''
    Counts unique values in a np array as a dictionary and returns key with the minimum value.
    '''
    import operator
    unique, counts = np.unique(array, return_counts=True)
    beamDia_count=dict(zip(unique, counts))
    print("\n=> Beam diameter(s) calculation.... \n------------------------\n value (um) | instances\n------------------------")
    for key, value in beamDia_count.items():
        print("  ", '%4.3f'%(key*1000000), "   |   ",  value)
    print ("------------------------\nWithin a single dataset with a constant dose, the beam diameter should be constant,\nand the table above would have one row.\n")
    beamDia=min(beamDia_count.items(), key=operator.itemgetter(1))[0]
    return beamDia

def get_exposuresArray(beamShiftArray, stagePositionArray, k):
    '''
    Adds beamShift values to the stagePosition
    '''
    beamShiftArray_um=np.multiply(beamShiftArray, k)
    stagePositionArray_um=np.multiply(stagePositionArray, 1000000)
    exposuresArray_um=np.add(beamShiftArray_um, stagePositionArray_um)
    return exposuresArray_um 

def kmeansClustering(nClusters, inputArray, maxIter, nInit):
    '''
    Kmeans for the beam-shift calibration
    '''
    kmeans = KMeans(n_clusters=nClusters, init='k-means++', max_iter=maxIter, n_init=nInit, random_state=0)
    #print("inputArray:",inputArray)
    pred_y = kmeans.fit_predict(inputArray)
    print("\n================== Information for the estimation of the beam-shift parameters ==================\n\nEuclidian distance matrix:")
    dists=euclidean_distances(kmeans.cluster_centers_)
    #print (kmeans.cluster_centers_)
    for dist in dists:
        with np.printoptions(precision=3, suppress=True, formatter={'float': '{: 0.3f}'.format} ): print(dist)
    tri_dists = dists[np.triu_indices(5, 1)]
    max_dist, avg_dist, min_dist = tri_dists.max(), tri_dists.mean(), tri_dists.min()
    print("\nMaximum distance: %4.3f"%max_dist, "\nMinimum distance: %4.3f"%min_dist)
    print("\nNote: to estimate coefficient for beam shift calculation divide the hole spacing in \nquantifoil (4 um for R2/2 Quantifoil grids) by an average of the smaller distances \n(consider discarding outliers) or a representative small distance in the distance matrix above")      
    print("\n=================================================================================================")
    print("\n=> K-means clustering is running. \nPlease check out the popping-up window and close it to continue.")
    plt.title('Beam-shifts distribution clustering')
    plt.xlabel('Beam-shift X')
    plt.ylabel('Beam-shift Y')
    plt.scatter(inputArray[:, 0], inputArray[:, 1], s=2)
    plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:,1], s=3, c='red')
    for i in enumerate(kmeans.cluster_centers_):
        plt.text(np.float32(i[1][0])+0.002, np.float32(i[1][1])+0.002, str(i[0]), fontsize='large', color='red')
        plt.plot(i[1][0], i[1][1])
    plt.gca().set_aspect('equal', adjustable='box')
    plt.show()
    return pred_y

def generate_montage(filenames, output_fn, row_size=6, margin=3, resize=False):
    '''
    Creates a .png montage of input files 
    '''
    if resize == True:
        images=[Image.open(filename) for filename in filenames] 
        im_rescaled = [im.resize([int(0.5 * s) for s in im.size]) for im in images]
        images=im_rescaled
    else:
        images = [Image.open(filename) for filename in filenames]
    width = max(image.size[0] + margin for image in images)*row_size
    height = sum(image.size[1] + margin for image in images)
    montage = Image.new(mode='L', size=(width, height), color=0)
    max_x = 0
    max_y = 0
    offset_x = 0
    offset_y = 0
    font = ImageFont.load_default()
    for i,image in enumerate(images):
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), filenames[i])
        montage.paste(image, (offset_x, offset_y))
        max_x = max(max_x, offset_x + image.size[0])
        max_y = max(max_y, offset_y + image.size[1])
        if i % row_size == row_size-1:
            offset_y = max_y + margin
            offset_x = 0
        else:
            offset_x += margin + image.size[0]
    montage = montage.crop((0, 0, max_x, max_y))
    montage.save(output_fn)
    
def main():
    output_text='''
========================================== find_dupl.py =========================================
Script for finding overexposed micrographs in a dataset collected by EPU. Such micrographs are
the result of several exposures of the same areas. This often happens due to wrong determination 
of the Foilhole centers, which, in turn, can be related to the problems with eucentric height 
determination, image shift calibration, large beam shifts, correct hole-detection by the EPU 
or any other problems with the EPU software or imaging. 
The script has to be run on the EPU data (.xlm and .jpg files)
The script is to be operated on the AFIS datasets and should be usually run twice:
1. The first run estimates the coefficient "k" for the beam shift estimation. 
2. The second run allows plotting all the exposures and finding overlapping micrographs. 
Outputs:
 - List of .jpg/.tiff overexposed micrographs to be deleted
 - Optionally: a .png montage of the repeating areas for checking parameters (max of 100)  
Assumptions:
 - The script reads the size of the beam from the .xml files and uses its value multiplied 
 by 0.9 as a radius for the search of overlapping exposures. Use --rad to change it.
 - .xml files in the format of FoilHole_*_Data_*_*_YYYYMMDD_HHMMSS.xml 
[version %s]
Written and tested in python3.6 on the data produced by EPU 2.8 with AFIS
Pavel Afanasyev
https://github.com/afanasyevp/find_dupl
-------------------------------------------------------------------------------------------------
''' % ver 
    
    parser = argparse.ArgumentParser(description="")
    #add=parser.add_argument
    parser.add_argument('--epudata', type=str, default="./", help="Directory with the EPU data (xml and jpg) files. By default, current folder is used.", metavar='')
    parser.add_argument('--o', type=str, default="duplicates", help="Output rootname. If empty, the output files will be saved with a rootname \"duplicates\" " , metavar='')
    parser.add_argument('--k',  help="Coefficient for the beam shift measurement", metavar='')
    parser.add_argument('--rawdata', type=str, help="Location of the .tiff files. Creates another file with the full path of each tiff file.", metavar='')
    parser.add_argument('--rad',  help="Radius of search (by default the radius of the beam size multiplied by 0.9 is used)", metavar='')
    parser.add_argument('--clusters', type=str, default="9", help="Number of clusters the beam-shifts should be divided in. (default: 9)", metavar='')
    parser.add_argument('--montage', default=False, action='store_true', help="If the input folder also contains .jpg files, the program can generate a montage of the duplicated micrographs.")
    parser.add_argument('--resize', default=False, action='store_true', help="Resize images in the montage by 2 - useful when one has too many duplicates")
    parser.add_argument('--max_iter', type=str, default="300", help="Expert option: Maximum number of iterations of the k-means algorithm for a single run. (default: 300)", metavar='')
    parser.add_argument('--n_init', type=str, default="10", help="Expert option: Number of time the k-means algorithm will be run with different centroid seeds. (default: 10)", metavar='')
    args = parser.parse_args()
    print(output_text) 
    parser.print_help()
    print("\nCommand template for the step 1: find_dupl.py --epudata . --clusters 9 \nCommand template for the step 2: find_dupl.py --epudata . --k 25 --montage --o duplicates --rad 0.2\n=================================================================================================\n")
    output=args.o
    try:
        clusters = int(args.clusters)
        max_iter = int(args.max_iter)
        n_init = int(args.n_init)
    except ValueError:
        print("--clusters, --n_init and --max_iter require integer values for comparison.")
        sys.exit(2)
    if len(sys.argv) == 1:
        sys.exit(2)
    #if args.epudata[-1] != "/":
    #    epudir=args.epudata+"/"
    #else:
    #    epudir=args.epudata
    if not os.path.exists(args.epudata):
        print("Input directory '%s' not found." % args.epudata)
        sys.exit(2)
    epudir=os.path.abspath(args.epudata)
    print("=> Working in the directory %s "%epudir)
    xmlfiles=glob.glob("%s/**/FoilHole_*_Data_*_*_*_*.xml"%epudir, recursive=True)
    if xmlfiles == []:
        print("No .xml files found! Check you input")
        sys.exit(2)
    #print(xmlfiles)
    beamShiftArray, stagePositionArray, beamDiameterArray = get_beamShiftArray_stagePositionArray(xmlfiles)
    
    if not args.rad:
        #The diameter is divided by 2 to get the radius in meters, multiplied by 1,000,000 to convert to microns. The result is also multiplied by 0.9 to take precision into account. This in total results in 450,000 as a coefficient in the formula below:
        rad=get_beamDia(beamDiameterArray)*450000
        print(color.BOLD + "Beam radius value of %4.3f um is used to find overlapping exposures \n"%rad + color.END)
    else:
        rad=float(args.rad)

    if not args.k:
        print("\n\n=> Running Kmeans for the coefficient estimation. ..")
        kmeansClustering(clusters, beamShiftArray, max_iter, n_init)
        print("=> Kmeans done!")
        print(color.BOLD + "\n=================================================================================================\n\nPlease estimate k (see instructions above) and use it as an input in this script. \nMake sure the number of clusters is correct. \nIf you see too many or not enough clusters, change the --clusters parameter accordingly. "%rad + color.END)       
        sys.exit(2)
    else:
        k=float(args.k)
    
    exposuresArray_um=get_exposuresArray(beamShiftArray, stagePositionArray, k)
    if len(exposuresArray_um) == 0:
        print("ERROR! The list of exposues is empty!")
        sys.exit(2)
    #fig, ax = plt.subplots()
    #ax.scatter(exposuresArray_um[:, 0], exposuresArray_um[:, 1], s=0.5)
    #plt.title('Exposures plot')
    #plt.xlabel('X')
    #plt.ylabel('Y')
    #plt.show()
    #x=exposuresArray_um[:, 0]
    #y=exposuresArray_um[:, 1]
    #xy = np.vstack([x,y])
    #z = gaussian_kde(xy)(xy)
    #plt.hist2d(x, y, (100,100), cmap=plt.cm.jet)
    #plt.colorbar()
    #plt.show()
    
    badfiles_jpg=[]
    badfiles_tiff=[]
    pairs=[]
    point_tree = spatial.cKDTree(exposuresArray_um)
    images_for_montage=[]
    for name, point  in zip(xmlfiles, exposuresArray_um):
        for i in point_tree.query_ball_point(point, rad):
            if name != xmlfiles[i]:
                a=name[:-4]
                b=xmlfiles[i][:-4]
                pair=sorted([a,b], key=lambda x: x[-15:])
                badfile_jpg=pair[1]+".jpg"
                badfile_tiff=os.path.basename(pair[1])+"_fractions.tiff"
                if badfile_tiff not in badfiles_tiff: 
                    badfiles_tiff.append(badfile_tiff)
                    badfiles_jpg.append(badfile_jpg)
                    pairs.append(pair)
                    #print(pair)
                    images_for_montage.append(pair[0]+".jpg")
                    images_for_montage.append(pair[1]+".jpg")
    if pairs== []: 
        print("All exposures in the radius of %4.3f um seem unique!" %rad )
        sys.exit(2)
    #for i in images_for_montage:
    #    print(i)
    print("\nThe program has detected %i overexposed micrographs (%d %%)"%(len(badfiles_tiff), 100*len(badfiles_tiff)/len(xmlfiles)))
    
    with open('%s_badfiles_jpg.txt'%output, 'w') as f:
        for item in badfiles_jpg:
            f.write("{}\n".format(item))
    
    if args.resize == True:
        print("=> Generating a montage image %s.png with the results..."%os.path.splitext(output)[0] )
        if len(images_for_montage) <=400: generate_montage(images_for_montage, os.path.splitext(output)[0]+".png", row_size=12, margin=1, resize=True)
        else: generate_montage(images_for_montage[:399], os.path.splitext(output)[0]+"_400.png", resize=True)
    elif args.montage == True:
        print("=> Generating a montage image %s.png with the results..."%os.path.splitext(output)[0] )
        if len(images_for_montage) <=100: generate_montage(images_for_montage, os.path.splitext(output)[0]+".png")
        else: generate_montage(images_for_montage[0:99], os.path.splitext(output)[0]+"_100.png")
    if args.rawdata:
        rawdatadir=os.path.abspath(args.rawdata)
        print("=> Searching for the raw files in the %s directory..."%rawdatadir )
        badfiles_tiff_fullpath=find_fullPath(rawdatadir, badfiles_tiff)
        if len(badfiles_tiff_fullpath) != len(badfiles_jpg):
            print("=> WARNING! Found only %d out of %d files in the %s folder"%(len(badfiles_tiff_fullpath),len(badfiles_jpg), rawdatadir))
        else:
            print("=> Found %d .tiff files"%len(badfiles_tiff_fullpath))
        with open('%s_badfiles_tiff.txt'%output, 'w') as f:
            for item in badfiles_tiff_fullpath:
                f.write("{}\n".format(item))
    else:
        with open('%s_badfiles_tiff.txt'%output, 'w') as f:
            for item in badfiles_tiff:
                f.write("{}\n".format(item))
 

    print("\n=> The program finished successfully. Please critically check the results in the %s file." % output)
if __name__ == '__main__':
    main()
