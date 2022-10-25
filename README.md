# Slow Fault Tree Analyser (SFTA)

A slow (also shitty) fault tree analyser based on the idea presented in
[Wheeler et al. (1977). Fault Tree Analysis Using Bit Manipulation.
IEEE Transactions on Reliability, Volume R-26, Issue 2.
<<https://doi.org/10.1109/TR.1977.5220060>>]

For coherent fault trees (which have only AND gates and OR gates).


## Usage

SFTA is currently a single-file script.

### Linux terminals, macOS Terminal, Git BASH for Windows

1. Make an alias for `sfta.py`
   in whatever dotfile you configure your aliases in:

   ```bashrc
   alias sfta='path/to/sfta.py'
   ```

2. Invoke the alias to analyse a fault tree text file:

   ```bash
   $ sfta [-h] [-v] ft.txt

   Perform a slow fault tree analysis.

   positional arguments:
     ft.txt         name of fault tree text file; output is written unto the
                    directory `{ft.txt}.out/`

   optional arguments:
     -h, --help     show this help message and exit
     -v, --version  show program's version number and exit
   ```

### Windows Command Prompt

1. Add the folder containing `sfta.py` to the `%PATH%` variable

2. Invoke `sfta.py` to analyse a fault tree text file:
   ```cmd
   > sfta.py [-h] [-v] ft.txt

   Perform a slow fault tree analysis.

   positional arguments:
     ft.txt         name of fault tree text file; output is written unto the
                    directory `{ft.txt}.out/`

   optional arguments:
     -h, --help     show this help message and exit
     -v, --version  show program's version number and exit
   ```


## License

**Copyright 2022 Conway** <br>
Licensed under the GNU General Public License v3.0 (GPL-3.0-only). <br>
This is free software with NO WARRANTY etc. etc., see [LICENSE]. <br>


[LICENSE]: LICENSE
