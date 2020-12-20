# Source Data Formats

DISCO can transform source models if the input data is structured in a
supported format.

Source models in a directory structure must have the file ``format.toml`` that
specifies its type with the key ``type``.

Source models defined by a JSON file must specify their type with the key
``type``.


## Source Tree 1
This format requires the following directory structure:

```
source_model_directory
├── format.toml
├── <substation>
│   ├── *.dss
│   └── <substation>--<feeder>
│       ├── *.dss
│       └── hc_pv_deployments
│           ├── feeder_summary.csv
│           └── <placement>
│               ├── <sample>
│               │   ├── <penetration-level>
│               │   │   └── PVSystems.dss
│               │   │   └── PVSystems.dss
│               │   └── pv_config.json
└── profiles
    └── <profile>.csv
```

## Source Tree 2
This format requires the following directory structure:

```
source_model_directory
├── inputs
│   ├── <feeder>
│   │   ├── LoadShapes
│   │   │   ├── <profile>.csv
│   │   ├── OpenDSS
│   │   │   ├── *.dss
│   │   ├── PVDeployments
│   │   │   └── new
│   │   │       ├── <dc-ac-ratio>
│   │   │       │   ├── <scale>
│   │   │       │   │   ├── <placement>
│   │   │       │   │   │   ├── <sample>
│   │   │       │   │   │   │   ├── PV_Gen_<sample>_<penetration-level>.txt
├── format.toml
```

## GEM
This format requires a JSON file that specifies paths to existing models.

TODO

## EPRI
This format requires source models downloaded by DISCO with the command ``disco
download-source epri``.
