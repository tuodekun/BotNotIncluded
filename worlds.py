import collections
import os.path as path
import os

import yaml

import utils

ONI_BASE = r"C:\Program Files (x86)\Steam\steamapps\common\OxygenNotIncluded"
ASSETS_BASE = path.join(ONI_BASE, "OxygenNotIncluded_Data", "StreamingAssets")

clusters_base = path.join(ASSETS_BASE, "dlc", "expansion1", "worldgen", "worlds")

version_paths = [
    "",
    path.join("dlc", "expansion1"),
]


def read_yaml(folder):
    data = {}
    for child in os.listdir(folder):
        child_path = path.join(folder, child)
        if path.isfile(child_path):
            with open(child_path, 'r') as f:
                data[child] = yaml.safe_load(f)
        elif path.isdir(child_path):
            data[child] = read_yaml(child_path)
    return data


def read_worldgen():
    for version_path in version_paths:
        worldgen_base = path.join(ONI_BASE, ASSETS_BASE, version_path, "worldgen")
        for child in os.listdir(worldgen_base):
            child_path = path.join(worldgen_base, child)
            if not path.isdir(child_path):
                continue
            suffix = '' if version_path == '' else '_' + path.split(version_path)[-1]
            utils.save_lua(path.join(utils.DIR_OUT, f"worldgen_{child}{suffix}.lua"),
                           read_yaml(child_path))


if __name__ == '__main__':
    read_worldgen()
