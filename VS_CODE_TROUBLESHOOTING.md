# VS Code Integration Troubleshooting Guide

If you're experiencing issues with VS Code integration in SarvajñaGPT, follow these steps to resolve them:

## Method 1: Use the start.bat File

The easiest way to ensure VS Code integration works properly is to use the included `start.bat` file:

1. Close any running instances of SarvajñaGPT
2. Double-click on `start.bat` in the project's root directory
3. The script will automatically:
   - Find VS Code on your system
   - Set the correct environment variable
   - Start SarvajñaGPT

## Method 2: Manual Environment Variable Setup

If you prefer to set things up manually:

1. Find the path to your VS Code executable (usually `Code.exe`)
   - Common locations:
     - `C:\Program Files\Microsoft VS Code\Code.exe`
     - `C:\Users\<username>\AppData\Local\Programs\Microsoft VS Code\Code.exe`
     - `C:\Users\<username>\AppData\Local\Microsoft\WindowsApps\code.exe` (Microsoft Store version)

2. Set the environment variable:
   - Open PowerShell as Administrator
   - Run: `[Environment]::SetEnvironmentVariable("POWER_VSCODE_BIN", "C:\path\to\your\Code.exe", "User")`
   - Replace `C:\path\to\your\Code.exe` with the actual path

3. Restart SarvajñaGPT

## Method 3: Add VS Code to PATH

If you don't want to set an environment variable:

1. Make sure VS Code is added to your system PATH
   - During VS Code installation, there's an option to "Add to PATH"
   - If you missed this option, you can reinstall VS Code or add it manually
   
2. To add manually:
   - Search for "Environment Variables" in Windows search
   - Edit the PATH variable for your user account
   - Add the folder containing Code.exe (not the .exe itself)

3. Restart your computer to ensure the PATH changes take effect

## Testing the Fix

To verify VS Code integration is working:
1. Start SarvajñaGPT
2. Use any feature that should open a file in VS Code
3. VS Code should launch and open the specified file

## Still Having Issues?

If you continue to experience problems:
1. Check the console output for any error messages related to "VSCODE_OPEN"
2. Verify that you can open VS Code from the command line by typing `code`
3. Ensure VS Code is properly installed and not corrupted

For detailed debugging, you can examine the `power_router.py` file which handles VS Code integration.