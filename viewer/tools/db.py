import sqlite3, datetime, os, re
import multiprocessing as mp
from tqdm import tqdm

import pandas as pd
import SimpleITK as sitk

INCLUDE_TAGS = {  # Attributes
    "0008|0005": "Specific Character Set",
    "0008|0008": "Image Type",
    "0008|0012": "Instance Creation Date",
    "0008|0013": "Instance Creation Time",
    "0008|0016": "SOP Class UID",
    "0008|0018": "SOP Instance UID",
    "0008|0020": "Study Date",
    "0008|0021": "Series Date",
    "0008|0022": "Acquisition Date",
    "0008|0023": "Content Date",
    "0008|0030": "Study Time",
    "0008|0031": "Series Time",
    "0008|0032": "Acquisition Time",
    "0008|0033": "Content Time",
    "0008|0050": "Accession Number",
    "0008|0060": "Modality",
    "0008|0070": "Manufacturer",
    "0008|1010": "Station Name",
    "0008|1030": "Study Description",
    "0008|103e": "Series Description",
    "0008|1040": "Institutional Department Name",
    "0008|1090": "Manufacturer's Model Name",
    "0010|0020": "Patient ID",
    "0010|0030": "Patient's Birth Date",
    "0010|0040": "Patient's Sex",
    "0010|1010": "Patient's Age",
    "0010|21b0": "Additional Patient History",
    "0012|0062": "Patient Identity Removed",
    "0012|0063": "De-identification Method",
    "0018|0015": "Body Part Examined",
    "0018|0020": "Scanning Sequence",
    "0018|0021": "Sequence Variant",
    "0018|0022": "Scan Options",
    "0018|0023": "MR Acquisition Type",
    "0018|0024": "Sequence Name",
    "0018|0050": "Slice Thickness",
    "0018|0080": "Repetition Time",
    "0018|0081": "Echo Time",
    "0018|0083": "Number of Averages",
    "0018|0084": "Imaging Frequency",
    "0018|0085": "Imaged Nucleus",
    "0018|0087": "Magnetic Field Strength",
    "0018|0088": "Spacing Between Slices",
    "0018|0089": "Number of Phase Encoding Steps",
    "0018|0091": "Echo Train Length",
    "0018|0093": "Percent Sampling",
    "0018|0094": "Percent Phase Field of View",
    "0018|1000": "Device Serial Number",
    "0018|1030": "Protocol Name",
    "0018|1310": "Acquisition Matrix",
    "0018|1312": "In-plane Phase Encoding Direction",
    "0018|1314": "Flip Angle",
    "0018|1315": "Variable Flip Angle Flag",
    "0018|5100": "Patient Position",
    "0018|9087": "Diffusion b-value",
    "0020|000d": "Study Instance UID",
    "0020|000e": "Series Instance UID",
    "0020|0010": "Study ID",
    "0020|0032": "Image Position (Patient)",
    "0020|0037": "Image Orientation (Patient)",
    "0020|0052": "Frame of Reference UID",
    "0020|1041": "Slice Location",
    "0028|0002": "Samples per Pixel",
    "0028|0010": "Rows",
    "0028|0011": "Columns",
    "0028|0030": "Pixel Spacing",
    "0028|0100": "Bits Allocated",
    "0028|0101": "Bits Stored",
    "0028|0106": "Smallest Image Pixel Value",
    "0028|0107": "Largest Image Pixel Value",
    "0028|1050": "Window Center",
    "0028|1051": "Window Width",
    "0040|0244": "Performed Procedure Step Start Date",
    "0040|0254": "Performed Procedure Step Description"
}

TABLENAME = "RUMC_PROSTATE_MPMRI"


class Connection:
    def __init__(self, db):
        self._conn = sqlite3.connect(db)
        self._c = self._conn.cursor()

    def __del__(self):
        self._conn.close()

    def select(self, **kvp):
        q = []
        for key, value in kvp.items():
            values = value.split(',')
            values = [f"{key} LIKE '%{v}%'" for v in values]
            values = ' OR '.join(values)
            q.append(f"({values})")
        Q = f"SELECT * FROM {TABLENAME} WHERE {' AND '.join(q)} ORDER BY Patient_ID"
        return self._c.execute(Q).fetchall()


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

    headers = {'Series_Length': len(ls), 'Path': path}
    for key, header in INCLUDE_TAGS.items():
        try:
            header = header.replace(' ', '_').strip()
            headers[header] = convert_val(header, reader.GetMetaData(key))
        except RuntimeError:
            headers[header] = None

    return headers


def create(path = None, parallel = True):
    try:
        path = os.getcwd() if path is None else path
        conn = sqlite3.connect(f"{TABLENAME}.db")
        dossiers = [d.path for d in filter(lambda a: a.is_dir(), os.scandir(path))]

        if parallel:
            pool = mp.Pool(mp.cpu_count())
            print(f"Running {mp.cpu_count()} cpus for job.")
        # else:
            # dicom_dirs = []
            # for result in tqdm([find_dicom_dir(d) for d in dossiers], total=len(dossiers)):
            #     dicom
        with pool:
            print(f"Gathering DICOM directories from {path}")
            dicom_dirs = []
            for result in tqdm(pool.imap_unordered(find_dicom_dir, dossiers), total=len(dossiers)):
                dicom_dirs.extend(result)
            print(f"Creating database from {len(dicom_dirs)} DICOM directories")
            rows = []
            for result in tqdm(pool.imap_unordered(dicom_dir_to_row, dicom_dirs), total=len(dicom_dirs)):
                rows.append(result)

        df = pd.DataFrame.from_dict(rows, orient='columns')
        print(f"Writing {len(rows)} rows to SQL database.")
        with conn:
            conn.cursor().execute(f"DROP TABLE IF EXISTS {TABLENAME}")
            df.to_sql(name=TABLENAME, con=conn, if_exists='replace')
        print("SQL Database created.")
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # create("D:/Repos/RUMCDataViewer/test")
    C = Connection("D:\\Repos\\RUMCDataViewer\\viewer\\tools\\RUMC_PROSTATE_MPMRI.db")
    result = C.select(Series_Description='naald,nld')
    pass
