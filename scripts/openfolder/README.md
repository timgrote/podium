# Open Folder Protocol Handler

Registers a custom `openfolder://` protocol on Windows so Conductor can open project Dropbox folders directly in Explorer.

## Setup (one-time, per machine)

Both files live in Dropbox and sync automatically. Just run the registry file:

```
Navigate to D:\Dropbox\TIE\Tools\Conductor\
Double-click install-openfolder.reg and confirm the prompt.
```

That's it. Conductor will now be able to open project folders via the folder icon in the project detail view.

## Files

Both files are in `D:\Dropbox\TIE\Tools\Conductor\`:

- `openfolder.cmd` — Batch script that handles the protocol
- `install-openfolder.reg` — Registry file that registers the protocol (points to the .cmd in this folder)

## How it works

- Conductor renders links like `openfolder://D:/Dropbox/TIE/TBG/HeronLakes`
- Windows recognizes the `openfolder://` protocol and launches `D:\Dropbox\TIE\Tools\Conductor\openfolder.cmd`
- The batch script strips the protocol prefix, converts forward slashes to backslashes, and opens Explorer at that path
- On first click, the browser asks "Allow this site to open openfolder links?" (can be remembered)

## Configuration

The Dropbox base path defaults to `D:/Dropbox/TIE` per user. Each user can override it via their user settings in the API.
