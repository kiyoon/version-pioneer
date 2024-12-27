# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [v0.0.9] - 2024-12-27
### :bug: Bug Fixes
- [`2b0a7cf`](https://github.com/kiyoon/version-pioneer/commit/2b0a7cfc574a1f9c4e2056383e4f4e272b424599) - remove tomli dependency in versionscript *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.8] - 2024-12-26
### :sparkles: New Features
- [`5c21ab2`](https://github.com/kiyoon/version-pioneer/commit/5c21ab2303a627c8e651fd0edd736ed97c218081) - automatic parentdir_prefix from pyproject.toml *(commit by [@kiyoon](https://github.com/kiyoon))*

### :white_check_mark: Tests
- [`3b55cb4`](https://github.com/kiyoon/version-pioneer/commit/3b55cb41baee2b791e984a469639680020819acb) - parentdir_prefix auto *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.7] - 2024-12-26
### :bug: Bug Fixes
- [`8362089`](https://github.com/kiyoon/version-pioneer/commit/836208963b1bcff97479ddba0fcebe962735b377) - inconsistency in pep440-master *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.6] - 2024-12-26
### :boom: BREAKING CHANGES
- due to [`12aac03`](https://github.com/kiyoon/version-pioneer/commit/12aac0377034c03df11222d32a16c93d21fa9eaf) - new pep440-master, change pep440-post *(commit by [@kiyoon](https://github.com/kiyoon))*:

  new pep440-master, change pep440-post


### :sparkles: New Features
- [`12aac03`](https://github.com/kiyoon/version-pioneer/commit/12aac0377034c03df11222d32a16c93d21fa9eaf) - new pep440-master, change pep440-post *(commit by [@kiyoon](https://github.com/kiyoon))*

### :bug: Bug Fixes
- [`56d75f5`](https://github.com/kiyoon/version-pioneer/commit/56d75f536cad2b398cb578639e58ae862b0cdc83) - optional default *(commit by [@kiyoon](https://github.com/kiyoon))*

### :wrench: Chores
- [`7c5af53`](https://github.com/kiyoon/version-pioneer/commit/7c5af532f345237d65c150cfb6492d8a1b7c3288) - lint fix *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.5] - 2024-12-26
### :boom: BREAKING CHANGES
- due to [`257069f`](https://github.com/kiyoon/version-pioneer/commit/257069f98a38affc0817094adb88599034f712cf) - consistent naming (version_pioneer_core -> versionscript) and improve docs *(commit by [@kiyoon](https://github.com/kiyoon))*:

  consistent naming (version_pioneer_core -> versionscript) and improve docs


### :bug: Bug Fixes
- [`6abdb7f`](https://github.com/kiyoon/version-pioneer/commit/6abdb7fbb7dd0fd68157056bf0e859514486d327) - handle better CLI dependency check *(commit by [@kiyoon](https://github.com/kiyoon))*

### :recycle: Refactors
- [`257069f`](https://github.com/kiyoon/version-pioneer/commit/257069f98a38affc0817094adb88599034f712cf) - consistent naming (version_pioneer_core -> versionscript) and improve docs *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`49dffcc`](https://github.com/kiyoon/version-pioneer/commit/49dffcc1b161fc3d180ae4ea2c715d793776bc1a) - eliminate __file__ and PROJECT_DIR at top-level *(commit by [@kiyoon](https://github.com/kiyoon))*

### :white_check_mark: Tests
- [`4663e4f`](https://github.com/kiyoon/version-pioneer/commit/4663e4f41ca203ceedf8ba98d9cfd58d1e9ccf49) - minimise dependency for pytest *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.4] - 2024-12-25
### :sparkles: New Features
- [`a91d2cf`](https://github.com/kiyoon/version-pioneer/commit/a91d2cf0606ea137226960bf85108e3302bf4dc0) - --no-vendor installation *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.3] - 2024-12-25
### :bug: Bug Fixes
- [`9bcce0b`](https://github.com/kiyoon/version-pioneer/commit/9bcce0bdcef71295f58e7c199b126f5e96766bc5) - __file__ NameError *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.2] - 2024-12-25
### :bug: Bug Fixes
- [`7007efe`](https://github.com/kiyoon/version-pioneer/commit/7007efe7c85b51785591d08f8fd891583fd6e6c6) - pkg_is_editable *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.0.1] - 2024-12-25
### :construction_worker: Build System
- [`48e11e8`](https://github.com/kiyoon/version-pioneer/commit/48e11e87e2af9090ccea9708e7ff0581656db6d6) - codecov, lockfile update, pyproject *(commit by [@kiyoon](https://github.com/kiyoon))*

### :memo: Documentation Changes
- [`389ca13`](https://github.com/kiyoon/version-pioneer/commit/389ca1308e6a4533bde2370879967bc65b655f48) - overall rewrite (minor) *(commit by [@kiyoon](https://github.com/kiyoon))*

[v0.0.1]: https://github.com/kiyoon/version-pioneer/compare/v0.0.0...v0.0.1
[v0.0.2]: https://github.com/kiyoon/version-pioneer/compare/v0.0.1...v0.0.2
[v0.0.3]: https://github.com/kiyoon/version-pioneer/compare/v0.0.2...v0.0.3
[v0.0.4]: https://github.com/kiyoon/version-pioneer/compare/v0.0.3...v0.0.4
[v0.0.5]: https://github.com/kiyoon/version-pioneer/compare/v0.0.4...v0.0.5
[v0.0.6]: https://github.com/kiyoon/version-pioneer/compare/v0.0.5...v0.0.6
[v0.0.7]: https://github.com/kiyoon/version-pioneer/compare/v0.0.6...v0.0.7
[v0.0.8]: https://github.com/kiyoon/version-pioneer/compare/v0.0.7...v0.0.8
[v0.0.9]: https://github.com/kiyoon/version-pioneer/compare/v0.0.8...v0.0.9
