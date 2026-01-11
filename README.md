# digipres

This is the space for policies, procedures, workflows, and instructions on specific software encompassing digital preservation practice at Queen's University Archives.

# Convert Metadata for Bags
Version 1.0

## Purpose

Scripts to export and transform exif metadata from born-digital media for Archivematica-compliant bags

## Installation

### Install Python

Install Python. See [Python downloads](https://www.python.org/downloads/) for instructions.

### Install ExifTool

Install ExifTool. See [ExifTool](https://exiftool.org/) for instructions.

### Install Teracopy (Recommended)

Install Teracopy. See [Teracopy](https://www.codesector.com/downloads) for instructions.

### Install Bagging Software

Select whichever bagging software works best for your processes. This process is streamlined for use with DART, which has batch bagging capabilities.
[DART](https://aptrust.github.io/dart/)
[Bagger](https://github.com/LibraryOfCongress/bagger)
Future versions may incorporate [BagIt](https://github.com/LibraryOfCongress/bagit-python) to streamline the process.

### Download convert.py

Create a folder on your computer (Desktop or wherever). Save the [convert.py](https://github.com/jerheil/digipres/blob/main/convert.py) and [convert_metadata.py](https://github.com/jerheil/digipres/blob/main/convert_metadata.py) files to a folder on your computer. FOR WINDOWS USERS: Save the [convert1.bat](https://github.com/jerheil/digipres/blob/main/convert1.bat) and [convert2.bat](https://github.com/jerheil/digipres/blob/main/convert2.bat) files to the same folder

## Use

### Set up folder structure

Bags for Archivematica are structured as:

![Bagname
|---data
    |---metadata
        |---metadata.csv
        |---rights.csv
    |---objects
        |---digitalobject1
        |---digitalobject2 ...](./bagStructure.png)

While these scripts can be run on any folder, it is recommended that you prepare the folder structure in advance, with BagnameFolder containing a metadata folder and an objects folder.

### Select and Copy Source Files

Use Teracopy or rsync to copy files and directories from source media (CDs, diskettes, etc.) to the objects folder of the new folder structure. Ensure the settings maintain the original dates with the files.

### Run convert

1) FOR WINDOWS USERS: Double-click on convert1.bat. For Mac or Linux users, run convert.py through the command line
```
   py convert.py
```
2) Answer whether you want to generate metadataExp.csv by running exiftool on a folder of files (y/n)
   a) Select n if metadataExp.csv already exists in the folder - see 7) for details
3) Follow the prompt to input the source directory.
4) Follow the prompt to input the directory to which the metadata file will be written. Choose the directory that stores the scripts (or where convert_metadata.py is).
5) When prompted, enter whether the transfer is by Deed of Gift (d) or University Transfer (u)
6) When prompted, enter the accession number, currently masked as ####-###. To change the mask, edit line 227 in convert.py
7) If the process exits before the previous two prompts, exiftool was unable to complete its scan. metadataExp.csv will still be written, but will need to be edited with additional details relating to the file types.
   a) Once metadataExp.csv editing is complete, restart the convert script, selecting "n" when asked to generate a new metadataExp.csv file.
8) The program will produce one file, metadataExp.csv, which contains the following fields from exiftool: SourceFile, Title, FileName, FileCreateDate, FileModifyDate, FileTypeExtension, MIMEType, PageCount, LayerCount
   a) For older media (pre-2000), the FileCreateDate may contain values that don't reflect the actual date. Verify the data in case FileModifyDate is a better reflection of the date of creation. If so, delete the   FileCreateDate column, and rename FileModifyDate as FileCreateDate. Save the file

### Run convert_metadata

1) FOR WINDOWS USERS: Double-click on convert2.bat. For Mac or Linux users, run convert.py through the command line
```
   py convert_metadata.py
```
2) The script will prompt to click any key when finished
3) The program will produce two files: metadata.csv and rights.csv
   a) Move these files into the metadata folder under the Bagnamefolder
   b) Open metadata.csv and remove "2" from "dc.format2" - the script cannot read two fields with the same name so it distinguishes the two fields, but two "dc.format" fields is accepted by Archivematica
   c) Examine and edit any outstanding issues in the metadata.csv file, then click Save.
