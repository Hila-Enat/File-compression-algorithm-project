# File-compression-algorithm-project
====================

This archiver Python module is intended to encode files into archive file, and to decode it, using the RLE (run-length encoding) algorithm.

Usage:
python archiver.py <arguments>

The various usage modes are:

1. Adding files to an archive:

   python archiver.py -c [-u UNIT_SIZE] <archive file name> <files/directories to archive>
   
   Archive file can exist and in that case the new files are encoded and appended to it.
   Multiple files and directories can be provided. For directories all the files in the directory hierarchy will be added.
   Multiple files with the same name may exist in the archive (each with potentially different unit size)
   
   The unit_size parameter determines the length of bytes that are considered in the run length encoding. For example,
   if the default unit size is used (1) the string "aaaaabbb" will be encoded into "5a3b" (in binary encoding for the 3/5 and
   string encoding for the a/b). However if unit size will be set to 2 then the same string will be encoded as "2aa1ab1bb".
   In case when the file content is not divisable by the unit_size, proper padding is performed.

2. Extracting an archive:

   python archiver.py -d <archive file name> <output directory>

   Output directory may exist and in that case the content is added to it.
   The program will never overwrite an existing file and will use a numeric suffix to create additional files with the same name.
   For exmaple if the archive contained two files with the name file.txt, the output directory will conatin file.txt and file_1.txt

3. Testing an archive file:

   python archiver.py -t <archive file name>

   Will print whether the file is corrupted or valid.

4. Listing an archive file:

   python archiver.py -l <archive file name>

   Will print the content of the archive and statistics about the files within it.
   For example:
   
   > python .\main.py -l .\archive_file                                                  
	File name: example text file.txt Unit size: 2 Encoded file size: 147 Original file size: 1673 Encode ratio: 8.79%
	File name: example text file.txt Unit size: 1 Encoded file size: 3346 Original file size: 1673 Encode ratio: 200.00%



   



