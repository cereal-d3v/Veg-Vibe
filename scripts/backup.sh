#!/bin/bash

# --- Script to back up all files in the current directory ---

# Define the name and path for the backup directory
BACKUP_DIR="$HOME/Desktop/Veg-Vibe_backup"

# Ensure the backup directory does not already exist
if [ -d "$BACKUP_DIR" ]; then
    echo "Backup directory already exists. Please remove it first to avoid conflicts."
    exit 1
fi

# Create the backup directory
echo "Creating backup directory: $BACKUP_DIR"
mkdir "$BACKUP_DIR"

# Copy all files and folders (excluding the .git directory) to the backup
echo "Copying files to backup..."
rsync -av --exclude '.git' . "$BACKUP_DIR"

echo "Backup complete! All your files are in $BACKUP_DIR"

# To check the contents of the backup folder you can run the following:
# ls "$BACKUP_DIR"
