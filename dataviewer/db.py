import sqlite3, datetime, os, re, multiprocessing as mp

import click
import pandas as pd
import SimpleITK as sitk
from tqdm import tqdm

dcm_tags = {  # Attributes
    "0008|0005": "SpecificCharacterSet",
    "0008|0008": "ImageType",
    "0008|0012": "InstanceCreationDate",
    "0008|0013": "InstanceCreationTime",
    "0008|0016": "SOPClassUID",
    "0008|0018": "SOPInstanceUID",
    "0008|0020": "StudyDate",
    "0008|0021": "SeriesDate",
    "0008|0022": "AcquisitionDate",
    "0008|0023": "ContentDate",
    "0008|0030": "StudyTime",
    "0008|0031": "SeriesTime",
    "0008|0032": "AcquisitionTime",
    "0008|0033": "ContentTime",
    "0008|0050": "AccessionNumber",
    "0008|0060": "Modality",
    "0008|0070": "Manufacturer",
    "0008|1010": "StationName",
    "0008|1030": "StudyDescription",
    "0008|103e": "SeriesDescription",
    "0008|1040": "InstitutionalDepartmentName",
    "0008|1090": "ManufacturersModelName",
    "0010|0020": "PatientID",
    "0010|0030": "PatientsBirthDate",
    "0010|0040": "PatientsSex",
    "0010|1010": "PatientsAge",
    "0010|21b0": "AdditionalPatientHistory",
    "0012|0062": "PatientIdentityRemoved",
    "0012|0063": "DeidentificationMethod",
    "0018|0015": "BodyPartExamined",
    "0018|0020": "ScanningSequence",
    "0018|0021": "SequenceVariant",
    "0018|0022": "ScanOptions",
    "0018|0023": "MRAcquisitionType",
    "0018|0024": "SequenceName",
    "0018|0050": "SliceThickness",
    "0018|0080": "RepetitionTime",
    "0018|0081": "EchoTime",
    "0018|0083": "NumberofAverages",
    "0018|0084": "ImagingFrequency",
    "0018|0085": "ImagedNucleus",
    "0018|0087": "MagneticFieldStrength",
    "0018|0088": "SpacingBetweenSlices",
    "0018|0089": "NumberofPhaseEncodingSteps",
    "0018|0091": "EchoTrainLength",
    "0018|0093": "PercentSampling",
    "0018|0094": "PercentPhaseFieldofView",
    "0018|1000": "DeviceSerialNumber",
    "0018|1030": "ProtocolName",
    "0018|1310": "AcquisitionMatrix",
    "0018|1312": "InplanePhaseEncodingDirection",
    "0018|1314": "FlipAngle",
    "0018|1315": "VariableFlipAngleFlag",
    "0018|5100": "PatientPosition",
    "0018|9087": "Diffusionbvalue",
    "0020|000d": "StudyInstanceUID",
    "0020|000e": "SeriesInstanceUID",
    "0020|0010": "StudyID",
    "0020|0032": "ImagePositionPatient",
    "0020|0037": "ImageOrientationPatient",
    "0020|0052": "FrameofReferenceUID",
    "0020|1041": "SliceLocation",
    "0028|0002": "SamplesperPixel",
    "0028|0010": "Rows",
    "0028|0011": "Columns",
    "0028|0030": "PixelSpacing",
    "0028|0100": "BitsAllocated",
    "0028|0101": "BitsStored",
    "0028|0106": "SmallestImagePixelValue",
    "0028|0107": "LargestImagePixelValue",
    "0028|1050": "WindowCenter",
    "0028|1051": "WindowWidth",
    "0040|0244": "PerformedProcedureStepStartDate",
    "0040|0254": "PerformedProcedureStepDescription"
}

# for x in tags_dcm.values():
#     print(x)

TABLENAME = "RUMC_PROSTATE_MPMRI"
ORDER_BY = "PatientID,SeriesInstanceUID,StudyInstanceUID,StudyTime,SeriesTime"


