import sqlite3, datetime, os, re, multiprocessing as mp

import click
import pandas as pd
import SimpleITK as sitk
import pydicom
from tqdm import tqdm

ifr = sitk.ImageFileReader()
ifr.LoadPrivateTagsOn()

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

TABLENAME = "RUMC_PROSTATE_MPMRI"
ORDER_BY = "SeriesTime,StudyTime,StudyInstanceUID,SeriesInstanceUID,PatientID"


def get_pydicom_value(data: pydicom.dataset.FileDataset, key: str):
    key = '0x' + key.replace('|', '')
    if key in data:
        result = data[key]
        return result.value if not result.is_empty else None
    return None


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


class Dossier:
    def __init__(self, path: str, dcms: list):
        self.dir = path
        self.sample = dcms[-1]
        self.samplep = os.path.join(path, self.sample)
        self.dcms = dcms

    def __len__(self):
        return len(self.dcms)

    def is_valid(self):
        try:
            pydicom.dcmread(self.samplep, specific_tags=['0x00080005'])
        except:
            try:
                ifr.SetFileName(self.samplep)
                ifr.ReadImageInformation()
            except:
                return False
        return True

    def dossier_to_row(self):
        try:
            dcm = pydicom.dcmread(self.samplep)
            get_metadata = lambda key: get_pydicom_value(dcm, key)
        except:
            try:
                ifr.SetFileName(self.samplep)
                ifr.ReadImageInformation()
                get_metadata = lambda key: ifr.GetMetaData(key)
            except Exception as e:
                print(f"EXCEPTION (skipping): {self.dir}")
                print(e)
                return None

        headers = {'SeriesLength': len(self), 'Path': self.dir, 'Sample': self.sample}
        for key, header in dcm_tags.items():
            try:
                header = header.replace(' ', '_').strip()
                val = get_metadata(key)
                try:
                    if 'Date' in header:
                        val = datetime.datetime(int(val[:4]), int(val[4:6]), int(val[6:]))
                    # if 'Time' in header:
                    #     return f'{val[0:2]}:{val[2:4]}:{val[4:6]}.{int(val[7:])}'
                finally:
                    val = val.strip()
                headers[header] = val
            except:
                headers[header] = None

        return headers


def dossier2row(dossier: Dossier):
    return dossier.dossier_to_row()

# def header_to_date(header):
#     header = str(header)
#     return datetime.datetime(int(header[:4]), int(header[4:6]), int(header[6:]))

def create(name: str, path=None, parallel=True):
    try:
        path = os.path.abspath(os.getcwd() if path is None else path)

        pool = mp.Pool(mp.cpu_count()) if parallel else mp.Pool(1)
        click.echo(f"Running {mp.cpu_count()} cpus for job.")

        click.echo(f"Gathering DICOMs from {path} and its subdirectories")
        dcms = dict()
        with tqdm() as bar:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in [f for f in filenames if f.endswith(".dcm")]:
                    dpath = dirpath.split(path)[1]
                    dcms[dpath] = dcms.get(dpath, []) + [filename]
                    bar.update(len(dcms.keys()))

        # Create Dossier items
        dossiers = []
        for subpath, filenames in dcms.items():
            dossiers.append(Dossier(path + subpath, filenames))

        with pool:
            click.echo(f"Creating database from {len(dossiers)} DICOM directories")
            rows = []
            for result in tqdm(pool.imap_unordered(dossier2row, dossiers), total=len(dossiers)):
                if result is not None:
                    rows.append(result)

        click.echo(f"Writing {len(rows)} rows to SQL database.")
        conn = sqlite3.connect(f"{name}.db")
        with conn:
            conn.cursor().execute(f"DROP TABLE IF EXISTS {TABLENAME}")
            pd.DataFrame.from_dict(rows, orient='columns').to_sql(name=TABLENAME, con=conn, if_exists='replace')
        click.echo(f"Database created at {os.path.join(os.getcwd(), name)}.db")
    except Exception as e:
        click.echo(e)


if __name__ == '__main__':
    # create("D:/Repos/RUMCDataViewer/test")
    C = Connection("D:\\Repos\\RUMCDataViewer\\viewer\\tools\\RUMC_PROSTATE_MPMRI.db")
    result = C.select(Series_Description='naald,nld')
    pass
