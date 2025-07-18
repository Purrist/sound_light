#!/usr/bin/env bash
# exit on error
set -o errexit

# Install project dependencies from requirements.txt
pip install -r api/requirements.txt

# Set the FLASK_APP environment variable for the migration command
export FLASK_APP=api.app

# Run the database migrations to ensure the schema is up to date
flask db upgrade