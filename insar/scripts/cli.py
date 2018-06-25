"""Main entry point to manage all other sub commands
"""
import click
import insar
import matplotlib.pyplot as plt


# Main entry point:
@click.group()
@click.option('--verbose', is_flag=True)
@click.option(
    '--path',
    type=click.Path(exists=False, file_okay=False, writable=True),
    default='.',
    help="Path to switch to and run command in")
@click.pass_context
def cli(ctx, verbose, path):
    """Command line tools for processing insar."""
    # Store these to be passed to all sub commands
    ctx.obj = {}
    ctx.obj['verbose'] = verbose
    ctx.obj['path'] = path


# COMMAND: DOWNLOAD
@cli.command()
@click.option("--date", "-r", help="Validity date for EOF to download")
@click.option(
    "--mission",
    "-m",
    type=click.Choice(["S1A", "S1B"]),
    help="Sentinel satellite to download (None gets both S1A and S1B)")
@click.pass_obj
def download(context, **kwargs):
    """Download Sentinel precise orbit files.

    Saves files to current directory, regardless of what --path
    is given to search.

    Download EOFs for specific date, or searches for Sentinel files in --path.
    With no arguments, searches current directory for Sentinel 1 products
    """
    insar.eof.main(context['path'], kwargs['mission'], kwargs['date'])


# COMMAND: DEM
@cli.command()
@click.option(
    "--geojson",
    "-g",
    required=True,
    type=click.File('r'),
    help="File containing the geojson object for DEM bounds")
@click.option(
    "--rate",
    "-r",
    default=1,
    type=click.IntRange(0, 30),  # Reasonable range of upsampling rates
    help="Rate at which to upsample DEM (default=1, no upsampling)")
@click.option(
    "--output",
    "-o",
    type=click.File('w'),
    default="elevation.dem",
    help="Name of output dem file (default=elevation.dem)")
@click.option(
    "--data-source",
    "-d",
    type=click.Choice(['NASA', 'AWS']),
    default='NASA',
    help="Source of SRTM data. See insar.dem docstring for more about data.")
@click.pass_obj
def dem(context, geojson, data_source, rate, output):
    """Stiches .hgt files to make one DEM and .dem.rsc file

    Pick a lat/lon bounding box for a DEM, and it will download
    the necessary SRTM1 tile, combine into one array,
    then upsample using upsample.c

    Suggestion for box: http://geojson.io gives you geojson for any polygon
    Take the output of that and save to a file (e.g. mybox.geojson

    Usage:

        insar dem --geojson data/mybox.geojson --rate 2

        insar dem -g data/mybox.geojson -r 2 -o elevation.dem

    Default out is elevation.dem for upsampled version, elevation_small.dem
    Also creates elevation.dem.rsc with start lat/lon, stride, and other info.
    """
    insar.dem.main(geojson, data_source, rate, output)


# COMMAND: PROCESS
@cli.command()
@click.option(
    '--geojson',
    '-g',
    help="File containing the geojson object for DEM bounds",
    type=click.Path(resolve_path=True))
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
    type=click.IntRange(min=1, max=len(insar.scripts.process.STEPS)),
    help="Choose which step to start on. Steps: {}".format(insar.scripts.process.STEP_LIST),
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
@click.pass_obj
def process(context, **kwargs):
    """Process stack of Sentinel interferograms.

    Contains the steps from SLC .geo creation to SBAS deformation inversion"""
    if context['verbose']:
        click.echo("Verbose mode")

    insar.scripts.process.main(context['path'], kwargs)


# COMMAND: kml
@cli.command()
@click.argument("tiffile", required=True)
@click.argument("rscfile", default="dem.rsc")
@click.option("--title", "-t", help="Title of the KML object once loaded.")
@click.option("--desc", "-d", help="Description for google Earth.")
def kml(tiffile, rscfile, title, desc):
    """Creates .kml file for tif image

    TIFFILE is the .tif image to load into Google Earth
    RSCFILE is the .rsc file containing lat/lon start and steps
        Default will be 'dem.rsc'


        insar kml 20180420_20180502.tif dem.rsc -t "My igram" -d "From April in Hawaii" > out.kml
    """
    rsc_data = insar.sario.load_dem_rsc(rscfile)
    print(insar.dem.create_kml(rsc_data, tiffile, title=title, desc=desc))


# COMMAND: view-dem
@cli.command()
@click.argument("demfile", type=click.Path(exists=True, dir_okay=False), nargs=-1)
def view_dem(demfile):
    """View a .dem file with matplotlib.

    Can list multiple .dem files to open in separate figures.
    """
    for fname in demfile:
        dem = insar.sario.load_file(fname)
        plt.figure()
        plt.imshow(dem)
        plt.colorbar()

    # Wait for windows to close to exit the script
    plt.show(block=True)


# COMMAND: animate
@cli.command()
@click.option(
    "--ref-row",
    '-r',
    type=click.INT,
    help="Row number of pixel to use as unwrapping reference (for SBAS inversion)")
@click.option(
    "--ref-col",
    '-c',
    type=click.INT,
    help="Column number of pixel to use as unwrapping reference (for SBAS inversion)")
@click.option(
    "--pause",
    '-p',
    default=200,
    help="For --animate, time in milliseconds to pause"
    " between stack layers (default 200).")
@click.option(
    "--save", '-s', help="If you want to save the animation as a movie,"
    " title to save file as.")
@click.option(
    "--display/--no-display",
    help="Pop up matplotlib figure to view (instead of just saving)",
    default=True)
@click.pass_obj
def animate(context, pause, ref_row, ref_col, save, display):
    """Creates animation for 3D image stack.

    If deformation.npy and geolist.npy or .unw files are not in current directory,
    use the --path option:

        insar --path /path/to/igrams animate

    Note: --ref-row and --ref-col only needed if the inversion
    has not already been done and saved as deformation.npy
    """
    geolist, deformation = insar.timeseries.load_deformation(context['path'], ref_row, ref_col)
    titles = [d.strftime("%Y-%m-%d") for d in geolist]
    insar.plotting.animate_stack(
        deformation, pause_time=pause, display=display, titles=titles, save_title=save)


# COMMAND: view_stack
@cli.command()
@click.option(
    "--ref-row",
    '-r',
    type=click.INT,
    help="Row number of pixel to use as unwrapping reference (for SBAS inversion)")
@click.option(
    "--ref-col",
    '-c',
    type=click.INT,
    help="Column number of pixel to use as unwrapping reference (for SBAS inversion)")
@click.pass_obj
def view_stack(context, ref_row, ref_col):
    """Explore timeseries on deformation image.

    If deformation.npy and geolist.npy or .unw files are not in current directory,
    use the --path option:

        insar --path /path/to/igrams view_stack

    Note: --ref-row and --ref-col only needed if the inversion
    has not already been done and saved as deformation.npy
    """
    geolist, deformation = insar.timeseries.load_deformation(context['path'], ref_row, ref_col)
    if geolist is None or deformation is None:
        return

    insar.plotting.view_stack(deformation, geolist, image_num=-1)
