# BeamDelta: Alignment tool

A simple GUI interface for python-microscope which allows a compatible camera
(see python-microscope compatibility list) to be used for optical alignment purposes.
The Gui will display live images, calculate and mark beam centroids and then store
an alignment centroid position. Once a position is stored the live centroid then 
displays a pixel based delta position to allow precise alignment between the marked
position and the new beam.

BeamDelta is called from the command line using the following format:

    BeamDelta CAMERA-1-URI [CAMERA-2-URI ... CAMERA-N-URI]

The `CAMERA-URI` arguments are URIs for [Python
microscope](https://www.python-microscope.org/) device servers, and
have the following format:

    PYRO:[microscope_device_name]@[ip_address]:[port]

See `BeamDelta --help` for other options.

## Usage

### Lens alignment

1. align the system with no lenses present using a laser or similar well collimated
beam.
2. position camera in beam.
3. mark centroid.
4. add first lens and check centroid.
5. shift lens in X and Y (perpendicular to optic axis) to align centroids.
6. check for back reflection to ensure the lens is perpendicular to optic axis
7. repeat 5-6 until no change.

### Co-aligning two beams

1. start with one correctly aligned beam.
2. construct a dual camera setup (description needed!)
3. mark centroids on both cameras.
4. turn of first beam, turn on second beam
5. use two mirrors to walk the beam (description needed) so it matches both centroids.
