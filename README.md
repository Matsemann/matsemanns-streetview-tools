# Matsemann's Streetview Tools

Utils and a pipeline for taking an equirectangular .360 video and a gpx file, and converting it into an
output usable for Google Streetview and Mapillary.

How it works is that you can specify how often you want an image from the video (in distance), like for instance
every 3 meters. Using the gpx file it will then calculate which frames from the videos to keep. 
This is different from a timelapse, where you for instance have one image every second. This way of doing it handles
that you move at a different pace or even have stops.

After having extracted all the images, a nadir cap (logo on the bottom of the 360 image) can be added, and also
simple image enhancements like contrast, brightness and color. The updated image will also be saved with correct
exif and xmp metadata, saying the location, direction (bearing and heading) of the image and when it was taken.
These images are then ready to be uploaded straight to Mapillary.

Next step is that the images are joined back into a mp4 video with the correct metadata so that time matches
the gpx and that it's considered a 360 file. A new gpx is also saved with the same name as the new video, with
new gpx points matching the frames in the joined video. The video+gpx is then ready for uploading to Streetview,
with a much, much higher quality, accuracy and correctness compared to doing it with the original .360 file.

The pipeline can either be used directly, or you can use the various tools to build your own in python.

### Rationale

Uploading to Street View is very fickle. The original .360 files contain an embedded gps track, but in my
experience it jumps around a lot, making the results bad. Google will also reject videos with little movement,
even though you might have just been unlucky and waited at an intersection when the new chaptered file started.
By instead extracting the images we want at the intervals we want, we have full control of the gps track, no
random movements, no breaks, just a perfectly smooth track, and can control which pictures are being used and
how they look.

<details>
<summary>Even more details</summary>
Normally, if you want to edit the video (like fixing colors or adding nadir cap) metadata is lost, making the file useless
for Street View. This tool, however, bakes in the needed metadata so it keeps working.

Another aspect is how long the processing time is. If I move at 10 km/h, that's about 3 m/s. If my video is
30 fps and Street View only keeps 1 frame every 3 meters, that's 30x wasted work if I had to add the effects to
every frame of the whole video. Instead, I can now do it only to the extracted images, saving lots of processing time.

Some of this could be combated by using timelapse / lower fps when filming. However, my experience is that for Gopro MAX,
the quality is lower when using timelapses (compression artifacts when two images after each other are very dissimilar),
and using photo mode instead the issue is often that it can't take an image often enough, and that the image is hard
to stabilize, as it doesn't have horizon lock as a video has.

There exist other tools for this as well, many used by professionals. However, they often feel very restrictive in what
you can do. This is just code, can change the pipeline to whatever need you have. Many of the other tools also aren't
well suited for automation. Doing this all in code, it's easy to build automagic stuff.
</details>

## Installation

The tool uses ffmpeg and exiftool under the hood, so they need to be installed on the system and in PATH, 
or point to them through `FFMPEG_HOME` and `EXIFTOOL_HOME` env variables.
If you want to use the util to create a nadir cap, imagemagick v7 or later needs to be installed as well,
can point to it using  `MAGICK_PATH` in env.

