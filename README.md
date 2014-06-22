mcworldtrim
===========

This is a simple world trim script for Minecraft using the `InhabitedTime`
value in chunks to determine which regions can be safely deleted.

## Requirements

* Python 2.7
* [pymclevel](https://github.com/mcedit/pymclevel)
* scipy
* numpy

## Usage

**Important:** Before doing anything make sure that you have backups. You are using this program at your own risk. 

### Extracting the data from your world save

Executing `extract` will generate a file called `world.json` in your working directory containing
the accumulated inhabited time for each region in your world.

```
worldtrim.py extract <path to your world>
```

Expect the extraction to run several hours if your world size exceeds a few GB
because each chunk has to be loaded in order to access its metadata.
It can be stopped with `^C` at any point and continued later.
Alternatively, the extracted data can be used to trim the part of the world that has already been processed.
Note that continuing the extraction skips the number of regions that have been extracted before
(instead of checking which regions have been extracted).
This means that regions might be skipped altogether if new regions were generated between two partial runs.

### Visualizing what will be trimmed

Before trimming your world you should check whether the parameters are right for you by running `show`
which will print the number of regions that can be deleted as well as generate a map of the world
saved in `world.png` in your working directory.

```
worldtrim.py show
```

In the world map each pixel represents one region colored depending on how the region is classified.

Color  | Class
:----- | :---------
white  | spawn area
green  | inhabited
yellow | connected to inhabited region
red    | uninhabited
transparent | not generated

### Trimming the world

Running the `trim` command will delete all uninhabited regions as well as the ones outside of the defined world border.

```
worldtrim.py trim <path to your world>
```

### Configuring the trimming

The classification of regions can be configured using the following parameters.
They have no affect when passed to the `extract` command.

Parameter | Unit | Default | Meaning
--------- | ---- | ------- | -------
`--center` | regions (512m) | 0,0 | Center of both the spawn area and the map border.
`--border` | regions (512m) | 6000 | Distance from 0,0 beyond which all regions are deleted.
`--spawn` | regions (512m) | 16 | Distance from 0,0 within which all regions are kept.
`--inhabited` | ticks | 18000 | Time before a chunk is considered inhabited.
`--old` | days | 60 | Time before a region is considered old
`--deleted-dir` | | | If set trimmed regions will be moved to this directory instead of being deleted.

The `--old` option is a safeguard to avoid deleting newly generated regions and is only applied in `trim`.
A region has to be older than the specified value to be considered for deletion.

Note that the counted ticks may be less than the time that players actually spent in your world if your server
had problems with lag as is often the case in vanilla Minecraft.

### Cleaning up

Finally, running the `clean` command will delete all generated files from your working directory.

```
worldtrim.py clean
```
