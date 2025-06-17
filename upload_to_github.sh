#!/bin/bash

# 🚀 GitHub Upload Script for Streamlined Drug Approval Tracker

# STEP 1: Initialize Git repository
echo "🛠️  Initializing Git repository..."
git init

# STEP 2: Configure Git identity (if not already set)
echo "🧾 Configuring Git user identity..."
git config user.name "Your Name"
git config user.email "your.email@example.com"

# STEP 3: Create a secure .gitignore file
echo "🧹 Creating .gitignore..."
cat <<EOF > .gitignore
# Ignore Python cache
__pycache__/
*.py[cod]

# Ignore virtual environments
venv/
.env
.env.*

# Ignore logs and temporary files
*.log
*.tmp
*.swp
*.DS_Store
*.pdf

# Jupyter/IPython files
.ipynb_checkpoints/

# Output data
outputs/
*.csv

# System files
Thumbs.db
EOF

# STEP 4: Stage all project files
echo "📦 Staging all files..."
git add .

# STEP 5: Commit with message
echo "📝 Creating initial commit..."
git commit -m "Initial commit: Streamlined Drug Approval Tracker 🚀"

# STEP 6: Add remote repository (replace with your GitHub repo URL)
read -p "🔗 Enter your GitHub repository URL (e.g. https://github.com/username/repo.git): " remote_url
git remote add origin "$remote_url"

# STEP 7: Push to GitHub
echo "🚀 Pushing code to GitHub..."
git branch -M main
git push -u origin main

echo "✅ Upload complete! Your project is live on GitHub!"