To install the project and python dependencies, [uv](https://docs.astral.sh/uv/) is used. Run `uv sync` to
install dependencies.

It's possible to run it through Docker if you don't want to install stuff locally.
The Dockerfile also serves as a blueprint on how to set up the project locally.
Note that when running with Docker, you need to mount the folders you want to work on.

```bash
docker build -t matsemanns_streetview_tools .
# and then before all commands later you will have to do
docker run --rm -v "./my/video-folder/:/app/video-folder" matsemanns_streetview_tools <command>
# for instance like
docker run --rm -v "./my/video-folder/:/app/video-folder" matsemanns_streetview_tools uv run cli.py pipeline /app/video-folder/streetview.json
```

## Usage

This is functionality out of the box. If you instead are interested in the parts, or to make your own pipeline,
more details are further down. Mainly, it's used from the command line as so:

```
uv run cli.py [OPTIONS] COMMAND
Commands: 
  image
  pipeline
```
Run with `--help` to see more details, for instance `uv run cli.py image --help` which lists the image commands,
and then `uv run cli.py image nadir --help` for more details on using the specific sub command.

### Pipeline
Main usage of this tool. It takes as input a JSON file close to the video files being worked on
with configurations for that specific "project".
```bash
uv run cli.py pipeline /path/to/my/video/files/street.json 
```

Note that this pipeline is built for my needs. But will explain how I use it, and further down all the parts
are explained so a custom pipeline can be built if needed.

After a trip with the camera, I save all the .360 video files in a folder. I then use Gopro Player to export
them as equirectangular to a new folder. For instance, my .360 files are in `/videos/my-cool-trip/`, and the exported
files in `/videos/my-cool-trip/equi/`. When exporting, I *disable* world lock, *enable* horizontal lock, HEVC 5.3k max bitrate.
Inside the `/videos/my-cool-trip/` folder, I then place my `.gpx` file from the trip (as it's much higher quality from my Garmin than 
Gopro MAX). I also add a `.json` file in the folder with my configurations.

The JSON file could be named `streetconfig.json` and look like:
```json
{
  "project_name": "my_cool_trip",
  "video_files": ["equi/*.mp4"],
  "original_files_folder": ".",
  "gpx_file": "garmin_export.gpx",
  "output_folder": "./streetview",
  "frame_distance_meters": 3,
  "nadir": "./nadir_equirectangular.png",
  "video_time_shift_seconds": 2.0,
  "video_cut_beginning_seconds": 1.0,
  "video_cut_end_seconds": 1.0,
  "contrast": 1.05,
  "color": 1.1
}
```

and I would then run the pipeline by doing
```bash
uv run cli.py pipeline /videos/my-cool-trip/streetconfig.json 
```
the console will show logs and a progress bar. Additionally, a log file will be saved in the output folder
specified in the json config.

#### Explanation of all parameters in JSON file
Paths are relative to the json file itself.  
Required fields: 
* `project_name` is added as a suffix to the final .mp4 video files, just so that it's easier to distinguish them in Street View Studio later.
* `video_files` is a str array of either files or globs. So in the example above it finds all files ending with `.mp4` in the `equi` folder in the folder where
 the json file is located. Can also use a value like `["GS00001.mp4", "GS00002.mp4]` etc. to target specific files.
* `original_files_folder` is where the .360 files are located. In this instance, the dot means the same folder as the json file. The pipeline
 uses those matching .360 files to extract some metadata, as on Windows, Gopro Player can't export GPMFs data.
* `gpx_file`, name of the .gpx file to be used.
* `output_folder`, where to put the finalized files, temp files, logs
* `frame_distance_meters`, a float of how spaced out the frames should be.

Optional fields:
* `nadir`, path to the nadir image to be applied in the bottom of all extracted images.
* `video_time_shift_seconds`, float, can be used to sync the gpx with the video. A positive value is
 used when the gpx lags behind the video. Like if the video shows you at a bridge, but the gpx track
 hasn't reached there yet. Negative if it's the opposite.
* `video_cut_beginning_seconds`, float, can be used to skip the first part of the video, like if that's
 a frame of you pressing the record button.
* `video_cut_end_seconds` same as above but for the end. Even though not always needed, it can be useful to
 set it to some small value due to how video codecs and frames work. Because it could happen that we calculate to
 keep the exact last frame in the video based on the video length+fps, but then it doesn't exist and stuff crashes.
* `contrast`, `color`, `brightness`, `sharpness` are filters that can be used to enhance the image. Default value for
 all of them is 1.0. A higher means more, lower less. Often most useful in the range 0.8-1.5. Note: If you don't need
 an enhancement, set it to `null` or remove it instead of `1.0`, since then the step will be skipped entirely saving time.
* `keep_debug_files`, bool, whether to clean up debug and temp files after it's done.


### Create nadir
```bash
uv run cli.py image nadir INPUT_FILE OUTPUT_FILE
```
can also specify `-w` and `-h` for the size. Example:
```bash
uv run cli.py image nadir test_files/nadir_square.png test_files/nadir_equirectangular.png
uv run cli.py image nadir -w 5376 -h 588 test_files/nadir_square.png test_files/nadir_equirectangular.png
```
This command uses imagemagick's magick command under the hood.

### Test pipeline effects
Useful when running the pipeline is to see how an image would look with various
contrasts, brightness, colors, so you can figure out good values to use for your project.
Take a screenshot of one of your videos and pass in the filename to see how it would look.

```bash
uv run cli.py image show test_files/test_frame.jpg
```
This brings up a GUI showing the image, and can experiment with various values to see what looks best.

If the GUI doesn't work for you, it's also possible to just generate a bunch of variations and look at those.
```bash
uv run cli.py image test-effects test_files/test_frame.jpg
```
this will create a lot of images in a new folder with the same name as the image (`test_files/test_frame/...`).

After finding suitable values, these can then be used in the pipeline JSON file.

## Custom pipeline

See `scripts/pipeline.py` for inspiration on how it works, or as a template for a new one.
Here follows an explanation of the various functionality and how it can be used:

### GPX


### Metadata

### Video

### Image


## Dev setup


```bash
uv run pytest matsemanns_streetview_tools/
uv run pyright matsemanns_streetview_tools/ # optionally with -w
```

## Acks
This project uses ffmpeg, pillow, exiftool, imagemagick and [spatial-media](https://github.com/google/spatial-media) to do its work. Most of the commands
are shown in terminal when applied.