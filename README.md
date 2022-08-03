# PyConquest

## Introduction

Python code to partly mimic the functionality of the Conquest Pacs system ( http://www.natura-ingenium.nl/dicom.html ).
No (source) code of Conquest was used to write this python code. Program was optimised to be partly compatible (files and database), so queries etc. can 
be re-used.

## Description:
Class is used to organise and index sets of dicom files. The dicom files are stored in
a directory (default name : data), with the files of each patient stored in a 
subdirectory with the patientid as the name. The class will index all files in the 
directory and store information (tag information of the dicom files) 
in a sqlite database (default name : conquest.db).
Which tags are stored in the database can be defined by the dicom.sql file, this 
file is optional, a standard set is used when not present.

Standard file/directory layout is :
```
conquest.db                       database file
data                              data_directory
    1                             subdirectory with name of PatientID
      file1_of_pat1.dcm           files of patient1
      file2_of_pat1.dcm
      ..
      ..
    2                             subdirectory with name of PatientID
      file1_of_pat2               files of patient2
      file2_of_pat2
      ..
      ..
[dicom.sql]                       optional definition of the database
```

### Implemented features :
- indexer properties : read a dicom tree and build a sqlite database from this which conforms to the Conquest standard.
- use the conquest style dicom.sql file to define the columns
- add some special columns,with for instance the roinames in a RTSTRUCT file
- provide low level procedures to write and read to the database and helper files to create queries
- provide basic SCU and SCP functionality
- basic printing of data properties

### What it is not and when you should use Conquest
- no attempt made to mimic full dicom functionality (this is no PACS)
- lua scripting
- image visualisation

# Examples

Note : use the argument *loglevel='INFO'* when creating the instance to get logging output
### (Re)create database and rebuild database

```
from pyconquest import pyconquest

c=pyconquest(loglevel='INFO')
c.create_standard_dicom_tables()
nr_files=c.rebuild_database_from_dicom()
# only rebuild a single MRN/patient
c.rebuild_database_from_dicom(mrn='1234567')
# build for every MRN, even if the MRN already exists in Database
c.rebuild_database_from_dicom(compute_only_missing=False)
```
### Basic database summary
```
from pyconquest import pyconquest

c=pyconquest()
c.dicom_series_summary()
```
### Saving database information to a csv file
```
from pyconquest import pyconquest

c=pyconquest()

# by table(s) or views, specification of filenames is optional
c.dump_data_to_csv(table='dicomstudies')
c.dump_data_to_csv(table=['dicomseries','dicompatients'],
                   filename_dict={'dicomseries': 'dicomseries_filename', 'dicompatients': 'dicompatients_filename'} )
# by query
c.dump_data_to_csv(query='select * from dicomstudies',filename='query_filename.csv')
```

### More advanced querying and extraction from the database:
```
from pyconquest import pyconquest

c=pyconquest()

# extract python list type of selected seriesuids 
query='select * from dicomseries where modality='CT'
list_of_seriesuid=c.execute_db_query(query,return_list_from_col='SeriesInst')
for seriesuid in list_of_seriesuid:
  print(seriesuid)
```
### Using non standard names and directories
```
from pyconquest import pyconquest

c=pyconquest(
    data_directory='data2',
    sql_inifile_name='dicom2.sql',
    database_filename='test.db',
    connect_and_read_sql=True)
    
nr_files=c.rebuild_database_from_dicom()   
c.dicom_series_summary()
```


## Adding and deleting files to the database
### Adding a single file specified by name (optionally remove original)
```
from pyconquest import pyconquest

c=pyconquest()
c.store_dicom_file('1.2.840.113704.1.111....931a31.dcm')
c.store_dicom_file('1.2.840.113704.1.111....931a31.dcm', remove_after_store=True)
```
### Enter all dicom files in a directory into the database
````
from pyconquest import pyconquest

c=pyconquest()
c.store_dicom_files_from_directory('input_directory_name')
c.store_dicom_files_from_directory('input_directory_name', remove_after_store=True)
````

### Deleting series or list of series from the database (optionally 'real' deletion of the file)
````
c.delete_series(seriesuid='2.16.840.1.11....152.20190524082318.537836')
c.delete_series(seriesuid=['2.16..7836','1.2.666...55'])
#or by query
c.delete_series(query='select * from dicomseries where modality="CT"')

# Really pyhsically remove the files (otherwise only the DB entries are removed)
c.delete_series('2.16.840.1.11....152.20190524082318.537836', delete_files=True)
````

## Sending and receiving files via dicom connectivity

### Send dicom files via dicom protocol, by patientid, seriesuid or query

```
from pyconquest import pyconquest

c=pyconquest()
c.connect_db()
c.send_dicom(addres='127.0.0.1', port=5678, patientid='1234567', ae_title=b'destinationAE',  sending_ae_title=b'MY_AE_TITLE')
c.send_dicom(seriesuid='2.16.840.1.113669.2.931128.880152.20190524082318.537836')

RTPLAN_query="select seriesinst from dicomseries where modality=\'RTPLAN\'"
c.send_dicom(query=RTPLAN_query)
```

### Start receiver (received files are stored in data directory and database is updated )

```
from pyconquest import pyconquest

c=pyconquest(data_directory='data2')
c.start_dicom_listener(port=5678)
# Below does not update the database which saves time
c.start_dicom_listener(port=104, write_to_database=False)
```



## Copying files of a series on the disk to another directory
#### by seriesuid or list of seriesuids
```
from pyconquest import pyconquest

c.copy_dicom_files_to_dest(seriesuid='1.2...8024597.12',destination='out', UseSubDirectories=True)
c.copy_dicom_files_to_dest(seriesuid=['1.2.84..97.12','2.16.840....33'],destination='data2')
```

#### Or by query (query should return seriesinst)
```
from pyconquest import pyconquest

c=pyconquest()
CTquery="select seriesinst from dicomseries where modality=\'CT\'"
c.copy_dicom_files_to_dest(query=CTquery, destination='CTdata',UseSubDirectories=True)
```


## Definition of the database structure
The database can be defined using various ways
- If a file dicom.sql exist that file is used
- If an alternative file is specified on creation of the instance, that file is used
    - use sql_infilename='filename.sql' when creating 
- If no file is found, a hardcoded definition is taken
    - You can add columns to this definition as illustrated below:


````
from pyconquest import pyconquest

c=pyconquest(sql_inifile_name='dicom.sql',loglevel='INFO')
c.add_column_to_database(tablename='DICOMpatients',column_definition=['0x0020', '0x000d', 'StudyInst'])
c.create_standard_dicom_tables()

````
the .sql files are compatible with the original Conquest file format

### To install and upload to PyPi:
```
python setup.py sdist
twine upload dist/*
```

# CHANGELOG

### version 0.1.1 (skipped to 0.1.1 because some systems take 0.0.51 as default)
- Added option **dump_data_to_csv()** to dump data from the database to csv files
- Logging of errors to a (rotating) log file : "pyconquest_error.log"
- Added option **write_to_database** to dicom_listener, if FALSE, sqlite db is not updated (for speed)
- For RTDOSE the referenced SOP UID of the RTPLAN is saved to DicomImages table
- For RTPLAN the referenced SOP UID of the RTSTUCT is saved to DicomImages table
### version 0.0.7
- added option not to check for double entries when rebuilding the database
- added fast option to delete a patient from the database
- database indices are now created when creating a new database
- made index tables non unique to improve robustness

### version 0.0.6
- **Rebuild_database_from_dicom()** now has option to rebuild only missing directories
- When closing the database, the time elapsed is printed
- Referenced seriesuid is now extracted from RTSTRUCT and placed in dicomseries and dicomimages table
- **Dicom_series_summary()** now prints result directly to stdout, so no need for pandas to make a readable table
- The view **v_series** now only combines series and study table (previous version was too slow due to complexity)
- New view : **v_seriesRT** now combines series,study and image tables for only RT dicom objects (so not for images)
### version 0.0.5
- a view (**v_series**) is added to the sqlite database that joins study,series and image table
- delete_series can now handle query to define the series to delete
- series argument of delete_series changed from positional to named
- added option to rebuild database for a single mrn  (mrn='1234567')
- added option sending_ae_title to send_dicom() and send_dicom_file()
- bugfix in name of file in store_dicom (wrong path was used)
- execute_db_query now has an option to return (only) a list of a single column

### version 0.0.4
- Added function **insert_dict** to class to easily insert your own data in the database. Also takes care of creating the
table when the first dict is inserted
- If a database has no tables, tables are created automatically on db opening (so on instance creation)
- In **create_buildquery**, now columns can be defined with formats deviating from default and the default can be defined
- Number of  fractions and number of beams saved from RTPLAN to database columns 
- For RTDOSE, RTPLAN and RTSTRUCT file hashes are calculated and saved in dicomimage table
- Added **delete_series** function to delete the series from database and optionally delete the .dcm files
- Added **filter_roinames()** and **set_roi_filter()** methods to facilitate filtering of roi name lists for child classes
### version 0.0.3
- Improved documentation and docstrings
- uniformity in calling send and copy routines