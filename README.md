# SC-Screen-Clip

A background utility for Star Citizen players that automatically watches your screenshot folders, copies new captures to the clipboard, displays a Windows toast notification with a thumbnail, and posts the screenshot to a dedicated Discord channel via a webhook.

## Features
- **Auto-Clipboard**: New screenshots are instantly copied to your clipboard for easy pasting into Discord or other apps.
- **Windows Notifications**: Shows a square-cropped thumbnail of your screenshot as a toast notification.
- **Discord Integration**: Automatically uploads screenshots to a Discord channel of your choice.
- **Folder Watching**: Monitors both LIVE and PTU screenshot directories by default.

## Getting Started

### 1. Get the Package
The easiest way for most users to get the program is to download it directly from GitHub:

1. Visit the GitHub repository URL (URL will be provided once pushed).
2. Click the green **Code** button and select **Download ZIP**.
3. Locate the downloaded `SC-Screen-Clip.zip` file on your computer.
4. Right-click the zip file and select **Extract All...**, then choose a folder where you want to keep the program (e.g., your Documents folder).
5. Open the extracted folder (it will be named `SC-Screen-Clip-main` or similar).

*Note: If you are a technical user with Git installed, you can simply clone the repository:*
```powershell
git clone <GITHUB_URL_HERE>
cd SC-Screen-Clip
```

### 2. Install `uv`
This project uses `uv` for fast, reliable Python package management. If you don't have it installed, you can install it via PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
*For other platforms or manual installation, see the [official uv documentation](https://docs.astral.sh/uv/getting-started/installation/).*

### 3. Configuration (`.env` file)
The script uses environment variables for configuration. A template is provided in `sample.env`.

#### Webhook Permissions & Security
- **Permissions**: To create a webhook, you need the **Manage Webhooks** permission in the Discord channel. If you don't have this, you will need to ask a server administrator to create one for you and provide the URL.
- **Security**: **Keep your Webhook URL secret.** Anyone with the URL can post messages to that channel. Do not share it publicly or commit it to a public repository.

1. Open a PowerShell terminal in the folder where you extracted the program.
   - *Quick tip: Click the address bar at the top of the folder window, type `powershell`, and press Enter.*
2. Copy the sample file to create your local `.env` file:
   ```powershell
   copy sample.env .env
   ```
3. Open `.env` in a text editor (like Notepad) and update the following values:
   - `DISCORD_WEBHOOK_URL`: Your Discord channel's webhook URL.
   - `USER_NAME`: Your Discord name (this will be included in the message content).

Example `.env` content:
```env
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
USER_NAME="Citizen_John"
```

### 4. Run the Script
The easiest way to run the script is to double-click the `SC-Screen-Clip.bat` file. This will automatically handle the creation of a virtual environment and installation of all required dependencies.

Alternatively, you can run it via PowerShell:

```powershell
uv run SC-Screen-Clip.py
```

To stop the script, simply close the terminal window or press `Ctrl+C`.

## Dependencies
- `Pillow`: Image processing.
- `pywin32`: Windows clipboard integration.
- `watchfiles`: Efficient filesystem monitoring.
- `winsdk`: Windows Runtime API for toast notifications.
- `requests`: Posting to Discord webhooks.
- `python-dotenv`: Loading configuration from `.env`.

---

## Disclaimer
**Use of this script is totally at your own risk.** The authors and contributors are not responsible for any damage, data loss, or account issues resulting from its use. Star Citizen is a trademark of Cloud Imperium Games. This is an unofficial community tool.
