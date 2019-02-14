Directions:
-----------
- Copy "startsg_auto_jasper" and "auto_jasper_*.m" to your mlib_devel directory.
- Edit the "auto_jasper_*.m" file to point to the correct reference design, output directory, and the right number of antennas to loop through.
- Run the "startsg_auto_jasper" script.


Example:
--------
```
./startsg_auto_jasper X 16
```
This will build all the X-engines for the 32k correlator (i.e. 16 FFT stages).
MATLAB will open a window and iterate through 8-, 16-, 32- and 64-antenna versions of the reference design with 16 FFT stages.

Some miscellaneous notes:
-------------------------
As I was compiling the X-engine this appeared to use ~4GB worth of RAM. Other designs may use more or less. I was able to run 3 of these in parallel, for 1k, 4k and 32k, by opening three terminals and running the command three times. Don't let power-saving turn off your screen, that seems to freeze Matlab.

TODO:
-----
- Automating the backend, once the frontend is done.
