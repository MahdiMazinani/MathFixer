# Third-party notices

## Pandoc

MathFixer can bundle the unmodified Pandoc command-line executable and invokes it
as a separate subprocess for isolated formula conversion.

- Project: Pandoc — universal markup converter
- Copyright: John MacFarlane and Pandoc contributors
- License: GNU General Public License, version 2 or later, with additional
  third-party notices listed by the Pandoc project
- Official source and releases: https://github.com/jgm/pandoc
- License text: https://github.com/jgm/pandoc/blob/main/COPYING.md
- Copyright and component notices: https://github.com/jgm/pandoc/blob/main/COPYRIGHT

The exact Pandoc version in a Windows executable is the version reported by
`pandoc --version` on the machine that ran `scripts/build_windows.ps1`.

MathFixer's own source remains under its stated license. Anyone distributing a
binary that contains Pandoc is responsible for satisfying Pandoc's GPL source,
notice, and license requirements for the exact bundled version.

## PySide6 Essentials / Qt

The desktop interface uses PySide6 Essentials and Qt under their respective
open-source licensing terms. Distributors must preserve the notices and comply
with the applicable LGPL/GPL option for the exact bundled version.

- Project and licensing: https://doc.qt.io/qtforpython-6/licenses.html

## lxml and pypdf

MathFixer uses lxml for OOXML processing and pypdf for PDF structure validation.
Both projects retain their own copyright and permissive license notices.

- lxml: https://github.com/lxml/lxml
- pypdf: https://github.com/py-pdf/pypdf
