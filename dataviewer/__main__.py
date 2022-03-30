from viewport import Viewer
import db
import click
from pathlib import Path

# command to create a db
# command to load a db
# command to select from db and show

valid_keys = db.tags_dcm.values()


@click.group()
def cli():
    pass


@cli.command(name='new')
@click.option('-i', '--input', 'input', type=click.Path(resolve_path=True, path_type=Path),
              help="Read from this directory", prompt='Enter RUMC data directory')
@click.option('-n', '--name', 'name', type=str,
              help="Database filename", prompt='Enter database file name', default='database')
def new(input: Path, name: str):
    """Create a database given a RUMC data directory."""
    db.create(name, input)


@cli.command(name='load')
@click.option('-i', '--input', 'input', type=click.Path(resolve_path=True, path_type=Path, exists=True, dir_okay=False),
              help="Load and view a RUMC database file",
              prompt='Enter RUMC database file (create using the \'new\' command)')
@click.option('-a', '--all', 'all', is_flag=True,
              help="View entire database without selections")
@click.option('-s', '--select', 'selection', multiple=True, type=str)
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
                click.echo('Valid keys are found in keys.txt (case sensitive!)\n')
                click.echo('e.g. SeriesDescription=naald,nld\n')
                click.echo(
                    'creates a selection of series where dicom metadata Series Description contains either \'naald\' or \'nld\'')
                click.echo('A blank input is considered the end of the list of key=value items\n')
                while value := click.prompt(f'key=value ({len(kvp) + 1})', type=str, default='') > 0:
                    k, v = process_selection(value)
                    kvp[k] = v

        C = db.Connection(input)
        if len(kvp) > 0:
            selection, series = C.select(**kvp)
            Viewer(selection, kvp, series).run()
        else:
            Viewer(C.select_all()).run()
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


if __name__ == '__main__':
    cli()

# @click.command()
# @click.option('--new', 'path', type=click.Path(resolve_path=True, path_type=pathlib.Path))
# def new(path):
#     """Create a database from RUMC data directory."""
#     click.echo(click.format_filename(path))
#
# @click.command()
# @click.option('--newx', 'path', type=click.Path(resolve_path=True, path_type=pathlib.Path))
# def newx(path):
#     """Create a databas from RUMC data directory."""
#     click.echo(click.format_filename(path))
