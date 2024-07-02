# pgloader guide

`pgloader` has 2 submodules:

- `image`: this module should be imported in your game files; here you can load and get images
- `meta`: this module should only be imported in meta files to specify settings for your images

## Meta

Before loading you should set the unit, a value which is multiplied with the `unit_size` setting.<br>
Ideally the unit should change whenever the window resizes to make sure images stay relative to it.<br>

When loading the folder and all subfolders will be scanned for images and special files. Folders and files
that end with `"_ignore"` will be ignored.<br>
All meta files are executed using the `exec()` function.

**NOTE**: When you call `meta.children_settings` or `meta.sheet_settings` set the default settings with `meta.default_settings` instead of `meta.settings` so the order of calls is irrelevant.

Images are usually loaded and stored as `"folder_name/image_name"`. Each image file can have their associated meta file to apply settings to it only which must have the name `"image_name_meta.py"`. The only allowed functions for this files are `meta.settings`/`meta.default_settings` and `meta.sheet_settings`

A folder can have a `"folder_meta.py"` file that can call:

- `meta.default_settings`: set the default settings for all files in the folder, overriden by the asset metas and children settings
- `meta.children_settings`: specify a dictionary where the keys are a string or a tuple of strings representing the images to apply the settings to and where the values are the actual settings, as a result of `meta.settings`, like `{"img": meta.settings(...), ("img2", "img3"): meta.settings(...), ...}`

The settings you can change are:

- `alpha`: when True call `convert_alpha` after load
- `size`: specific size on load
- `scale`: scale the current size to the specified one
- `global_alpha`: call `set_alpha` with the value
- `unit_size`: multiply this values with the unit
- `colorkey`: call `set_colorkey` with the value
- `smoothscale`: choose between smooth scaling and normal scaling

An asset meta can specify the `meta.default_settings` and then the `meta.sheet_settings` stating the image is a spritesheet. You can then specify how many rows and columns the sheet has and the space between each row and column.<br>
The `coordinate_settings` parameter specify custom settings for specific coordinates, like `{(0, 0): meta.settings(...), ...}`

If you want the images of a subfolder to be loaded as if they were in a parent folder, you can create a file in the parent folder named `"register_parent.meta"` which should only contain an ID and then in the subfolder create a file named `"folder_parent.meta"` which contains the same ID, pairing the two folders.

# Image

In the image module you have simple commands to load and get images.<br>
Note that getting images from a spritesheet is done like so: `"folder/sheet_name(x,y)"`

- `set_unit`: set the unit, ideally you'd change this when the window resizes
- `get_unit`: get the current unit

You have the load functionality:

- `load`: load everything in a folder like specified above
- `reload`: same as load but without specifying the folder (last one is used)
- `refresh`: reload the images without checking for changes in the files; usually called after `set_unit` when the window resizes

You can check if an image exists:

- `exists: check` that image names (example: `"folder/image"`) exist
- `exists_folder`: check that folders (example:`"folder"`) exist
- `exists_sheet`: check that sheets (example: `"folder/sheet"`) exist
- `sheet_has`: check that a sheet exists and has all the coordinates

And you can get images as `Image` objects. This objects hold common information like the image, the raw surface, the rect and the size.<br>
**NOTE**: when reloading/refreshing `Image` objects will not be deleted, rather their surfaces will be updated, so it's safe to store them once.

- `get`: get an `Image` object; the name should be `"folder/image"` or `"folder/sheet(x,y)"`
- `gets`: return a list with multiple calls to `get()`
- `get_from`: return a list of images from the same folder
- `get_all`: return all images from a folder
- `get_sheet`: return a dict where each coordinate is mapped to the corresponding image

Finally some utility functions:

- `default_settings`: specify default settings for every file in every folder; settings are applied at the next load/refresh
- `register_refresh`: register a callback called when reload or refresh are called
