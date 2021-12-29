import sqlite3
import logging
from pydicom import dcmread
import os
import os.path
import re
import shutil
from pynetdicom import AE, evt, AllStoragePresentationContexts, StoragePresentationContexts
import time
import pkg_resources

log = logging.getLogger(__name__)
LOGFORMAT = "%(levelname)s %(asctime)s [%(filename)-15s:%(lineno)-4s][%(funcName)-30s]\t%(message)s"
LOGFORMAT_console = "[%(funcName)-25s]\t%(message).40s ..."
logging.basicConfig(level=logging.ERROR, format=LOGFORMAT, datefmt='%H:%M:%S')


class pyconquest:
    """Class  ConquestDB is used to read and write (interact) with a conquest PACS database
    """
    __name_to_tablename = {'Series': 'DICOMseries',
                           'Image': 'DICOMimages',
                           'Patient': 'DICOMpatients',
                           'Study': 'DICOMstudies',
                           'WorkList': 'DICOMworklist'}
    __extra_imagetable_columns = ['Objectfile', 'ElementCount', 'ElementList', 'UniqueFOR_UID', 'DatabaseTimeStamp']
    __prev_seriesuid = ''
    __prev_studyuid = ''
    __prev_patientid = ''
    __db_design = {}
    __truncate_colnames = True
    __version__ = pkg_resources.get_distribution("pyconquest").version
    data_directory = ''
    sql_inifile_name = ''
    database_filename = ''
    conn_pacs = ''

    def __init__(self, data_directory='data', sql_inifile_name='dicom.sql', database_filename='conquest.db',
                 connect_and_read_sql=True, loglevel='ERROR'):
        self.data_directory = data_directory
        self.sql_inifile_name = sql_inifile_name
        self.database_filename = database_filename

        if loglevel == 'ERROR':
            log.level = logging.ERROR
        elif loglevel == 'DEBUG':
            log.level = logging.DEBUG
        elif loglevel == 'INFO':
            log.level = logging.INFO

        if connect_and_read_sql:
            self.connect_db()
            self.read_conquest_sql_inifile(self.sql_inifile_name)
        log.info("Created pyconquest({}) with dir:({}); db:({});ini:({}) "
                 .format(self.__version__, data_directory, database_filename, sql_inifile_name))

    #
    #   some general multi purpose database interaction routines
    #

    def connect_db(self):
        self.conn_pacs = sqlite3.connect(self.database_filename)
        log.info('Connected to ' + self.database_filename)

    def close_db(self):
        self.conn_pacs.close()
        log.info('Closed connection to ' + self.database_filename)

    def execute_db_query(self, query):
        query_result = None
        try:
            cursor = self.conn_pacs.cursor()
            cursor.execute(query)
            self.conn_pacs.commit()
            data = cursor.fetchall()
            cols = cursor.description
            query_result = [dict(line) for line in [zip([column[0] for column in cols], row) for row in data]]
            log.debug('Query : '+query)
            log.debug('Result: ' + str(query_result))
        except Exception as e:
            log.error('exception ' + str(e) + '\nencountered in execution of db query: ' + query)
        return query_result

    def delete_table(self, tablename):
        try:
            cur = self.conn_pacs.cursor()
            cur.execute('DROP TABLE ' + tablename)
            self.conn_pacs.commit()
        except Exception as e:
            log.error('failed to drop table : ' + tablename + ' probably already exists')

    def check_if_table_contains(self, tablename, colname, value):
        cur = self.conn_pacs.cursor()
        query = 'SELECT * FROM ' + tablename + ' WHERE ' + colname + ' = \"' + value.strip() + '\"'
        cur.execute(query)
        row = cur.fetchone()
        if row is None:
            return False
        else:
            return True

    def create_insertquery(self, table, myDict):
        myDict = self.__convert_listvalues_to_conquest_style(myDict)
        columns_string = ('(' + ','.join(myDict.keys()) + ')').replace("-", "_")
        values_string = '("' + '","'.join(map(str, myDict.values())) + '")'
        sql = """INSERT INTO %s %s VALUES %s""" % (table, columns_string, values_string)
        return sql

    def create_buildquery(self, table, mydict):
        columns_string = (' character varying(128),'.join(mydict.keys()) + ' character varying(128)').replace("-", "_")
        sql = """CREATE TABLE %s (%s)
                 """ % (table, columns_string)
        return sql

    #
    # below conquest specific routines
    #

    def __convert_listvalues_to_conquest_style(self, Dict):
        for key, val in Dict.items():
            if str(val).startswith("[") is True and key not in self.__extra_imagetable_columns:
                val = str(val).replace('[', '').replace(']', '').replace(',', "\\")
                Dict[key] = val
        return Dict

    def add_column_to_database(self, tablename, column_definition):
        # add an individual column to the database
        # example of column definition : ['0x0020', '0x000e', 'SeriesInst']
        if not isinstance(column_definition[0], list):
            column_definition = [column_definition]

        for col in column_definition:
            try:
                self.__db_design[tablename].append(col)
                log.info('Added column {} to table {}'.format(col, tablename))
            except Exception:
                log.error('failed to add column {} to table {}'.format(col, tablename))

    def read_conquest_sql_inifile(self, filename):
        # reads in the conquest style .sql file where the db is defined
        if os.path.exists(filename):
            with open(filename) as file:
                lines = file.readlines()
                lines = [line.rstrip() for line in lines]
            file.close()
        else:
            self.__set_default_database()
            return

        for line in lines:
            # comment lines
            if line.startswith("#") or line.startswith("/*") or line.startswith("*/"):
                continue
            # definition of tablename
            if line.startswith("*"):
                tablename = line.replace("*", "")
                tablename = self.__name_to_tablename[tablename]
                list_of_rows = []
                continue

            # end of table def
            if line.startswith("}"):
                log.info('reading table ' + tablename + ' from inifile:' + filename)
                self.__db_design[tablename] = list_of_rows
                continue

            stripped_line = re.sub("\s+", ' ', line)
            if stripped_line.startswith(" {"):
                col = (line.replace("\t{", "").replace("}", "").replace("{", '').replace(" ", "").split(","))
                if self.__truncate_colnames:
                    col[2] = col[2].replace('"', '').replace(' ', '')[0:10]
                list_of_rows.append(col[0:3])

    def __create_tabledict(self, tablename, ds):
        tabledict = {}
        for item in self.__db_design[tablename]:
            try:
                elem = ds[item[0], item[1]]
                val = elem.value
            except Exception:
                val = ''
            tabledict[item[2].replace('\"', '')] = val
        return tabledict

    def write_tags(self, ds, filename=''):
        sopinstanceuid = ds['0x0008', '0x0018'].value
        if not self.check_if_table_contains('DICOMimages', 'SOPInstanc', sopinstanceuid):
            imagedict = self.__create_tabledict('DICOMimages', ds)
            imagedict['Objectfile'] = filename
            imagedict.update(self.extra_dicom_tags(ds))
            query = self.create_insertquery('DICOMimages', imagedict)
            self.execute_db_query(query)
        else:
            # update timestamp in case of rewrite of the data
            updatequery = """update DICOMimages set DatabaseTimeStamp=\'{}\' where SOPInstanc=\'{}\'""". \
                format(time.time(), sopinstanceuid)
            self.execute_db_query(updatequery)

        seriesuid = ds['0x0020', '0x000e'].value
        if not (seriesuid == self.__prev_seriesuid):
            self.__prev_seriesuid = seriesuid
            if not self.check_if_table_contains('DICOMseries', 'SeriesInst', seriesuid):
                seriesdict = self.__create_tabledict('DICOMseries', ds)
                # if a unique FOR_UID was extracted from RTSTRUCT, add to series table also
                if 'UniqueFOR_UID' in imagedict:
                    seriesdict['FrameOfRef'] = imagedict['UniqueFOR_UID']
                query = self.create_insertquery('DICOMseries', seriesdict)
                self.execute_db_query(query)

            studyuid = ds['0x0020', '0x000d'].value
            if not (studyuid == self.__prev_studyuid):
                self.__prev_studyuid = studyuid
                if not self.check_if_table_contains('DICOMstudies', 'Studyinsta', studyuid):
                    studydict = self.__create_tabledict('DICOMstudies', ds)
                    query = self.create_insertquery('DICOMstudies', studydict)
                    self.execute_db_query(query)

                patientid = ds['0x0010', '0x0020'].value
                if not (patientid == self.__prev_patientid):
                    self.__prev_patientid = patientid
                    if not self.check_if_table_contains('DICOMpatients', 'Patientid', patientid):
                        patientdict = self.__create_tabledict('DICOMpatients', ds)
                        query = self.create_insertquery('DICOMpatients', patientdict)
                        self.execute_db_query(query)

    def create_standard_dicom_tables(self):

        for tablename in self.__db_design:
            tablelist = self.__db_design[tablename]
            colnames = {}
            for item in tablelist:
                colnames[item[2]] = 'dummy'

            # as an excepion, add extra column to images table
            if tablename == 'DICOMimages':
                for colname in self.__extra_imagetable_columns:
                    colnames[colname] = 'dummy'

            query = self.create_buildquery(tablename, colnames)
            self.delete_table(tablename)
            self.execute_db_query(query)

    def rebuild_database_from_dicom(self, directory=None):
        if directory is None:
            directory = self.data_directory

        counter = 0
        for root, dirs, files in os.walk(directory, topdown=True):
            for name in files:
                full_filename = os.path.join(root, name)
                log.info('Processing ... ' + full_filename)
                try:
                    counter = counter + 1
                    ds = dcmread(full_filename)
                    self.write_tags(ds, full_filename[len(directory) + 1:])
                except Exception as e:
                    log.error(str(e))
        return counter

    def store_dicom_file(self, filename):
        # places dicom file in proper directory in data directory and updates database
        try:
            ds = dcmread(filename)
            patientid = ds[0x0010, 0x0020].value

            target_filename = "{}/{}/{}".format(self.data_directory, patientid, os.path.basename(filename))
            path = "{}/{}".format(self.data_directory, patientid)
            if not os.path.exists(path):
                os.makedirs(path)
                log.info("Directory " + path + " Created ")

            shutil.copy(filename, target_filename)
            os.remove(filename)
            self.write_tags(ds, target_filename)
            log.info('stored file : '+filename+' in database at location: '+target_filename)
        except Exception as e:
            log.error('Exception encountered in store_dicom_file: ' + str(e))

    def extra_dicom_tags(self, ds):
        # save some nested tags to the database
        # roi names for RTSTRUCT
        # to do : beam names for RTPLAN

        returndict = {}
        returndict['DatabaseTimeStamp'] = time.time()
        dicomtype = ds[0x0008, 0x0060].value
        if dicomtype == 'RTSTRUCT':
            contours = ds[0x3006, 0x0020].value
            contournamelist = []
            FrameOfReferenceUID_List = []
            for c in contours:
                contournamelist.append(c[0x3006, 0x0026].value)
                FrameOfReferenceUID_List.append(c[0x3006, 0x0024].value)
            unique_frame_of_ref = list(set(FrameOfReferenceUID_List))
            returndict['ElementList'] = contournamelist
            returndict['ElementCount'] = len(contournamelist)
            if len(unique_frame_of_ref) == 1:
                returndict['UniqueFOR_UID'] = unique_frame_of_ref[0]
            else:
                returndict['UniqueFOR_UID'] = ''

        return returndict

    #
    #   Some utility routines not part of base functionality of conquest, but handy
    #

    def copy_dicom_files_to_dest(self, seriesuid=None, studyuid=None, patientid=None, destination='', CreateDir=True):
        # copies all dicom files belonging to a series/study/patient to

        if not seriesuid is None:
            query = "select Objectfile from dicomimages where seriesinst=\"{}\"".format(seriesuid)
            return_list = self.execute_db_query(query)
        else:
            log.error('As yet unimplemented option in copy_dicom_files_to_dest')
            return 0

        if return_list and CreateDir:
            if not os.path.exists(destination):
                os.makedirs(destination)
                log.info("Directory "+destination+ " Created ")

        for row in return_list:
            filename = "{}/{}".format(self.data_directory, row['Objectfile'])
            log.info('copying ' + filename + ' to dest : ' + destination)
            shutil.copy(filename, destination)
        return 1

    #
    #   Below is the dicom communication part using pynetdicom
    #

    def send_dicom(self, addres, port, patientid='', seriesuid='', filename='',
                   query='Select Objectfile from DICOMimages', ae_title=b'pyconquest'):
        filename_list = []
        if not patientid == '':
            query = 'Select Objectfile from DICOMimages where imagepat=\'{}\''.format(patientid)
        elif not seriesuid == '':
            query = 'Select Objectfile from DICOMimages where seriesinst=\'{}\''.format(seriesuid)
        elif not filename == '':
            filename_list.append(filename)
            self.send_dicom_file(addres, port, filename_list)
            return

        # query for filenames and fill list of fienames
        result = self.execute_db_query(query)
        for line in result:
            filename_list.append(self.data_directory + '\\' + line['Objectfile'])

        self.send_dicom_file(addres, port, filename_list, aetitle=ae_title)

    def send_dicom_file(self, addres, port, filename_list, aetitle=b'pyconquest'):

        # Initialise the Application Entity
        ae = AE()

        # Add a requested presentation context
        ae.requested_contexts = StoragePresentationContexts

        assoc = ae.associate(addres, port, ae_title=aetitle)
        if assoc.is_established:
            # Use the C-STORE service to send the dataset
            # returns the response status as a pydicom Dataset
            for filename in filename_list:
                ds = dcmread(filename)
                status = assoc.send_c_store(ds)

                # Check the status of the storage request
                if status:
                    # If the storage request succeeded this will be 0x0000
                    log.info('C-STORE request status: 0x{0:04x}'.format(status.Status))
                else:
                    log.error('Connection timed out, was aborted or received invalid response')

            # Release the association
            assoc.release()
        else:
            log.error('Association rejected, aborted or never connected')

    def start_dicom_listener(self, port=5678, forward_dir=None):
        # handlers and context can be added to parameters
        print('starting listener on port : ' + str(port))
        if forward_dir is None:
            handlers = [(evt.EVT_C_STORE, self.handle_dicom_store_request)]
        else:
            handlers = [(evt.EVT_C_STORE, self.handle_dicom_store_request, [forward_dir])]
            print('Enabled forwarding dir to directory : ' + forward_dir)
        # Initialise the Application Entity
        ae = AE()
        # Support presentation contexts for all storage SOP Classes
        ae.supported_contexts = AllStoragePresentationContexts
        # Start listening for incoming association requests
        ae.start_server(('', port), evt_handlers=handlers)

    def handle_dicom_store_request(self, event, args=None):
        """Handle a C-STORE request event."""
        # Decode the C-STORE request's *Data Set* parameter to a pydicom Dataset
        log.info('incoming event')

        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta
        patientid = ds[0x0010, 0x0020].value

        filename = "{}/{}/{}.dcm".format(self.data_directory, patientid, ds.SOPInstanceUID)
        path = "{}/{}".format(self.data_directory, patientid)
        if not os.path.exists(path):
            os.makedirs(path)
            log.info("Directory " + path + " Created ")

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(filename, write_like_original=False)
        log.info('dicom saved to file : ' + filename)

        if not args is None:
            xtra_filename = "{}/{}.dcm".format(args, ds.SOPInstanceUID)
            try:
                ds.save_as(xtra_filename, write_like_original=False)
                log.info('dicom saved to file : ' + xtra_filename)
            except Exception as e:
                log.error(e)

        ds2 = dcmread(filename)
        c2 = pyconquest(database_filename=self.database_filename, data_directory=self.data_directory)
        filename2 = "{}/{}".format(patientid, os.path.basename(filename))
        c2.write_tags(ds2, filename2)
        c2.close_db()

        # Return a 'Success' status
        return 0x0000

    #
    # examine database
    #

    def dicom_series_summary(self, orderby='nrCT'):
        # you can use this command to pretty print this output: (needs pandas)
        # print(pd.DataFrame(c.dicom_series_summary()))
        query = "select distinct patientid " \
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'CT\') as nrCT" \
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'MR\') as nrMR" \
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'PT\') as nrPT" \
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'RTSTRUCT\') as nrRTSTRUCT"\
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'RTDOSE\') as nrRTDOSE" \
                ",(select count(*) from dicomseries where seriespat=patientid and modality=\'RTPLAN\') as nrRTPLAN" \
                " from dicompatients order by {}".format(orderby)
        result = self.execute_db_query(query)
        return result

    def __set_default_database(self):
        log.info('Using default database layout,specify .sql file during instance creation to change this')
        self.__db_design = \
            {'DICOMpatients':
                 [['0x0010', '0x0020', 'PatientID'],
                  ['0x0010', '0x0010', 'PatientNam'],
                  ['0x0010', '0x0030', 'PatientBir'],
                  ['0x0010', '0x0040', 'PatientSex']],
             'DICOMstudies':
                 [['0x0020', '0x000d', 'StudyInsta'],
                  ['0x0008', '0x0020', 'StudyDate'],
                  ['0x0008', '0x0030', 'StudyTime'],
                  ['0x0020', '0x0010', 'StudyID'],
                  ['0x0008', '0x1030', 'StudyDescr'],
                  ['0x0008', '0x0050', 'AccessionN'],
                  ['0x0008', '0x0090', 'ReferPhysi'],
                  ['0x0010', '0x1010', 'PatientsAg'],
                  ['0x0010', '0x1030', 'PatientsWe'],
                  ['0x0008', '0x0061', 'StudyModal'],
                  ['0x0010', '0x0010', 'PatientNam'],
                  ['0x0010', '0x0030', 'PatientBir'],
                  ['0x0010', '0x0040', 'PatientSex'],
                  ['0x0008', '0x1070', 'OperatorsN'],
                  ['0x0010', '0x0020', 'PatientID']],
             'DICOMseries':
                 [['0x0020', '0x000e', 'SeriesInst'],
                  ['0x0020', '0x0011', 'SeriesNumb'],
                  ['0x0008', '0x0021', 'SeriesDate'],
                  ['0x0008', '0x0031', 'SeriesTime'],
                  ['0x0008', '0x103e', 'SeriesDesc'],
                  ['0x0008', '0x0060', 'Modality'],
                  ['0x0008', '0x1090', 'ManModelNa'],
                  ['0x0008', '0x1155', 'Referenced'],
                  ['0x0018', '0x5100', 'PatientPos'],
                  ['0x0018', '0x0010', 'ContrastBo'],
                  ['0x0008', '0x0070', 'Manufactur'],
                  ['0x0018', '0x0015', 'BodyPartEx'],
                  ['0x0018', '0x1030', 'ProtocolNa'],
                  ['0x0008', '0x1010', 'StationNam'],
                  ['0x0008', '0x0080', 'Institutio'],
                  ['0x0020', '0x0052', 'FrameOfRef'],
                  ['0x0028', '0x0008', 'NumberOfFr'],
                  ['0x3004', '0x000A', 'DoseSummat'],
                  ['0x3006', '0x0002', 'StructureS'],
                  ['0x0010', '0x0020', 'SeriesPat'],
                  ['0x0008', '0x1070', 'OperatorsN'],
                  ['0x0020', '0x000d', 'StudyInsta']],
             'DICOMimages':
                 [['0x0008', '0x0018', 'SOPInstanc'],
                  ['0x0008', '0x0016', 'SOPClassUI'],
                  ['0x0020', '0x0013', 'ImageNumbe'],
                  ['0x0008', '0x0023', 'ImageDate'],
                  ['0x0008', '0x0033', 'ImageTime'],
                  ['0x0008', '0x1155', 'Referenced'],
                  ['0x0018', '0x0086', 'EchoNumber'],
                  ['0x0028', '0x0008', 'NumberOfFr'],
                  ['0x0008', '0x0022', 'AcqDate'],
                  ['0x0008', '0x0032', 'AcqTime'],
                  ['0x0018', '0x1250', 'ReceivingC'],
                  ['0x0020', '0x0012', 'AcqNumber'],
                  ['0x0020', '0x1041', 'SliceLocat'],
                  ['0x0028', '0x0002', 'SamplesPer'],
                  ['0x0028', '0x0004', 'PhotoMetri'],
                  ['0x0028', '0x0010', 'Rows'],
                  ['0x0028', '0x0011', 'Colums'],
                  ['0x0028', '0x0030', 'PixelSpaci'],
                  ['0x0028', '0x0101', 'BitsStored'],
                  ['0x0028', '0x1052', 'RescaleInt'],
                  ['0x0028', '0x1053', 'RescaleSlo'],
                  ['0x0008', '0x0008', 'ImageType'],
                  ['0x0054', '0x0400', 'ImageID'],
                  ['0x0010', '0x0020', 'ImagePat'],
                  ['0x0018', '0x0060', 'KVP'],
                  ['0x0018', '0x1150', 'ExposureTi'],
                  ['0x0018', '0x1151', 'TubeCurren'],
                  ['0x0018', '0x1152', 'Exposure'],
                  ['0x0018', '0x9345', 'CTDIvol'],
                  ['0x01F1', '0x1026', 'Pitch'],
                  ['0x01F1', '0x1027', 'RotationTi'],
                  ['0x01F1', '0x104A', 'DoseRight'],
                  ['0x01F1', '0x104B', 'Collimatio'],
                  ['0x0018', '0x0050', 'SliceThick'],
                  ['0x0020', '0x0037', 'ImageOrien'],
                  ['0x0008', '0x0060', 'Modality'],
                  ['0x0008', '0x103e', 'SeriesDesc'],
                  ['0x0020', '0x0032', 'ImagePosit'],
                  ['0x0020', '0x000e', 'SeriesInst']],
             'DICOMworklist':
                 [['0x0008', '0x0050', 'AccessionN'],
                  ['0x0010', '0x0020', 'PatientID'],
                  ['0x0010', '0x0010', 'PatientNam'],
                  ['0x0010', '0x0030', 'PatientBir'],
                  ['0x0010', '0x0040', 'PatientSex'],
                  ['0x0010', '0x2000', 'MedicalAle'],
                  ['0x0010', '0x2110', 'ContrastAl'],
                  ['0x0020', '0x000d', 'StudyInsta'],
                  ['0x0032', '0x1032', 'ReqPhysici'],
                  ['0x0032', '0x1060', 'ReqProcDes'],
                  ['0x0040', '0x0100', '--------'],
                  ['0x0008', '0x0060', 'Modality'],
                  ['0x0032', '0x1070', 'ReqContras'],
                  ['0x0040', '0x0001', 'ScheduledA'],
                  ['0x0040', '0x0002', 'StartDate'],
                  ['0x0040', '0x0003', 'StartTime'],
                  ['0x0040', '0x0006', 'PerfPhysic'],
                  ['0x0040', '0x0007', 'SchedPSDes'],
                  ['0x0040', '0x0009', 'SchedPSID'],
                  ['0x0040', '0x0010', 'SchedStati'],
                  ['0x0040', '0x0011', 'SchedPSLoc'],
                  ['0x0040', '0x0012', 'PreMedicat'],
                  ['0x0040', '0x0400', 'SchedPSCom'],
                  ['0x0040', '0x0100', '---------'],
                  ['0x0040', '0x1001', 'ReqProcID'],
                  ['0x0040', '0x1003', 'ReqProcPri']]}
