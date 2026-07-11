# EbookAlchemist-Portable

A **fully offline, privacy-first** desktop application that converts ebooks
between many formats. Point it at files or entire folders, pick a target
format, and convert. The released Windows package is **all-inclusive** &mdash;
it bundles the conversion engine, so there is **nothing else to download**.

## Features

- **Convert between many formats**, including HTML, EPUB, MOBI, AZW3, PDF, FB2,
  DOCX, RTF, LIT, PDB, TXT, and more.
- **Add files or whole folders.** Folders are scanned **recursively**, so
  ebooks inside sub-folders are included automatically.
- **Drag-and-drop** files and folders straight onto the window.
- **Batch conversion** with a progress bar and a live log.
- **Choose an output folder**, or write results next to each source file.
- **Strong conversion engine.** Conversion is powered by calibre's
  `ebook-convert`, the most capable open-source ebook conversion engine.

## Privacy & security

This app performs **no network access whatsoever**. Your files never leave your
computer. Everything runs locally as a subprocess with no shell interpolation.
See [SECURITY.md](SECURITY.md) for full details.

## Download & run (end users)

1. Go to the **Actions** tab (or the **Releases** page for tagged versions).
2. Download the `EbookAlchemist-Portable-win64` artifact / release ZIP.
3. Extract it anywhere and run `EbookAlchemist.exe`.

No installer, no Python, no calibre install required &mdash; the engine is
bundled inside the package.

## Usage

1. Click **Add Files...** or **Add Folder...**, or drag items onto the window.
2. Pick the target format from the **Convert to** drop-down.
3. (Optional) Click **Output Folder...** to choose where results are written.
4. Click **Convert**. Progress and results appear in the log.

## How the build works

A GitHub Actions workflow (`.github/workflows/build.yml`) runs on Windows and:

1. Installs calibre from its official distribution to obtain `ebook-convert`.
2. Copies the calibre engine alongside the app.
3. Uses **PyInstaller** to build a self-contained package that includes the
   engine.
4. Publishes the result as a downloadable ZIP artifact (and attaches it to a
   GitHub Release when you push a `v*` tag).

Because the engine and all of calibre's supporting binaries are large, the
package is a single portable folder distributed as one ZIP (extract and run)
rather than a single loose `.exe`. This keeps it genuinely all-inclusive while
remaining reliable.

## Running from source (developers)

```bash
pip install -r requirements.txt
# Ensure calibre's ebook-convert is on your PATH, or set EBOOK_CONVERT.
python ebook_alchemist.py
```

## Making a release

Push a tag such as `v1.0.0`. The workflow builds the package and attaches the
ZIP to the corresponding GitHub Release automatically.

## Credits

Conversion is performed by [calibre](https://calibre-ebook.com/)'s
`ebook-convert` engine. calibre is a separate project with its own license.
