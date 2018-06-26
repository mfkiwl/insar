import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from insar.log import get_log

logger = get_log()


def animate_stack(stack, pause_time=200, display=True, titles=None, save_title=None, **savekwargs):
    """Runs a matplotlib loop to show each image in a 3D stack

    Args:
        stack (ndarray): 3D np.ndarray, 1st index is image number
            i.e. the idx image is stack[idx, :, :]
        pause_time (float): Optional- time between images in milliseconds (default=200)
        display (bool): True if you want the plot GUI to pop up and run
            False would be if you jsut want to save the movie with as save_title
        titles (list[str]): Optional- Names of images corresponding to stack.
            Length must match stack's 1st dimension length
        save_title (str): Optional- if provided, will save the animation to a file
            extension must be a valid extension for a animation writer:
        savekwargs: extra keyword args passed to animation.save
            See https://matplotlib.org/api/_as_gen/matplotlib.animation.Animation.html
            and https://matplotlib.org/api/animation_api.html#writer-classes

    Returns:
        None

    Notes: may need this
        https://github.com/matplotlib/matplotlib/issues/7759/#issuecomment-271110279
    """
    num_images = stack.shape[0]
    if titles:
        assert len(titles) == num_images, "len(titles) must equal stack.shape[0]"
    else:
        titles = ['' for _ in range(num_images)]  # blank titles, same length

    # Use the same stack min and stack max for all colorbars/ color ranges
    minval, maxval = np.min(stack), np.max(stack)
    fig, ax = plt.subplots()
    image = plt.imshow(stack[0, :, :], vmin=minval, vmax=maxval)  # Type: AxesImage

    cbar = fig.colorbar(image)
    cbar_ticks = np.linspace(minval, maxval, num=6, endpoint=True)
    cbar.set_ticks(cbar_ticks)
    cbar.set_label("Centimeters")

    def update_im(idx):
        image.set_data(stack[idx, :, :])
        fig.suptitle(titles[idx])
        return image,

    stack_ani = animation.FuncAnimation(
        fig, update_im, frames=range(num_images), interval=pause_time, blit=False, repeat=True)

    if save_title:
        logger.info("Saving to %s", save_title)
        stack_ani.save(save_title, **savekwargs)

    if display:
        plt.show()


def view_stack(stack, geolist=None, display_img=-1, label="Centimeters", title=""):
    """Displays an image from a stack, allows you to click for timeseries

    Args:
        stack (ndarray): 3D np.ndarray, 1st index is image number
            i.e. the idx image is stack[idx, :, :]
        geolist (list[datetime]): Optional: times of acquisition for
            each stack layer. Used as xaxis if provided
        display_img (int, str): Optional- default = -1, the last image.
            Chooses which image in the stack you want as the display
            display_img = 'avg' will take the average across all images
        label (str): Optional- Label on colorbar/yaxis for plot
            Default = Centimeters
        title (str): Optional- Title for plot

    Returns:
        None

    Raises:
        ValueError: if display_img is not an int or the string 'mean'

    """
    # If we don't have dates, use indices as the x-axis
    if geolist is None:
        geolist = np.arange(stack.shape[0])

    def get_timeseries(row, col):
        return stack[:, row, col]

    imagefig = plt.figure()
    if isinstance(display_img, int):
        image = plt.imshow(stack[display_img, :, :])  # Type: AxesImage
    elif display_img == 'mean':
        image = plt.imshow(np.mean(stack, axis=0))
    else:
        raise ValueError("display_img must be an int or 'mean'")

    cbar = imagefig.colorbar(image)
    cbar.set_label(label)

    timefig = plt.figure()
    if not title:
        title = "Time series for pixel"

    plt.title(title)
    legend_entries = []

    def onclick(event):
        # Ignore right/middle click, clicks off image
        if event.button != 1 or not event.inaxes:
            return
        plt.figure(timefig.number)
        row, col = int(event.ydata), int(event.xdata)
        try:
            timeline = get_timeseries(row, col)
        except IndexError:  # Somehow clicked outside image, but in axis
            return

        legend_entries.append('Row %s, Col %s' % (row, col))

        plt.plot(geolist, timeline, marker='o', linestyle='dashed', linewidth=1, markersize=4)
        plt.legend(legend_entries)
        x_axis_str = "SAR image date" if geolist is not None else "Image number"
        plt.xlabel(x_axis_str)
        plt.ylabel(label)
        plt.show()

    imagefig.canvas.mpl_connect('button_press_event', onclick)
    plt.show(block=True)
