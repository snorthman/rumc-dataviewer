from pathlib import Path

import click

from dataviewer import db
from dataviewer import viewport

(valid_keys := list(set(db.dcm_tags.values()))).sort()


@click.group()
def cli():
    pass


@cli.command(name='keys')
@click.option('-o', '--output', 'output', is_flag=True,
              help="Write to keys.txt rather than terminal")
def keys(output: bool):
    """Prints valid keys for --select."""
    if output:
        with open('keys.txt', 'w') as f:
            [f.write(k + '\n') for k in valid_keys]
    else:
        [print(k) for k in valid_keys]


@cli.command(name='new')
@click.option('-i', '--input', 'input', type=click.Path(resolve_path=True, path_type=Path),
              help="Read data from this directory.", prompt='Enter path/to/data_directory', default='.')
@click.option('-o', '--output', 'output', type=click.Path(resolve_path=True, path_type=Path),
              help="Output database to this path.", prompt='Enter output path/to/database', default='./rumc_database.db')
def new(input: Path, output: Path):
    """Create a database given a RUMC data directory. Overwrites existing databases in cwd."""
    if not input.is_dir():
        raise NotADirectoryError("Expected input to be a directory")
    if output.is_dir():
        raise IsADirectoryError("Expected output to be a file")
    db.create(input.absolute(), output.with_suffix('.db').absolute())


@cli.command(name='load')
@click.option('-i', '--input', 'input', type=click.Path(resolve_path=True, path_type=Path, exists=True, dir_okay=False),
              help="Load and view a RUMC database file.",
              prompt='Enter RUMC database file (create using the \'new\' command)')
@click.option('-a', '--all', 'all', is_flag=True,
              help="View entire database without selections.")
@click.option('-s', '--select', 'selection', multiple=True, type=str,
              help="View database with selection, as key=value items. e.g. -s SeriesDescription=naald,nld -s Modality=MR")
def load(input: Path, all: bool, selection):
    """Load a database for later use."""
    try:
        kvp = {}
        if not all:
            if len(selection) > 0:
                for value in selection:
                    k, v = process_selection(value)
                    kvp[k] = v
            else:
                click.echo('Create a selection by submitting a list of dicom metadata key=value items')
                click.echo('Valid keys are found in keys.txt (case sensitive!), try \'dataviewer --keys\'\n')
                click.echo('e.g. SeriesDescription=naald,nld\n')
                click.echo(
                    'creates a selection of series where dicom metadata Series Description contains either \'naald\' or \'nld\'')
                click.echo('A blank input is considered the end of the list of key=value items\n')
                while value := click.prompt(f'key=value ({len(kvp) + 1})', type=str, default=''):
                    k, v = process_selection(value)
                    if k and v:
                        kvp[k] = v

        conn = db.Connection(input)

        try:
            db_input_path = Path(conn._c.execute("SELECT * FROM InputPath").fetchone()[1])
        except:
            db_input_path = ''

        if len(kvp) > 0:
            selection, series = conn.select(**kvp)
            viewport.Viewer(input, db_input_path, selection, kvp, series).run()
        else:
            viewport.Viewer(input, db_input_path, conn.select_all()).run()
    except Exception as e:
        click.echo(e)


def process_selection(value: str):
    if len(value) > 0:
        if '=' in value:
            if not value.endswith('='):
                k, v = value.split('=', maxsplit=1)
                if k in valid_keys:
                    return k, v
                else:
                    click.echo('Ignored input, invalid key')
            else:
                click.echo('Ignored input, empty value')
        else:
            click.echo('Ignored input, no \'=\' found')
    return False, False