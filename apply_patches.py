#!/usr/bin/env python3

import os
import sys
import subprocess
import re
from datetime import datetime, timedelta
import random

# Configuration
# Paths to your patches directories
frontend_patches_dir = '/Users/tony/Desktop/Projet4A/frontend-patches'
backend_patches_dir = '/Users/tony/Desktop/Projet4A/backend-patches'

# Contributors' information with desired commit percentages
contributors = [
    {'name': 'TonyTawil', 'email': 'ctawil175@gmail.com', 'percentage': 60},
    {'name': 'VeronicaHoyek', 'email': '202011458@ua.edu.lb', 'percentage': 40}
]

# Timeframe for spreading the commits
start_date = datetime(2024, 10, 1, 14, 0, 0)  # Start date
end_date = datetime(2024, 11, 17, 17, 0, 0)   # End date

# Percentage of patches to apply
max_patches_percentage = 50  # Set to desired percentage (0-100)

# Repository configuration
branch_name = 'main'  # Change if using a different branch

# Function to collect patches from a directory
def get_patches(patches_dir):
    patches = [f for f in os.listdir(patches_dir) if f.endswith('.patch')]
    patches.sort()
    return [os.path.join(patches_dir, f) for f in patches]

# Get all patches
frontend_patches = get_patches(frontend_patches_dir)
backend_patches = get_patches(backend_patches_dir)

# Combine patches, alternating between frontend and backend
all_patches = []
frontend_index = 0
backend_index = 0
while frontend_index < len(frontend_patches) or backend_index < len(backend_patches):
    if frontend_index < len(frontend_patches):
        all_patches.append(frontend_patches[frontend_index])
        frontend_index += 1
    if backend_index < len(backend_patches):
        all_patches.append(backend_patches[backend_index])
        backend_index += 1

total_patches_available = len(all_patches)

if total_patches_available == 0:
    print("No patches found in the specified directories.")
    sys.exit(1)

# Calculate the number of patches to apply based on the percentage
if max_patches_percentage is not None:
    max_patches_percentage = max(0, min(100, max_patches_percentage))  # Ensure percentage is between 0 and 100
    max_patches_to_apply = max(1, int((max_patches_percentage / 100) * total_patches_available))
    total_patches = max_patches_to_apply
    all_patches = all_patches[:total_patches]
else:
    total_patches = total_patches_available

# Calculate the interval between commits
total_seconds = (end_date - start_date).total_seconds()
interval_seconds = total_seconds / total_patches

# Prepare a list of contributors according to the desired percentages
def generate_contributor_sequence(contributors, total_commits):
    # Expand contributors list according to their percentages
    sequence = []
    for contributor in contributors:
        commits = int((contributor['percentage'] / 100) * total_commits)
        sequence.extend([contributor] * commits)

    # Adjust if the total number doesn't match due to rounding
    while len(sequence) < total_commits:
        max_contributor = max(contributors, key=lambda x: x['percentage'])
        sequence.append(max_contributor)
    while len(sequence) > total_commits:
        sequence.pop()

    return sequence

contributor_sequence = generate_contributor_sequence(contributors, total_patches)

# Shuffle the contributor sequence to distribute commits more naturally
random.shuffle(contributor_sequence)

# Apply patches with the specified contributors
current_timestamp = start_date
for i, patch_file in enumerate(all_patches):
    contributor = contributor_sequence[i]
    author_name = contributor['name']
    author_email = contributor['email']

    # Format the commit date
    commit_date = current_timestamp.strftime('%Y-%m-%dT%H:%M:%S')

    # Prepare environment variables for git (committer information)
    env = os.environ.copy()
    env['GIT_COMMITTER_NAME'] = author_name
    env['GIT_COMMITTER_EMAIL'] = author_email
    env['GIT_COMMITTER_DATE'] = commit_date
    env['GIT_TERMINAL_PROMPT'] = '0'  # Prevent git from prompting for input

    print(f"Applying patch: {os.path.basename(patch_file)}")
    print(f"Author & Committer: {author_name} <{author_email}>")
    print(f"Date: {commit_date}\n")

    # Apply the patch without committing
    try:
        result = subprocess.run(
            ['git', 'apply', '--whitespace=nowarn', patch_file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Failed to apply patch: {patch_file}")
        print("Error message:")
        print(e.stderr)
        sys.exit(1)

    # Extract commit message from the patch file
    try:
        with open(patch_file, 'r') as f:
            lines = f.readlines()
        commit_message_lines = []
        recording = False
        for line in lines:
            if line.startswith('Subject:'):
                subject = line[len('Subject:'):].strip()
                # Remove '[PATCH]', '[PATCH X/Y]', and leading numbers with hyphens or spaces
                subject = re.sub(r'^\[PATCH.*?\]\s*', '', subject)
                subject = re.sub(r'^\d+[-\s]+', '', subject)
                commit_message_lines.append(subject)
            elif line.startswith('---'):
                break
            elif recording:
                commit_message_lines.append(line.strip())
            elif line.strip() == '':
                recording = True
        commit_message = '\n'.join(commit_message_lines)
    except Exception as e:
        print(f"Failed to extract commit message from patch: {patch_file}")
        print(f"Error: {e}")
        sys.exit(1)

    # Commit the changes
    try:
        # Add all changes
        result = subprocess.run(
            ['git', 'add', '.'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Commit with author, date, and message
        result = subprocess.run(
            [
                'git', 'commit',
                '--author', f'{author_name} <{author_email}>',
                '--date', commit_date,
                '-m', commit_message
            ],
            check=True,
            env=env,  # Contains committer information
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print("Failed to commit changes.")
        print("Error message:")
        print(e.stderr)
        sys.exit(1)

    # Increment the timestamp
    current_timestamp += timedelta(seconds=interval_seconds)

print("Pushing changes to the remote repository...")
try:
    result = subprocess.run(
        ['git', 'push', 'origin', branch_name],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(result.stdout)
    print(result.stderr)
except subprocess.CalledProcessError as e:
    print("Failed to push changes.")
    print("Error message:")
    print(e.stderr)
    sys.exit(1)

print("All patches applied and pushed successfully.")
