# find_dupl
Search of the overexposed micrographs collected by EPU

Script for finding overexposed micrographs in a dataset collected by EPU. Such micrographs are the result of several exposures of the same areas. This often happens due to wrong determination of the Foilhole centers, which, in turn, can be related to the problems with eucentric height determination, image shift calibration, large beam shifts, correct hole-detection by the EPU or any other problems with the EPU software or imaging. 

The script has to be run on the EPU data (.xlm and .jpg files). It operates on the AFIS dataset and should be usually run twice:
1.	The first run estimates the coefficient "k" to calibrate beam shifts:
find_dupl.py --epudata . --clusters 9

![alt text](https://user-images.githubusercontent.com/24687497/91664001-87380b80-eaec-11ea-843f-9bb5c8e74d25.png)

2. The second run allows plotting all the exposures and finding overlapping micrographs.
find_dupl.py --epudata . --montage --rad 0.2 --k 25

The script reads the size of the beam from the .xml files and uses its value multiplied by 0.9 as a radius for the search of overlapping exposures. Use --rad to change the radius of search (in um)

Use --montage option to evaluate the results: 100 pairs will be written out into a duplicates.png file (--rescale option to have it binned by 2).

The resulting list of files (duplicates_badfiles_tiff.txt) can be used to find movie-files, corresponding to the overexposed images.

