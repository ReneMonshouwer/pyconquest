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
```
### Basic database summary
```
from pyconquest import pyconquest

c=pyconquest()
c.dicom_series_summary()
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


## Adding files to the database
#### Adding a single file specified by name (optionally remove original)
```
from pyconquest import pyconquest

c=pyconquest()
c.store_dicom_file('1.2.840.113704.1.111....931a31.dcm')
c.store_dicom_file('1.2.840.113704.1.111....931a31.dcm', remove_after_store=True)
```
#### to enter all dicom files in a directory into the database
````
from pyconquest import pyconquest

c=pyconquest()
c.store_dicom_files_from_directory('input_directory_name')
c.store_dicom_files_from_directory('input_directory_name', remove_after_store=True)
````

## Sending and receiving files via dicom connectivity

### Send dicom files via dicom protocol, by patientid, seriesuid or query

```
from pyconquest import pyconquest

c=pyconquest()
c.connect_db()
c.send_dicom(addres='127.0.0.1',port=5678,patientid='1234567')
c.send_dicom(seriesuid='2.16.840.1.113669.2.931128.880152.20190524082318.537836')

RTPLAN_query="select seriesinst from dicomseries where modality=\'RTPLAN\'"
c.send_dicom(query=RTPLAN_query)
```

### Start receiver (received files are stored in data directory and database is updated )

```
from pyconquest import pyconquest

c=pyconquest(data_directory='data2')
c.start_dicom_listener(port=5678)
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