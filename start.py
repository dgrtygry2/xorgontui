import os
import subprocess
import sys
import shutil
import time
import numpy as np
from PIL import Image
from caca.canvas import Canvas
from caca.display import Display


def check_and_install_dependencies():
    """
    Check and install required dependencies if not already installed.
    Dependencies: Xephyr, ffmpeg, libcaca, Python packages (Pillow, numpy, caca)
    """
    print("Checking dependencies...")

    # Check for Xephyr
    if not shutil.which("Xephyr"):
        print("Xephyr not found. Installing...")
        subprocess.run(["sudo", "apt-get", "install", "-y", "xserver-xephyr"], check=True)

    # Check for ffmpeg
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found. Installing...")
        subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)

    # Check for libcaca
    if not shutil.which("cacaview"):
        print("libcaca not found. Installing...")
        subprocess.run(["sudo", "apt-get", "install", "-y", "libcaca-dev", "caca-utils"], check=True)

    # Check for required Python packages
    try:
        import PIL
        import numpy
        import caca
    except ImportError:
        print("Required Python packages not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "numpy", "Pillow", "caca"], check=True)

    print("All dependencies are installed!")


def run_xorg_app_in_xephyr(command, width=800, height=600, scale_factor=2):
    """
    Runs an Xorg GUI app in Xephyr, captures its screen, and renders it as a TUI with color and performance optimization.
    """
    # Xephyr command to create a virtual X server
    xephyr_cmd = [
        "Xephyr", ":1", f"-screen {width}x{height}", "-ac", "-br", "-noreset"
    ]
    os.environ["DISPLAY"] = ":1"  # Point DISPLAY to Xephyr

    # Start Xephyr
    xephyr = subprocess.Popen(xephyr_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # Give Xephyr time to start

    try:
        # Run the GUI app inside Xephyr
        app_process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Setup the canvas for text-based rendering
        canvas_width = width // (8 * scale_factor)
        canvas_height = height // (16 * scale_factor)
        canvas = Canvas(canvas_width, canvas_height)
        display = Display(canvas)

        # Capture Xephyr's framebuffer in real time using ffmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-f", "x11grab", "-i", ":1", 
            "-vf", f"scale={canvas_width}:{canvas_height}", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24", "-an", "-sn", "-f", "rawvideo", "-"
        ]
        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        print("\nRendering application... Press Ctrl+C to exit.")

        while True:
            # Read frame data from ffmpeg
            raw_frame = ffmpeg.stdout.read(canvas_width * canvas_height * 3)
            if not raw_frame:
                break

            # Convert raw frame (RGB) to ASCII art with color
            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape(canvas_height, canvas_width, 3)
            for y, row in enumerate(frame):
                for x, pixel in enumerate(row):
                    char, color = get_ascii_char_and_color(pixel)
                    canvas.set_color_ansi(color)
                    canvas.put_char(x, y, char)

            # Refresh the display
            display.refresh()

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up processes
        xephyr.terminate()
        app_process.terminate()
        ffmpeg.terminate()


def get_ascii_char_and_color(pixel):
    """
    Maps RGB pixel values to ASCII characters and color indices.
    :param pixel: A tuple (R, G, B).
    :return: A tuple (character, color index).
    """
    ascii_chars = " .:-=+*%@#"
    intensity = (0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2])  # Grayscale intensity
    char = ascii_chars[int((intensity / 255) * (len(ascii_chars) - 1))]

    # Map RGB to 16 ANSI color codes (basic approximation)
    r, g, b = pixel
    color = 0  # Default black
    if r > 128:
        color |= 1  # Red
    if g > 128:
        color |= 2  # Green
    if b > 128:
        color |= 4  # Blue

    return char, color


if __name__ == "__main__":
    print("Welcome to the Fully-Featured GUI-to-TUI Converter!")
    print("This tool converts graphical apps into ASCII-based TUI with color.")
    print("Press Ctrl+C to exit.\n")

    # Check and install dependencies
    check_and_install_dependencies()

    # Ask user for the app to run
    app_to_run = input("Enter the GUI program to run (e.g., xclock, xterm): ")
    run_xorg_app_in_xephyr(app_to_run)
