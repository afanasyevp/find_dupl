# Detection of the overexposed micrographs collected by EPU 

Script for finding overexposed micrographs in datasets collected by the EPU. Such micrographs are the result of several exposures of the same area. This often happens due to wrong determination of the Foilhole centres. This, in turn, can be related to the problems with eucentric height determination, image shift calibration, large beam shifts, correct hole detection by the EPU or any other problems with the EPU software or imaging. 

The script calibrates beam shift values recorded in the .xml files (see below), adds those to the stage positions (also from the .xml files) and maps all the exposures. Within a given radius from each of the exposure, it searches for the neighbours and finds point pairs. Given the filenames, it estimates the micrographs exposure times at the area and records the names of those, which were exposed later. Optionally, it can (i) output a montage file with such pairs (based on the .jpg images); (ii) search for the full path of the bad movie files and output those into a separate file (assuming the movies are .tiff files).      

The script has to be run on the AFIS EPU data. It requires the name of the EPU folders with .xlm and .jpg files (and access to those files). The script should be run in two steps:
1.	The first run estimates the coefficient "k" to calibrate beam shifts (using K-means classification of the beam shift values):
```
find_dupl.py --epudata [path for the folder with all the EPU data] --clusters 5
```
Example of the program output (5 clusters used):
![alt text](https://user-images.githubusercontent.com/24687497/91664001-87380b80-eaec-11ea-843f-9bb5c8e74d25.png)
```
================== Information for the estimation of the beam-shift parameters ==================
Euclidian distance matrix:
[ 0.000  0.219  0.365  0.327  0.163]
[ 0.219  0.000  0.163  0.216  0.145]
[ 0.365  0.163  0.000  0.161  0.231]
[ 0.327  0.216  0.161  0.000  0.163]
[ 0.163  0.145  0.231  0.163  0.000]
Maximum distance: 0.365 
Minimum distance: 0.145
Note: to estimate coefficient for beam shift calculation divide the hole spacing in 
quantifoil (4 um for R2/2 Quantifoil grids) by an average of the smaller distances 
(consider discarding outliers) or a representative small distance in the distance matrix above
=================================================================================================
```
In the output image above, we see 5 clusters, corresponding to 5 holes with 6 exposures in each. Therefore, to calibrate the values of the beam shifts, one can find the distance between the cluster centres (centres of the holes) using the output Euclidian distance matrix and compare it with the known distance between the holes. Thus, in the image above, the distance between classes #0 and #4 is 0.163 (according to the matrix), which corresponds to 4 um spacing of the Quantifoil R2/2 grids (value provided by the manufacturer). Therefore, the coefficient for beam shift calculation is 4/0.163 ≈ 25. Note, that the labeling of the classes starts with 0.

2. The second run allows plotting all the exposures and finding overlapping micrographs.
```
find_dupl.py --epudata [path for the folder with all the EPU data]  --k 25 --montage --rawdata [path for the folder with all movies]
```
The script by default reads the sizes of the beam (which all should all be the same) from all the .xml files. By default, the program uses 0.2 um as a radius for search of overlapping exposures. This is an arbitrary value to account for precision of the performed calibration, imaging and stage stability. In the case I was testing (dataset with plenty of overexposed micrographs and ~1 um beam in diameter) values of 0.2 um to 0.8 um were producing similar results. Use --rad option to change the radius of search (in um) and lower it to avoid false-positive results.

Use --montage option to evaluate the results: only a maximum of 100 pairs of the .jpg files (due to RAM limits) will be written out into a duplicates.png file (--rescale option to have those binned by 2 with a montage of 400 if needed). The resulting list of files (duplicates_badfiles_tiff.txt) can be used to find movie-files, corresponding to the overexposed images.

Example of the output montage file:

![alt text](https://user-images.githubusercontent.com/24687497/91664274-5e187a80-eaee-11ea-923e-0ff5e177e16e.png)

The output matching pairs are represented sequentially (3 pairs in each row). Note, that the first pair in the second raw contains two close areas, which are significantly overlapping (almost by half). In the presented example, the data was acquired with a K3 camera with a column of defect pixels, causing troubles for the correct determination of the hole centres. 

**Validation of the results**
The results of a "healthy" dataset tipically demonstrate <0.2% (depending on the radius) of the overexposed micrographs. False-positive results can be the result of high "--rad" value, inaccurate beam-shift calibration or estimation of the calibration coefficient ("--k") in this script.



