# PyConquest

## Introduction

Python code to partly mimic the functionality of the Conquest Pacs system ( http://www.natura-ingenium.nl/dicom.html ).
No (source) code of Conquest was used to write this python code. Program was optimised to be partly compatible (files and database), so queries etc. can 
be re-used.

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

## Examples

### Rebuild database

```
from pyconquest import pyconquest

c=pyconquest()
c.create_standard_dicom_tables()
nr_files=c.rebuild_database_from_dicom()
```

## Send dicom files via dicom protocol

```
from pyconquest import pyconquest

c=pyconquest()
c.connect_db()
c.send_dicom('127.0.0.1',11112,patientid='1234567')
c.send_dicom('127.0.0.1',11112,query='Select Objectfile from DICOMimages where Modality=\'RTDOSE\'')
```

### Start Receiver ( received files are stored in data directory and database is updated )

```
from pyconquest import pyconquest

c=pyconquest(data_directory='data2')
c.start_dicom_listener(port=5678)
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
    
c.dicom_series_summary()
```
### Adding a single file to the database and insert into filebased tree
```
from pyconquest import pyconquest

c=pyconquest()
c.store_dicom_file('1.2.840.113704.1.111....931a31.dcm')
```

### Physically copying files on the disk to other directory
```
from pyconquest import pyconquest

c=pyconquest()
c.copy_dicom_files_to_dest(seriesuid='1.2......97.12',destination='data2/hallo')
```

### Physically copying all CTs on the disk to other directory
```
from pyconquest import pyconquest

c=pyconquest()
query="select seriesinst,* from dicomseries where modality=\'CT\'"
result=c.execute_db_query(query)
for r in result:
    seriesinst = r['SeriesInst']
    dest = """{}/{}""".format('CTdata', r['SeriesPat'])
    c.copy_dicom_files_to_dest(seriesuid=seriesinst, destination=dest)
```

### Definition of the database structure
The database can be defined using various ways
- If a file dicom.sql exist that file is used
- If an alternative file is specified on creation of the instance, that file is used
    - use sql_infilename='filename.sql' when creating 
- If no file is found, a hardcoded definition is taken
    - You can add columns to this definition as illustrated below:

the .sql files are compatible with the original Conquest file format
````
from pyconquest import pyconquest

c=pyconquest(sql_inifile_name='dicom.sql',loglevel='INFO')
c.add_column_to_database(tablename='DICOMpatients',column_definition=['0x0020', '0x000d', 'StudyInst'])
c.create_standard_dicom_tables()

````
### To install and upload to PyPi:
```
python setup.py sdist
twine upload dist/*
```