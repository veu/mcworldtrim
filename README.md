mcworldtrim
===========

This is a simple world trim script for Minecraft using the `InhabitedTime`
value in chunks to determine which regions can be safely deleted.

## Requirements

* [pymclevel](https://github.com/mcedit/pymclevel)
* scipy
* numpy

## Usage

### Extracting the data from your world save

Executing `extract` will generate a file called `world.json` in your working directory containing the accumulated inhabited time for each region.

```
worldtrim.py extract <path to your world>
```

It can be stopped with `^C` at any point and continued later. Expect this to run several hours if your world is more than a few GB big.

**Important:** Run this on a copy of your world as I haven't verified that the *pymclevel* library I use in this part doesn't modify the data.

### Visualizing what will be trimmed

Before trimming your world you should check whether the parameters are right for you by running `show` which will print the number of regions that will be deleted as well as generate a map of the world saved in `world.png` in your working directory.

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
`--border` | regions (512m) | 6000 | Distance from 0,0 beyond which all regions are deleted.
`--spawn` | regions (512m) | 16 | Distance from 0,0 within which all regions are kept.
`--inhabited` | ticks | 18000 | Time before a chunk is considered inhabited.
`--old` | days | 60 | Time before a region is considered old

The `--old` option will be ignored in `show` and only applied in `trim` which will report the actual number of deleted regions.
The reasoning behind this is that these regions will be deleted eventually unless changed and the option is only there to protect newly generated regions.

### Cleaning up

Finally, running the `clean` command will delete all generated files from your working directory.

```
worldtrim.py clean
```
