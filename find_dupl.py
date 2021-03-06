#!/home/pafanasyev/software/anaconda3/bin/python

ver=200906

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
from datetime import datetime
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

def get_timeStamp(xmlFile):
    '''
    Returns timestamp of the given .xml or .jpg file named as "*_YYYYMMDD_HHMMSS.*". Only one "." can be in the basename.
    '''
    d=os.path.basename(xmlFile).split(".")[0][-15:]
    timeStamp = datetime.strptime(d,  "%Y%m%d_%H%M%S")
    #print(d, d.strftime("%Y%m%d_%H%M%S"))
    return timeStamp 

def get_foilHoleImagename(xmlFile, foilHoleFiles):
    '''
    For a given xmlFile finds corresponding foilHoleFile.
    FoilHoles in EPU 2.7 are collected twice: before and after centering with an interval of ~5 sec. This function returns the second (centered) Foilhole
    '''
    foilHoleFilesTimeStamps=[get_timeStamp(foilHoleFile) for foilHoleFile in foilHoleFiles]
    #print("=> Determining Foilholes...")
    foilHoleImageTimeStamp=min([i for i in foilHoleFilesTimeStamps if i < get_timeStamp(xmlFile)], key=lambda x: abs(x - get_timeStamp(xmlFile)))
    for foilHoleFile in foilHoleFiles:
        if foilHoleImageTimeStamp.strftime("%Y%m%d_%H%M%S") in foilHoleFile:
            foilHoleImageName=foilHoleFile
    #print(xmlFile)
    #print(foilHoleImageName)
    #print(foilHoleImageTimeStamp)
    return foilHoleImageName

def get_beamShiftArray_stagePositionArray(xmlFiles):
    '''
    Returns arrays from the .xml files:
    beamShiftArray, stagePositionArray, beamDiameterArray
    '''
    print("=> Analysing %d .xml files... "%len(xmlFiles))
    beamShifts = []
    stagePositions = []
    beamDiameters =[]
    for index, xmlFile in enumerate(xmlFiles):
        if len(xmlFiles) > 1000 and index % 300 ==0:  print("=> Working on %s file...     Progress: %d %% " %(xmlFile, 100*index/len(xmlFiles)))
        try:
            from xml.parsers.expat import ExpatError
            xmldoc = minidom.parse("%s" %xmlFile)
        except ExpatError:
            print(color.YELLOW + "WARNING! Check the %s file"%xmlFile + color.END)
            #sys.exit(2)
            continue
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

def generate_montage(filenames, output_fn, row_size=4, margin=3, resize=False):
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
        #print(os.path.basename(filenames[i]))
        #draw.text((0, 0), os.path.basename(filenames[i]))
        draw.text((0, 0), str(get_timeStamp(filenames[i])))
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
 - Optionally: a montage of overexposed areas with corresponding Foilholes images (max of 100)  
Assumptions:
 - The script reads the size of the beam from the .xml files. However, it uses a value of 0.2 um 
