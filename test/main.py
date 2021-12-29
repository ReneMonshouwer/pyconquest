from pyconquest import pyconquest
import time
import pandas as pd
import os
import shutil

#normal rebuild
c=pyconquest(sql_inifile_name='dicom.sql',loglevel='INFO')
c.add_column_to_database(tablename='DICOMpatients',column_definition=['0x0020', '0x000d', 'StudyInst'])
c.create_standard_dicom_tables()
start = time.time()
nr_files=c.rebuild_database_from_dicom()
end = time.time()
print('time elapsed : '+ str(end-start) + ' seconds ; ms per file : '+ str( 1000*(end-start)/nr_files))

#test printing
print(pd.DataFrame(c.dicom_series_summary()))

#test moving data
c.copy_dicom_files_to_dest(seriesuid='1.2.840.113704.1.111.7700.1448024597.12',destination='data2/hallo/')

# non existent file
c.store_dicom_file('notpresent.dcm')
# existing file
c.store_dicom_file('input/test.dcm')

c.close_db()

exit()
#watches inbox, sends incoming to dest en copy's file to sent dir
path_to_watch = "inbox"
while 1:
  time.sleep (2)
  fl = os.listdir(path_to_watch)
  for f in fl:
    full_filename = os.path.join(path_to_watch, f)
    c.send_dicom('127.0.0.1', 5678,filename=full_filename)
    shutil.copy(full_filename,'inbox_sent')
    os.remove(full_filename)
    print(full_filename)

