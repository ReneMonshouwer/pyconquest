import re

from pyconquest import pyconquest
import time
import pandas as pd

#normal rebuild
c=pyconquest(sql_inifile_name='dicom.sql',loglevel='INFO', compute_hash=True)
c.add_column_to_database(tablename='DICOMpatients',column_definition=['0x0020', '0x000d', 'StudyInst'])
c.create_standard_dicom_tables()
start = time.time()
nr_files=c.rebuild_database_from_dicom('1234567', compute_only_missing=False)
end = time.time()
print('numer of files: {}; should be 13'.format(nr_files))
print('time elapsed : '+ str(end-start) + ' seconds ; ms per file : '+ str( 1000*(end-start)/nr_files))

#test printing
print(pd.DataFrame(c.dicom_series_summary()))
print('should look like : \n0   1234567     1     0     0           2         1         1')

#test copying data
#by seriesuid
c.copy_dicom_files_to_dest(seriesuid='1.2.840.113704.1.111.7700.1448024597.12',destination='data2', UseSubDirectories=True)
#by list of seriesuid
c.copy_dicom_files_to_dest(seriesuid=['1.2.840.113704.1.111.7700.1448024597.12','2.16.840.1.113669.2.931128.880152.20190524082317.937233'],
                           destination='data2', UseSubDirectories=True)
#now copy by query
query="select seriesinst from dicomseries where modality=\'RTPLAN\'"
c.copy_dicom_files_to_dest(query=query, destination='data2', UseSubDirectories=True)

#now send by query, using default port numbers and localhost
query = "select seriesinst from dicomseries where modality=\'RTPLAN\'"
#.send_dicom(query=query)

#now send by seriesinst, using default port numbers and localhost'
c.send_dicom(seriesuid='2.16.840.1.113669.2.931128.880152.20190524082318.537836')

#now send by patientid
#c.send_dicom(addres='127.0.0.1', port=5678, patientid='1234567')

#read all files from directory input
c.store_dicom_files_from_directory('input')

# non existent file
c.store_dicom_file('notpresent.dcm')
# existing file
c.store_dicom_file('input/test.dcm')

print('\nTESTING INSERT DICT ROUTINE')
c.execute_db_query('DROP TABLE IF EXISTS newtable ')
c.insert_dict('newtable', {'col1': 'val1','col2': 'val2'})
c.insert_dict('newtable', {'col1': 'val1','col2': 'val2'})
print(pd.DataFrame(c.execute_db_query('select * from newtable')))

#delete a series
print('\nTESTING OF DELETE SERIES FUNCTIONALITY')
print(pd.DataFrame(c.execute_db_query('select seriesinst from dicomimages')))

#delete single series
c.delete_series(seriesuid='2.16.840.1.113669.2.931128.880152.20190524082318.537836')
all_series = ['2.16.840.1.113669.2.931128.880152.20190524082318.537836',
                 '2.16.840.1.113669.2.931128.880152.20190524082317.937233',
                 '1.2.840.113704.1.111.7700.1448024597.12',
                 '2.16.840.1.113669.2.931128.880152.20190524094947.12551',
                 '2.16.840.1.113669.2.931128.880152.20190524095038.429446']

#delete all, if you do this, all tables should be empty ( inc dicompatients)
# c.delete_series(seriesuid=all_series)

print(pd.DataFrame(c.execute_db_query('select sopinstanc from dicomimages')))


# test of roifilter, ignore case is default
print('\nTESTING OF THE ROI FILTER FUNCTIONALITY')
c.set_roi_filter(exclude=['Ex'])
print('after filtering ptv out here should only be lung : '+str(c.filter_roinames(['ex','lung'])))
c.set_roi_filter(include=['PTV'],exclude=[''],roi_filter_flags=re.IGNORECASE)
print('after filtering PTV in (include) there should only be ptv : '+str(c.filter_roinames(['ex','lung','ptv'])))
c.set_roi_filter(include=['PTV'],exclude=[''],roi_filter_flags=0)
print('after filtering PTV in (include) without ignorease there should only be only PTV not ptv : '+str(c.filter_roinames(['ex','PTV','ptv'])))
c.set_roi_filter(include='PTV',exclude=[''],roi_filter_flags=0)
print('after filtering PTV in (include) without ignorease there should only be only PTV not ptv : '+str(c.filter_roinames(['ex','PTV','ptv'])))

c.delete_series(query='select * from dicomseries where modality="CT"')

lst = c.execute_db_query('select * from dicomseries', return_list_from_col='SeriesInst')
print('should be list of 3 uids : '+str(lst))


c.close_db()