as a radius for the search of overlapping exposures by default. Use --rad to change it.
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
    if not os.path.exists(args.epudata):
        print("Input directory '%s' not found." % args.epudata)
        sys.exit(2)
    epudir=os.path.abspath(args.epudata)
    print("=> Working in the directory %s "%epudir)
    
    xmlFiles=glob.glob("%s/**/FoilHole_*_Data_*_*_*_*.xml"%epudir, recursive=True)
    if xmlFiles == []:
        print("No .xml files found! Check you input")
        sys.exit(2)
    foilHoleFiles=glob.glob("%s/**/FoilHoles/FoilHole*_*_*_*.jpg"%epudir, recursive=True)
    if foilHoleFiles==[]:
        print(color.red+ "WARNING: no Foilhole files found!"+ color.END)
    
    #foilHoleFiles=[get_foilHoleImagename(i, foilHoleFiles) for i in xmlFiles]
    #print(foilHoleFiles)
    beamShiftArray, stagePositionArray, beamDiameterArray = get_beamShiftArray_stagePositionArray(xmlFiles)
    dia=get_beamDia(beamDiameterArray)*1000000
    if not args.rad:
        #OLD: The diameter is divided by 2 to get the radius in meters, multiplied by 1,000,000 to convert to microns. The result is also multiplied by 0.9 to take precision into account. This in total results in 450,000 as a coefficient in the formula below:
        #rad=get_beamDia(beamDiameterArray)*450000
        rad=0.2
        print(color.YELLOW + "Beam diameter: %4.3f um. To find overlapping exposures, the default value of 0.2 um will be used  \n"%dia + color.END)
    else:
        rad=float(args.rad)
        print(color.YELLOW + "Beam diameter: %4.3f um. To find overlapping exposures, the set value of %4.3f um will be used  \n"%(dia,rad) + color.END)

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
    point_tree = spatial.cKDTree(exposuresArray_um)
    points=point_tree.query_ball_point(exposuresArray_um, rad)
    badfiles_jpg=[]
    badfiles_tiff=[]
    images_for_montage=[]
    point_numbers_uniq=[]
    dupl_xmls=[]
    count_doubles=[] # list with the number of double exposures around in each location
    count_missedStageMove=0
    print("=> Searching for double-exposures and corresponding FoilHoles. If you have a large dataset, this might take a few minutes")
    for point_name, list_of_point_numbers in zip(xmlFiles, points):
        #print("name:", point_name, point_name[:-4], "\n")
        #print(list_of_point_numbers)
        point_number=list_of_point_numbers[0]
        #print("point_number", point_number)
        if len(list_of_point_numbers) >1 and list_of_point_numbers not in point_numbers_uniq:
            point_numbers_uniq.append(list_of_point_numbers)
            #print(list_of_point_numbers)
            a=point_name[:-4]
            b=[]
            #print(list_of_point_numbers_uniq, "list_of_point_numbers")
            for i in list_of_point_numbers:
                b.append(xmlFiles[i])
            dupl_xmls_each_point=sorted(b, key=lambda x: x[-19:])  #sorted xml list for each point 
            dupl_xmls.append(dupl_xmls_each_point)
            count_doubles.append(len(dupl_xmls_each_point)-1)
            #print("dupl:", dupl_xmls_each_point[:1])
            #print("dupl_xmls_each_point", dupl_xmls_each_point)
            #print("dupl_xmls_each_point", dupl_xmls_each_point)
            #images for montage are: image taken first and its duplicate (second); image taken first and its duplicate (third); etc.
            if len(dupl_xmls_each_point)==2:
                badfiles_jpg.append(dupl_xmls_each_point[1][:-4]+".jpg")
                badfile_tiff=os.path.basename(dupl_xmls_each_point[1][:-4])+"_fractions.tiff"
                badfiles_tiff.append(badfile_tiff)
                temp1=get_foilHoleImagename(dupl_xmls_each_point[0], foilHoleFiles)
                temp2=get_foilHoleImagename(dupl_xmls_each_point[1], foilHoleFiles)
                images_for_montage.append(dupl_xmls_each_point[0][:-4]+".jpg")
                images_for_montage.append(dupl_xmls_each_point[1][:-4]+".jpg")
                images_for_montage.append(temp1)
                images_for_montage.append(temp2)

                if temp1 == temp2:
                    count_missedStageMove+=1
                #else:
                    #print(temp1, temp2)
                    #images_for_montage.append(dupl_xmls_each_point[0][:-4]+".jpg")
                    #images_for_montage.append(dupl_xmls_each_point[1][:-4]+".jpg")
                    #images_for_montage.append(temp1)
                    #images_for_montage.append(temp2)
                #print("to del:", [(dupl_xmls_each_point[1][:-4]+".jpg")] )
            else:
                for i in dupl_xmls_each_point[1:]:
                    #print(i)
                    #print("to del: ", i[-11:-4]+".jpg")
                    badfile_tiff=os.path.basename(i[:-4])+"_fractions.tiff"
                    badfiles_jpg.append(i[:-4]+".jpg")
                    badfiles_tiff.append(badfile_tiff)
                    temp1=get_foilHoleImagename(dupl_xmls_each_point[0], foilHoleFiles)
                    temp2=get_foilHoleImagename(i[:-4], foilHoleFiles)
                    images_for_montage.append(dupl_xmls_each_point[0][:-4]+".jpg")
                    images_for_montage.append(i[:-4]+".jpg")
                    images_for_montage.append(temp1)
                    images_for_montage.append(temp2)
                    if temp1 == temp2:
                        count_missedStageMove+=1
                        #print(temp1, temp2)
                    #else:
                        #images_for_montage.append(dupl_xmls_each_point[0][:-4]+".jpg")
                        #images_for_montage.append(i[:-4]+".jpg")
                        #images_for_montage.append(temp1)
                        #images_for_montage.append(temp2)

                #badfiles_jpg=badfiles_jpg[1:]
    count_doubles_dict = {i:count_doubles.count(i) for i in count_doubles}
    #print("count_doubles_dict:", count_doubles_dict)
    if dupl_xmls== []: 
         print("All exposures in the radius of %4.3f um seem unique!" %rad )
         sys.exit(2)

    print("\nThe program has detected %i overexposed micrographs (%4.2f %%) (overlap zone: %4.2f um)"%(len(badfiles_tiff), 100*len(badfiles_tiff)/len(xmlFiles), rad))
    if count_missedStageMove !=0:
        print("\n%d double-exposures are taken from exactly the same stage position (after all exposures from each stage position, EPU did not move the stage to the next FoilHole position but instead continued collecting)"%count_missedStageMove)
    with open('%s_badfiles_jpg.txt'%output, 'w') as f:
        for item in badfiles_jpg:
            f.write("{}\n".format(item))
    
    if args.resize == True:
        print("=> Generating a montage image %s.png with the results..."%os.path.splitext(output)[0] )
        if len(images_for_montage) <=400: generate_montage(images_for_montage, os.path.splitext(output)[0]+"_all_resize.png", row_size=12, margin=1, resize=True)
        else: generate_montage(images_for_montage[:399], os.path.splitext(output)[0]+"_400_resize.png", row_size=12, margin=1,  resize=True)
    elif args.montage == True:
        print("=> Generating a montage image %s.png with the results..."%os.path.splitext(output)[0] )
        if len(images_for_montage) <=100: generate_montage(images_for_montage, os.path.splitext(output)[0]+"_all.png")
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

    print("\n=> The program finished successfully. Please critically check the results in the \"%s\" files. \nNote, that false-positive results could be due to errors in determination of the stage positions and/or beam shifts for each exposure; as well as wrong beam shift calibration coefficient in this program (step 1)" % output)
if __name__ == '__main__':
    main()

