import os, re, json
from pathlib import Path

import SimpleITK as sitk

with open(Path(__file__).parent.joinpath("assets\\dicom_kvp.json"), "r") as assetfile:
    dicom_kvp = json.load(assetfile)


def load_data(fp):
    j = json.load(open(fp))
    return j['patients']


def scan_data(dirp, savep=os.getcwd(), queue=None):
    data_name = re.sub(r'[^a-z0-9]', '', dirp, flags=re.IGNORECASE)
    patients = os.listdir(dirp)
    patients.sort()

    try:
        path = f"{dirp}/{patients[0]}"
        study = os.listdir(path)[0]
        serie = os.listdir(f"{path}/{study}")[0]
        if not any(dcm.endswith('.dcm') for dcm in os.listdir(f"{path}/{study}/{serie}")):
            raise
    except:
        if queue:
            queue.put(-1)
            return savep
        else:
            raise NotADirectoryError("Directory does not contain a valid patient dataset")

    data = [{'id': p, 'data': {}} for p in patients]

    sitki = sitk.ImageFileReader()
    sitki.LoadPrivateTagsOn()

    for i, p in enumerate(data):
        try:
            dicom = {}
            dir = f"{dirp}\\{p['id']}"
            for study in os.listdir(dir):
                dicom[study] = {}
                for serie in os.listdir(f"{dir}\\{study}"):
                    fp = f"{dir}\\{study}\\{serie}"
                    try:
                        sitki.SetFileName(f"{fp}\\0.dcm")
                        sitki.ReadImageInformation()
                        item = {"path": fp}
                        for key, value in dicom_kvp.items():
                            try:
                                item[value] = sitki.GetMetaData(key)
                            except:
                                item[value] = ''
                        dicom[study][serie] = item
                    except RuntimeError as e:
                        print(e)
                # p['n'][study] = sum([1 if serie['needle'] else 0 for serie in dicom[study].values()])
            # p['n_total'] = sum([n for n in p['n'].values()])
            p['data'] = dicom
        except Exception as ex:
            if queue:
                queue.put(-1 * p['id'])
            else:
                print(f"ERROR: patient {p['id']}")
                print(ex)
            continue
        finally:
            if queue:
                queue.put(i + 1)

    dump = json.dumps({"dir": dirp, "patients": data.copy()})
    try:
        f = open(savep + "\\DATA_" + data_name + ".json", "w")
        f.write(dump)
        f.close()
    except:
        print(dump)
    finally:
        if queue:
            queue.put(0)
    return savep

# ['0008|0005:ISO_IR 100',
#  '0008|0008:ORIGINAL\\PRIMARY\\M\\NORM\\DIS2D ',
#  '0008|0016:1.2.840.10008.5.1.4.1.1.4',
#  '0008|0018:1.2.276.0.7230010.3.1.3.338343255778492766281538160854115408851',
#  '0008|0020:20141021',
#  '0008|0030:120000',
#  '0008|0050:',
#  '0008|0060:MR',
#  '0008|0070:SIEMENS ',
#  '0008|0090:',
#  '0008|1030:MR PROSTAAT STADIERING I.V. CONTRAST',
#  '0008|103e:Perfusie_t1_twist_tra_TT=46.3s',
#  '0008|1090:Skyra ',
#  '0010|0010:RUMC Patient 10007',
#  '0010|0020:10007 ',
#  '0010|0030:19510701',
#  '0010|0040:M ',
#  '0010|1010:063Y',
#  '0018|0010:dotarem ',
#  '0018|0020:GR',
#  '0018|0021:SP\\OSP',
#  '0018|0022:PFP ',
#  '0018|0023:3D',
#  '0018|0024:*fldyn3d1 ',
#  '0018|0025:Y ',
#  '0018|0050:3 ',
#  '0018|0080:3.62',
#  '0018|0081:1.27',
#  '0018|0083:1 ',
#  '0018|0084:123.240454',
#  '0018|0085:1H',
#  '0018|0086:1 ',
#  '0018|0087:3 ',
#  '0018|0088:1 ',
#  '0018|0089:308 ',
#  '0018|0091:0 ',
#  '0018|0093:90',
#  '0018|0094:100 ',
#  '0018|0095:485 ',
#  '0018|1030:Perfusie_t1_twist_tra ',
#  '0018|1251:Body',
#  '0018|1310:0\\224\\202\\0',
#  '0018|1312:ROW ',
#  '0018|1314:14',
#  '0018|1315:N ',
#  '0018|1316:1.5259332636804 ',
#  '0018|1318:0 ',
#  '0018|5100:FFS ',
#  '0020|000d:1.2.276.0.7230010.3.1.3.172098957519812515103477578791518032318',
#  '0020|000e:1.2.276.0.7230010.3.1.3.101834603287146520064712801805457931289',
#  '0020|0010:',
#  '0020|0011:24',
#  '0020|0012:11',
#  '0020|0013:8 ',
#  '0020|0032:-94.387765188834\\-67.964980994154\\37.893870946495 ',
#  '0020|0037:1\\-1.99097e-10\\4.9272e-11\\2.05103e-10\\.97071648174839\\-.2402280417895 ',
#  '0020|0052:1.2.276.0.7230010.3.1.3.30710024706774768101572425170598437909',
#  '0020|1040:',
#  '0028|0002:1',
#  '0028|0004:MONOCHROME2 ',
#  '0028|0010:224',
#  '0028|0011:224',
#  '0028|0030:.85714286565781\\.85714286565781 ',
#  '0028|0100:16',
#  '0028|0101:16',
#  '0028|0102:15',
#  '0028|0103:0',
#  '0028|1050:263 ',
#  '0028|1051:607 ',
#  '0028|1052:0 ',
#  '0028|1053:1 ',
#  '0028|1054:US']