class Connection:
    def __init__(self, path):
        self._conn = sqlite3.connect(os.path.abspath(path))
        self._c = self._conn.cursor()
        self.name = path.name

    def __del__(self):
        self._conn.close()

    def _refactor_result(self, results: list):
        desc = self._c.description
        R = []
        for r in results:
            item = dict()
            for j in range(len(desc)):
                item[desc[j][0]] = r[j]
            R.append(item)
        return R

    def select(self, include_siblings=True, **kvp):
        q = []
        for key, value in kvp.items():
            values = value.split(',')
            values = [f"{key} LIKE '%{v}%'" for v in values]
            values = ' OR '.join(values)
            q.append(f"({values})")
        selection = 'StudyInstanceUID,SeriesInstanceUID' if include_siblings else '*'
        Q = f"SELECT {selection} FROM {TABLENAME} WHERE {' AND '.join(q)} ORDER BY {ORDER_BY}"
        if include_siblings:
            R = self._c.execute(Q).fetchall()
            studies, series = set(), []
            for study, serie in R:
                series.append(serie)
                studies.add(study)
            return self.select(include_siblings=False, StudyInstanceUID=','.join([s for s in set(studies)])), series
        return self._refactor_result(self._c.execute(Q).fetchall())

    def select_all(self):
        Q = f"SELECT * FROM {TABLENAME} ORDER BY {ORDER_BY}"
        return self._refactor_result(self._c.execute(Q).fetchall())


def is_dicom(name):
    return re.fullmatch(r'\d+\.dcm', name)


def header_to_date(header):
    header = str(header)
    return datetime.datetime(int(header[:4]), int(header[4:6]), int(header[6:]))


def find_dicom_dir(path):
    dicoms = []
    for item in os.scandir(path):  # type: os.DirEntry
        if item.is_dir():
            dicoms.extend(find_dicom_dir(item.path))
        if item.is_file() and is_dicom(item.name):
            return [path]
    return dicoms


def convert_val(header, val):
    try:
        return int(val)
    except ValueError:
        if 'Date' in header:
            return datetime.datetime(int(val[:4]), int(val[4:6]), int(val[6:]))
        else:
            return val.strip()


def dicom_dir_to_row(path):
    ls = list(filter(lambda a: is_dicom(a), os.listdir(path)))
    try:
        reader = sitk.ImageFileReader()
        reader.SetFileName(os.path.join(path, ls[-1]))
        reader.LoadPrivateTagsOn()
        reader.ReadImageInformation()
    except:
        print(f"EXCEPTION (skipping): {path}")
        return dict()

    headers = {'SeriesLength': len(ls), 'Path': path, 'Sample': ls[-1]}
    for key, header in dcm_tags.items():
        try:
            header = header.replace(' ', '_').strip()
            headers[header] = convert_val(header, reader.GetMetaData(key))
        except RuntimeError:
            headers[header] = None

    return headers


def create(name: str, path = None, parallel = True):
    try:
        path = os.path.abspath(os.getcwd() if path is None else path)
        conn = sqlite3.connect(f"{name}.db")
        dossiers = [d.path for d in filter(lambda a: a.is_dir(), os.scandir(path))]

        pool = mp.Pool(mp.cpu_count()) if parallel else mp.Pool(1)
        click.echo(f"Running {mp.cpu_count()} cpus for job.")

        with pool:
            click.echo(f"Gathering DICOM directories from {path}")
            dicom_dirs = []
            for result in pool.imap_unordered(find_dicom_dir, dossiers):
                dicom_dirs.extend(result)
            click.echo(f"Creating database from {len(dicom_dirs)} DICOM directories")
            rows = []
            for result in tqdm(pool.imap_unordered(dicom_dir_to_row, dicom_dirs), total=len(dicom_dirs)):
                rows.append(result)

        df = pd.DataFrame.from_dict(rows, orient='columns')
        click.echo(f"Writing {len(rows)} rows to SQL database.")
        with conn:
            conn.cursor().execute(f"DROP TABLE IF EXISTS {TABLENAME}")
            df.to_sql(name=TABLENAME, con=conn, if_exists='replace')
        click.echo(f"Database created at {os.path.join(os.getcwd(), name)}.db")
    except Exception as e:
        click.echo(e)


if __name__ == '__main__':
    # create("D:/Repos/RUMCDataViewer/test")
    C = Connection("D:\\Repos\\RUMCDataViewer\\viewer\\tools\\RUMC_PROSTATE_MPMRI.db")
    result = C.select(Series_Description='naald,nld')
    pass
