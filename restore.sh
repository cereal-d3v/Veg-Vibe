#!/bin/bash

# --- Script to restore files from a backup into a new repository ---

# Define the name and path for the backup directory
BACKUP_DIR="$HOME/Desktop/Veg-Vibe_backup"

# Check if the backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found at $BACKUP_DIR. Please make sure the backup was created correctly."
    exit 1
fi

echo "Restoring files from backup..."

# Loop through each item in the backup directory
for item in "$BACKUP_DIR"/*; do
    # Get the base name of the file or directory
    BASE_ITEM=$(basename "$item")

    # Check if a file with the same name exists in the current directory
    if [ ! -e "$BASE_ITEM" ]; then
        echo "Copying missing file: $BASE_ITEM"
        cp -r "$item" .
    fi
done

echo "Restore complete! Missing files have been copied back."
echo "Please review your files and then commit the changes with 'git add .' and 'git commit'."

