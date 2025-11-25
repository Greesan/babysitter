# Windows Shortcut Setup for BabysitterPOC + Claude Code

## Files Created
- `launch-babysitter-claude.bat` - Batch script to launch WSL, navigate to project, and start Claude Code

## Setup Instructions

### Step 1: Copy the Batch Script to Windows
1. Open Windows File Explorer
2. Navigate to: `\\wsl$\Ubuntu\home\grees\greesCoding\claude-projects\babysitterPOC`
3. Copy `launch-babysitter-claude.bat` to a Windows location, such as:
   - `C:\Users\YourUsername\Scripts\` (recommended)
   - Or anywhere on your Windows filesystem

### Step 2: Create Desktop Shortcut
1. Right-click on your Windows Desktop
2. Select **New > Shortcut**
3. In "Type the location of the item", enter the full path to your batch file:
   ```
   C:\Users\YourUsername\Scripts\launch-babysitter-claude.bat
   ```
4. Click **Next**
5. Name it: `BabysitterPOC - Claude Code`
6. Click **Finish**

### Step 3: Make it Searchable from Taskbar (Optional)
The desktop shortcut is already searchable from Windows Start menu/taskbar search.

To make it even more accessible:
- **Pin to Taskbar**: Right-click the shortcut → "Pin to taskbar"
- **Pin to Start**: Right-click the shortcut → "Pin to Start"

### Step 4: Customize Icon (Optional)
1. Right-click the shortcut → **Properties**
2. Click **Change Icon...**
3. Choose an icon or browse for a custom `.ico` file
4. Click **OK** → **Apply**

## Usage
- **Desktop**: Double-click the shortcut
- **Taskbar Search**: Press `Win` key, type "BabysitterPOC", press Enter
- **Pinned**: Click the taskbar icon (if pinned)

## How It Works
The batch script:
1. Opens Windows Terminal (`wt.exe`)
2. Launches Ubuntu WSL distribution
3. Changes directory to `/home/grees/greesCoding/claude-projects/babysitterPOC`
4. Starts Claude Code (`claude code`)

## Troubleshooting

### "wt.exe not found"
- Install Windows Terminal from Microsoft Store
- Or use alternative command: `wsl -d Ubuntu -- bash -c "cd ... && claude code"`

### Claude Code doesn't start
- Ensure `claude` is in your PATH in WSL
- Test manually: `wsl -d Ubuntu -- bash -c "which claude"`

### Wrong directory
- Verify the path in the batch script matches your actual project location
