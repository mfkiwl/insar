"""Main entry point to manage all other sub commands
"""
import click
import insar.scripts.process as procc

# class Config(object):
#     def __init__(self):
#         self.verbose = False

# pass_config = click.make_pass_decorator(Config, ensure=True)


# Main entry point:
@click.group()
@click.option('--verbose', is_flag=True)
@click.option(
    '--path',
    type=click.Path(exists=False, file_okay=True, writable=True),
    help="Path to switch to and run command in")
@click.pass_context
def cli(context, verbose, path):
    """Help for the insar group of command"""
    context.obj = {}
    context.obj['verbose'] = verbose
    if path:
        context.obj['path'] = path
        logger.info("Changing directory to {}".format(path))
        os.chdir(path)


# Options for the "process" command
@cli.command()
@click.option('--geojson', '-g', help="File containing the geojson object for DEM bounds")
@click.option(
    "--rate", "-r", default=1, help="Rate at which to upsample DEM (default=1, no upsampling)")
@click.option(
    "--max-height",
    default=10,
    help="Maximum height/max absolute phase for converting .unw files to .tif"
    "(used for contour_interval option to dishgt)")
@click.option(
    "--step",
    "-s",
    type=click.IntRange(min=1, max=len(procc.STEPS)),
    help="Choose which step to start on. Steps: {}".format(procc.STEP_LIST),
    default=1)
@click.option(
    "--max-temporal",
    type=int,
    default=500,
    help="Maximum temporal baseline for igrams (fed to sbas_list)")
@click.option(
    "--max-spatial",
    type=int,
    default=500,
    help="Maximum spatial baseline for igrams (fed to sbas_list)")
@click.option(
    "--looks",
    type=int,
    help="Number of looks to perform on .geo files to shrink down .int, "
    "Default is the upsampling rate, makes the igram size=original DEM size")
@click.option(
    "--lowpass",
    type=int,
    default=1,
    help="Size of lowpass filter to use on igrams before unwrapping")
@click.option(
    "--ref-row",
    type=int,
    help="Row number of pixel to use as unwrapping reference for SBAS inversion")
@click.option(
    "--ref-col",
    type=int,
    help="Column number of pixel to use as unwrapping reference for SBAS inversion")
# @click.pass_obj
def process(**kwargs):
    """Process a stack of Sentinel interferograms

    Contains the steps from SLC .geo creation to SBAS deformation inversion"""
    print('context obj verbose in process func')
    # print(context)
    print(kwargs)
    # if context.obj['verbose']:
    # click.echo("Verbose mode")
    procc.main(kwargs)


if __name__ == '__main__':
    cli(obj={})
