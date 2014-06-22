# Minecraft World Trimmer 1.1
#
# Requirements: Python 2.7, pymclevel (mcedit), numpy, scipy

import sys
import os
import shutil
import signal
import json
import numpy
import scipy.misc
import pymclevel
import argparse
import traceback
import datetime
import itertools


USAGE ="""%(prog)s [options] <command> [<world folder>]

Commands:
  extract - extract information from regions in <world folder>
  trim    - remove regions from <world folder>
  show    - print information and generate map for deleted regions
  clean   - remove all files generated by %(prog)s"""
DATA_PATH = 'world.json'
MAP_PATH = 'world.png'


class Application(object):

    def run(self, **kwargs):
        self.stop = False

        # copy arguments
        for i, arg in kwargs.iteritems():
            setattr(self, i, arg)
    
        # try loading region data
        self.region_data = None
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH) as f:
                self.region_data = json.load(f)
        elif self.command in ('show', 'trim'):
            raise Exception("Please run extract first.")

        # check if directory for deleted files exists
        if not os.path.isdir(self.deleted_dir):
            raise Exception("'{}' is not a directory.".format(self.deleted_dir))

        # make sure that ^C exits gracefully
        signal.signal(signal.SIGINT, self.signal_handler)

        # execute command
        if hasattr(self, 'do_' + self.command):
            getattr(self, 'do_' + self.command)()
        else:
            raise Exception("Unknown command.")

    def iter_regions(self, folder, skip=0):
        region_dir = folder.getFolderPath("region")
        region_files = os.listdir(region_dir)
        region_files.sort()
        for filename in region_files[skip:]:
            region = folder.tryLoadRegionFile(os.path.join(region_dir, filename))
            if not region is None and region.offsets.any():
                yield region
    
    def iter_chunks(self, region):
        rx, rz = region.regionCoords
        for index, offset in enumerate(region.offsets):
            if offset:
                yield (index % 32 + rx * 32, index / 32 + rz * 32)
    
    def do_extract(self):
        # load folder
        folder = pymclevel.infiniteworld.AnvilWorldFolder(self.world_path)
        num_regions = sum(1 for i in self.iter_regions(folder))

        # check for already extracted data
        if self.region_data is None:
            self.region_data = []
        skip = len(self.region_data)
        if skip:
            sys.stdout.write("{0:,} / {1:,} regions already processed. ".format(skip, num_regions))
            sys.stdout.write("Run clean first if you want to start over.\n")
            if skip == num_regions:
                return

        # extract data
        for region in self.iter_regions(folder, skip):
            if self.stop:
                break
            rx, rz = region.regionCoords
            max_inhabited = 0
            try:
                for cx, cz in self.iter_chunks(region):
                    if region.containsChunk(cx, cz):
                        root_tag = pymclevel.nbt.load(buf=region.readChunk(cx, cz))
                        inhabited = root_tag['Level']['InhabitedTime'].value
                        max_inhabited = max(inhabited, max_inhabited)
            except:
                sys.stderr.write("Ignoring r.{0}.{1}.mca because of errors.\n".format(rx, rz))
            self.region_data.append((rx, rz, max_inhabited))
            if len(self.region_data) % 10 == 0:
                sys.stdout.write('{0:,} / {1:,} regions processed\n'.format(len(self.region_data), num_regions))
        
        # write (partial) data
        with open(DATA_PATH, 'w') as f:
            json.dump(self.region_data, f)
        
    def analyze(self):
        outside = set()
        uninhabited = set()
        connected = set()
        inhabited = set()
        spawn = set()

        # mark uninhabited regions, spawn regions, and regions outside of the border
        for rx, rz, max_inhabited in self.region_data:
            if max(abs(rx - self.center[0]), abs(rz - self.center[1])) > self.border:
                outside.add((rx, rz))
            elif max(abs(rx - self.center[0]), abs(rz - self.center[1])) < self.spawn:
                spawn.add((rx, rz))
            elif max_inhabited >= self.inhabited:
                inhabited.add((rx, rz))
            else:
                uninhabited.add((rx, rz))
        
        # unmark regions whose neighbors are kept
        for rx, rz in uninhabited:
            for nx, nz in [(rx + 1, rz), (rx - 1, rz), (rx, rz + 1), (rx, rz - 1)]:
                if (nx, nz) in inhabited:
                    connected.add((rx, rz))
                    break
        uninhabited = [region for region in uninhabited if not region in connected]
        return spawn, inhabited, connected, uninhabited, outside
    
    def paint(self, img, regions, color):
        for rx, rz in regions:
            img[rz + self.border - self.center[1]][rx + self.border - self.center[0]] = color

    def do_show(self):
        spawn, inhabited, connected, uninhabited, outside = self.analyze()
    
        # print info
        l = len(str(len(self.region_data)))
        sys.stdout.write('total regions:       {1:{0}}\n'.format(l, len(self.region_data)))
        sys.stdout.write('spawn regions:       {1:{0}}\n'.format(l, len(spawn)))
        sys.stdout.write('inhabited regions:   {1:{0}}\n'.format(l, len(inhabited)))
        sys.stdout.write("connected regions:   {1:{0}}\n".format(l, len(connected)))
        sys.stdout.write("uninhabited regions: {1:{0}}\n".format(l, len(uninhabited)))
        sys.stdout.write('outside the border:  {1:{0}}\n'.format(l, len(outside)))
        sys.stdout.write("deletable regions:   {1:{0}}\n".format(l, len(uninhabited) + len(outside)))
    
        # generate image
        img = numpy.zeros((self.border * 2 + 1, self.border * 2 + 1, 4), 'uint8')
        self.paint(img, spawn, (255, 255, 255, 255))
        self.paint(img, inhabited, (0, 255, 0, 255))
        self.paint(img, connected, (255, 255, 0, 255))
        self.paint(img, uninhabited, (255, 0, 0, 255))
    
        # save image
        scipy.misc.imsave(MAP_PATH, img)
        sys.stdout.write("Saved map as {0}.\n".format(MAP_PATH))
    
    def do_trim(self):
        _, _, _, uninhabited, outside = self.analyze()
        sys.stdout.write("deletable regions: {0}\n".format(len(uninhabited)))
        count = 0
        for rx, rz in itertools.chain(uninhabited, outside):
            path = os.path.join(self.world_path, 'region', 'r.{0}.{1}.mca'.format(rx, rz))
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), path)
            if os.path.exists(path):
                last_update = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                now = datetime.datetime.now()
                if last_update < now - datetime.timedelta(days=self.old):
                    if self.deleted_dir:
                        shutil.move(path, self.deleted_dir)
                    else:
                        os.remove(path)
                    count += 1
        sys.stdout.write("deleted regions:   {0}\n".format(count))
    
    def do_clean(self):
        if os.path.exists(DATA_PATH):
            os.remove(DATA_PATH)
        if os.path.exists(MAP_PATH):
            os.remove(MAP_PATH)
    
    def signal_handler(self, signal, frame):
        sys.stdout.write("Aborting...\n")
        self.stop = True
   
   
