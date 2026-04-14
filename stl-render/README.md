# STL-Render

## Notes
- the project was setup using `uv` to help with managing dependencies and the
  virtual environment. otherwise the `pyproject.toml` list the necessary
  information to run the package.
- if using `uv` you can run the package from the root of the repo with the
  following command
  ```
uv run --package stl-render ./stl-render/main.py ...
  ```
- Open3D does not work on 3.14 or is at least not listed as working as of
  2026-04-13. the project is setup to use python 3.12
- `OffscreenRenderer` is listed as being supported only in linux environments
  and will require mesa drives of somekind (the link the provide to `mesa3d`
  website is showing as `404` as of 2026-04-13)
- the currently used packages have that do not come with the packages themselves
  but the project should be setup to pull those dependencies.
- this process is not very fast and takes 10's or 100's of milliseconds to
  render the necessary view of the STL model. hopefully having some amount of
  GPU acceleration will help (if possible).
