# BotNotIncluded
A personal version of Pywikibot and other scripts for [zh ONI wiki](https://oxygennotincluded.fandom.com/zh), specially tuned for MacOS.

- Dependencies versions are arranged for python 3.11+ . If you are running a different version, you may need to adjust the dependency requirements in `requirements.txt`.
- Make sure to run with Python 3.7+ as some new features are used. (e.g. Insertion-order preservation nature of dict)

# Configure
## Environment variables
You can configure the script with these environment variables:
| Name           | Notes                            | Default                                                                                 |
| -------------- | -------------------------------- | --------------------------------------------------------------------------------------- |
| `BNI_ONI_ROOT` | Root path of the ONI game        | `C:\Program Files (x86)\Steam\steamapps\common\OxygenNotIncluded`                       |
| `BNI_PO_HANT`  | Root path of the zh-hant po file | `C:\Users\%USERNAME%\Documents\Klei\OxygenNotIncluded\mods\Steam\2906930548\strings.po` |

Environment variables can be configured by
```sh
export [KEY]=[VALUE] # temporary configuration
```
or
```sh
echo 'export [KEY]=[VALUE]' >> ~/.zshrc # write into system file for long-term use
```

and can be unset by
```sh
unset [KEY]
```

## Modular Global variables
There are some 'global' (module-level) variables in a number of modules. Most of them are paths to the game data. Before running (especially on a different OS, such as Windows), please check if them fit your actual setup.
A good route for examine all these variables is:
- First check the `utils.py`.
- Then follow the steps of `game_update.py` to examine relevant modules.

# Running specifics
## Run
```sh
python3 -m venv venv --clear # create virtual environment (recommended)
source venv/bin/activate # activate virtual environment
pip3 install -r requirements.txt # install dependencies

# Preparing necessary data

python3 game_update.py

# processing data

deactivate # deactivate virtural environment
```
