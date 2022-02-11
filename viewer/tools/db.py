import sqlite3, json, datetime

def connect(data):
    conn = sqlite3.connect("data.db")
    with conn:
        c = conn.cursor()
        for table in ['Patient', 'Study', 'Serie']:
            c.execute(f"CREATE TABLE IF NOT EXISTS {table} (id text PRIMARY KEY);")
        [parse_patient(conn.cursor(), d) for d in data[:5]]


def str_to_date(date):
    return datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:]))


def parse_patient(cursor: sqlite3.Cursor, data):
    cursor.execute(f"CREATE TABLE IF NOT EXISTS Patient (id text PRIMARY KEY);")
    id = data['id']
    cursor.execute(f'INSERT INTO Patient VALUES (?)', (id,))
    for key, val in data['data'].items():
        parse_study(cursor, {'id': key, 'series': val})


def parse_study(cursor: sqlite3.Cursor, data):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS Study (
            id text PRIMARY KEY, 
            FOREIGN KEY (patient_id) REFERENCES Patient (id)
        );
    """)
    id = data['id']
    cursor.execute(f'INSERT INTO Study VALUES (?)', (id,))
    for val in data['series'].values():
        parse_serie(cursor, val)


def parse_serie(cursor: sqlite3.Cursor, data):
    data['files'] = len(data['files'])
    data['dob'] = str_to_date(data['dob'])
    data['date'] = str_to_date(data['date'])
    data['sampling'] = data.pop('sampling %')
    data['pe_steps'] = data.pop('pe steps')
    data['flip_angle'] = data.pop('flip angle')
    data['file_path'] = data.pop('path')

    columns = data.keys()
    table = []
    for key in columns:
        if key != 'id_series':
            try:
                data[key] = int(data[key])
                table.append(f"{key} integer")
            except:
                table.append(f"{key} text")

    table = ',\n'.join(table)
    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS Serie (
                id_series text PRIMARY KEY, 
                files integer,
                FOREIGN KEY (study_id) REFERENCES Study (id)
            );
        """)
    files = data['files']
    cursor.execute(f'INSERT INTO Serie VALUES (?)', (files,))

    # sql = f"INSERT INTO Serie ({', '.join(columns)}) VALUES ({', '.join([':{0}'.format(col) for col in columns])})"
    # cursor.execute(sql, data)


with open(
        "D:\Repos\RUMCDataViewer\DATA_mediaradngdiagprostatearchivesProstatempMRIScientificArchiveRUMC201420target.json") as f:
    data = json.load(f)
connect(data['patients'])
