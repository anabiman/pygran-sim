# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.0.0]
### Added

- Source code from PyGran repo
- CHANGELOG for version logging
- CircleCI config for continuous integration
- Added License file

## [1.0.1]
### Added

- Version printed to log file

## [1.0.2]
### Added
- Keyword 'psd_style' (default: 'numberbased') to particle distribution
- Versioneer for automated version control

### Changed
- Log filename from 'dem' to 'pygran'
- Fixed bug (missing dimension for cylindrical boxes) in 'models' module 
- CI migration to github actions

### Removed
- generator module

## [1.0.3]
### Added
- requiremens.txt to src dir

### Changed
- Numerous minor fixes and improvements in code quality

## [1.1.0]
### Added
- Generic EngineAPI class for engines
- Simple engine for 1D contact mechanics
- Generic ProtoInput base class for engine params
- Methods EngineAPI.SetupPrint and EngineAPI.setupWrite

### Changed
- Refactored code for generic engine implementation
- Merged DEMPy and Liggghts into `LiggghtsAPI`, a subclass of EngineAPI
- Improved mechanism for runtime discovery of engines

### Removed
- Redundant engine_liggghts.DEMPy
- Methods EngineAPI.printSetup and EngineAPI.writeSetup