if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument("command")
    parser.add_argument("world_path", nargs='?')
    parser.add_argument("-b", "--border", action='store', type=int, default=6000,
        dest='border', help="distance from center in regions (512m) beyond which all regions are deleted")
    parser.add_argument("-c", "--center", action='store', type=int, default=[0, 0], nargs=2,
        dest='center', help="distance of center from 0,0 in regions (512m)")
    parser.add_argument("-s", "--spawn", action='store', type=int, default=16,
        dest='spawn', help="distance from center in regions (512m) within which all regions are kept")
    parser.add_argument("-i", "--inhabited", action='store', type=int, default=18000,
        dest='inhabited', help="number of ticks before a chunk is considered inhabited")
    parser.add_argument("-o", "--old", action='store', type=int, default=60,
        dest='old', help="number of days before a region is considered old")
    parser.add_argument("-d", "--deleted-dir", action='store', type=str, default=None,
        dest='deleted_dir', help="move trimmed regions to a different directory instead of deleting")
    args = parser.parse_args()

    try:
        if args.command in ('extract', 'trim') and args.world_path is None:
            raise Exception("World folder missing.")
        Application().run(**vars(args))
    except Exception as e:
        sys.stderr.write("Error: {0} See -h for details.\n".format(e))
        exit(1)
