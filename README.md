# python-env


## Setup

1. Download conda from https://docs.conda.io/en/latest/miniconda.html

2. Create Conda environment using the following steps:
```bash 
conda deactivate 
conda env create -f conda requirements.yml
conda activate
```




## Project Organization

    ├── README.md          <- The top-level README for those using this project.
    ├── data               <- All data in here should be temporary, not added to git, 
    │   │                     and used only for processing as part of a notebook worfklow.
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical output datsets, organised by source
    │   └── raw            <- Original data dumps, organised by source
    │
    ├── projects           <- python application for executing workflows:
    |                         each application has it's own folder and contains a readme.md and
    |                         a main.py file as the entry point of the application.
    |
    ├── conda-requirements.yml   <- The requirements file for reproducing the project environment
    │
    ├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
    └── src                <- Source code for use in this project.