# Open Folder Protocol Handler

Opens project Dropbox folders directly in Windows Explorer from Conductor.

## Setup (one-time, per machine)

Both files sync via Dropbox automatically. You only need to register the protocol:

1. Open `D:\Dropbox\TIE\Tools\Conductor\` in Explorer
2. **Right-click** `install-openfolder.reg` → **Run as administrator**
3. Click **Yes** when Windows asks to confirm the registry change

Done. The reg file registers the `openfolder://` protocol and configures Brave to launch it without prompting.

## Files

Both live in `D:\Dropbox\TIE\Tools\Conductor\`:

| File | Purpose |
|------|---------|
| `openfolder.cmd` | Batch script that receives the link and opens Explorer |
| `install-openfolder.reg` | Registers the `openfolder://` protocol with Windows |

## How it works

1. You click the folder icon on a project in Conductor
2. The browser opens a link like `openfolder://D:/Dropbox/TIE/TBG/HeronLakes`
3. Windows hands it to `openfolder.cmd`, which opens Explorer at that path

## Troubleshooting

- **Nothing happens on click** — Make sure you ran `install-openfolder.reg` on this machine
- **Browser blocks the link** — Look for a popup asking to allow `openfolder://` links and click Allow
- **Wrong Dropbox location** — The base path defaults to `D:/Dropbox/TIE`. If yours is different, an admin can update it in your user settings in Conductor
