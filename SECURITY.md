# Security & Privacy

Privacy and security are core design goals of EbookAlchemist-Portable.

## No network access

The application never connects to the internet. All conversion happens locally
on your machine using the bundled engine. Your files and their contents are
never uploaded, transmitted, or shared with any server.

- The GUI code (`ebook_alchemist.py`) contains no networking imports or calls.
- The bundled `ebook-convert` engine is invoked as a local subprocess only,
  with no shell interpolation (arguments are passed as a list, not a string).

## Self-contained

The released package bundles calibre's `ebook-convert` engine, so you do not
need to install calibre, Python, or anything else. Extract the ZIP and run.

## Local-only file handling

- Converted output is written next to the source file, or to an output folder
  you explicitly choose.
- The app never deletes your source files.
- The app refuses to overwrite a source file with its own output.

## Supply chain

- Builds run on GitHub-hosted runners via a workflow you can inspect in
  `.github/workflows/build.yml`.
- The conversion engine is downloaded at build time from calibre's official
  distribution server (`download.calibre-ebook.com`).
- Only pinned, widely-used official GitHub Actions are used.

## Verifying for yourself

Because the source is public, you can read every line, build the package
yourself from the workflow, and confirm there is no telemetry or network I/O.

## Reporting a vulnerability

If you discover a security issue, please open a private security advisory on the
repository rather than a public issue.
