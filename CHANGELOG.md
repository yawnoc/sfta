# Changelog


## [Unreleased]


## [v0.7.1] Readme tweaks (2024-06-14)

- Minor readme tweaks


## [v0.7.0] Modularised and packaged (2024-06-12)

- Modularised to no longer be a single-file script
- Packaged as `sfta` and published to PyPI


## [v0.6.2] No percent-operator string formatting (2023-07-06)

- Rewrote `blunt` without percent operator
- Rewrote `dull` without percent operator


## [v0.6.1] Gates in figure index (2023-04-19)

- Fixed figure index missing gates


## [v0.6.0] Importance (2023-02-14)

- Implemented importance (event contribution divided by gate quantity)


## [v0.5.0] Contributions (2023-02-09)

- Implemented contributions (of each event to a gate)


## [v0.4.0] Figure index & earlier scientific notation (2022-12-02)

- Rewrote `blunt` (decimal places) without `Decimal`
- Rewrote `dull` (significant figures) without `Decimal`
- Coerced `dull` to scientific notation for `9.99...E-3` or lower
- Added index.html to output figures directory


## [v0.3.1] Determinism II (2022-11-29)

- Fixed summation dependent on event declaration order
- Sorted cut set factors by event declaration order


## [v0.3.0] Determinism (2022-11-28)

- Fixed multiplication dependent on event declaration order
- Sorted cut set output by string (after sorting by quantity value)
- Added `cut_set_order` to cut set output


## [v0.2.5] `comment` property (2022-11-28)

- Added property setting `comment` for Event and Gate


## [v0.2.4] Label vertical fit (2022-11-03)

- Fixed over-tall labels for Consolas


## [v0.2.3] Consolas (2022-11-03)

- Actually updated demos for Consolas


## ~~[v0.2.2] Consolas (2022-11-03)~~ (release cancelled)

- Added Consolas to start of font stack


## [v0.2.1] Line spacing (2022-11-02)

- Increased label line spacing


## [v0.2.0] SVG output (2022-11-02)

- Implemented SVG generation
- Added property setting `is_paged` for Gate
- Added check for already set `time_unit`
- Made `create_directory_robust` remove then make
- Minor code fixes


## [v0.1.0] First unstable (2022-10-27)

- First seemingly working version. SVG generation yet to be implemented.


[Unreleased]: https://github.com/yawnoc/sfta/compare/v0.7.1...HEAD
[v0.7.1]: https://github.com/yawnoc/sfta/compare/v0.7.0...v0.7.1
[v0.7.0]: https://github.com/yawnoc/sfta/compare/v0.6.2...v0.7.0
[v0.6.2]: https://github.com/yawnoc/sfta/compare/v0.6.1...v0.6.2
[v0.6.1]: https://github.com/yawnoc/sfta/compare/v0.6.0...v0.6.1
[v0.6.0]: https://github.com/yawnoc/sfta/compare/v0.5.0...v0.6.0
[v0.5.0]: https://github.com/yawnoc/sfta/compare/v0.4.0...v0.5.0
[v0.4.0]: https://github.com/yawnoc/sfta/compare/v0.3.1...v0.4.0
[v0.3.1]: https://github.com/yawnoc/sfta/compare/v0.3.0...v0.3.1
[v0.3.0]: https://github.com/yawnoc/sfta/compare/v0.2.5...v0.3.0
[v0.2.5]: https://github.com/yawnoc/sfta/compare/v0.2.4...v0.2.5
[v0.2.4]: https://github.com/yawnoc/sfta/compare/v0.2.3...v0.2.4
[v0.2.3]: https://github.com/yawnoc/sfta/compare/v0.2.2...v0.2.3
[v0.2.2]: https://github.com/yawnoc/sfta/compare/v0.2.1...v0.2.2
[v0.2.1]: https://github.com/yawnoc/sfta/compare/v0.2.0...v0.2.1
[v0.2.0]: https://github.com/yawnoc/sfta/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/yawnoc/sfta/releases/tag/v0.1.0
