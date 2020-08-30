# Search of the overexposed micrographs collected by EPU 

Script for finding overexposed micrographs in a dataset collected by EPU. Such micrographs are the result of several exposures of the same areas. This often happens due to wrong determination of the Foilhole centers, which, in turn, can be related to the problems with eucentric height determination, image shift calibration, large beam shifts, correct hole-detection by the EPU or any other problems with the EPU software or imaging. 

The script has to be run on the EPU data (.xlm and .jpg files). It operates on the AFIS dataset and should be run twice:
1.	The first run estimates the coefficient "k" to calibrate beam shifts:
```
find_dupl.py --epudata . --clusters 9
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
In the output image, to calibrate the values of the beam shifts one can measure the distance between the cluster centres (centres of the holes) using the output Euclidian distance matrix. In the image above, the distance between classes 0 and 4 is 0.163 (according to the matrix), which corresponds to 4 um spacing of the R2/2 grids. Therefore, the coefficient for beam shift calculation is 4/0.163 ≈ 25. 

2. The second run allows plotting all the exposures and finding overlapping micrographs.
```
find_dupl.py --epudata . --montage --rad 0.2 --k 25
```
The script reads the size of the beam from the .xml files and uses its value multiplied by 0.9 as a radius for the search of overlapping exposures. Use --rad to change the radius of search (in um)

Use --montage option to evaluate the results: 100 pairs will be written out into a duplicates.png file (--rescale option to have it binned by 2).

The resulting list of files (duplicates_badfiles_tiff.txt) can be used to find movie-files, corresponding to the overexposed images.

Example of the output montage file:

![alt text](https://user-images.githubusercontent.com/24687497/91664274-5e187a80-eaee-11ea-923e-0ff5e177e16e.png)
The output matching pairs are represented sequentially (3 pairs in each row). Note, that the first pair the second raw contains two close areas, which are significantly overlapping.
