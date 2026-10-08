# Dependencies

## casparMIX 0.6.0

Procedural page geometry, shader lighting and background composition add no
new build or runtime libraries.

## casparMIX 0.5.0

Native DME/MOVE/3D adds no dependencies beyond the existing CasparCG OpenGL
mixer, C++ standard library and Boost JSON property-tree parser. The optional
capture harness uses the existing FFmpeg CLI.

## casparMIX 0.4.0

New build dependency: **FreeType** headers/library (`find_package(Freetype)`).
New runtime dependencies: FreeType and a readable TrueType font when using
`GRAPHICS`. On Arch Linux add `freetype2` and `ttf-dejavu` to the package's
runtime dependencies; `freetype2` also includes its build headers. Other fonts
can be selected with `<graphics><font>/absolute/path/font.ttf</font></graphics>`.
Default proportional probes prefer installed Arial, then Noto/DejaVu on Linux;
monospace uses Noto/DejaVu before Courier.
Windows uses Arial/Courier. Monospace can be overridden with
`configuration.graphics.monospace-font`. Fonts are not redistributed by the patch. Installing the
font is not required to use existing CasparCG commands; missing fonts reject
only creation of a native GRAPHICS producer.

Earlier casparMIX releases introduced no additional library dependencies.
The engine uses the existing C++ standard library and the existing CasparCG audio/OpenGL mixers.
Existing upstream dependencies and optional modules remain unchanged.

The developer release exporter requires Git and Python 3 (standard library only).
Neither is a new dependency for building or running the exported engine patch.
Package recipes should carry the patch as a local source with its SHA-256 checksum.

The optional regression harness also needs the FFmpeg command-line tools and a
working OpenGL session. These are developer test requirements, not new libraries
for the exported patch.
