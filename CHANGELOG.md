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
