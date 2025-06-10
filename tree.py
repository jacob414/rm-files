import paramiko
import json
import os
import re


def is_web_link(path_or_name):
    # Enhanced regex pattern to match a broader range of DNS-like strings, including subdomains
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}$"
    # Debugging: Print the input to see what is being matched
    print("Checking:", path_or_name)
    return bool(re.match(pattern, path_or_name))


import re


def is_web_link(path_or_name):
    # Updated regex pattern to exclude spaces and ensure it captures more complex URLs
    pattern = r"^(https?:\/\/)?[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?$"
    return bool(re.match(pattern, path_or_name))


def fetch_metadata_files(ssh, path):
    """Fetch list of metadata files, skipping web-linked files."""
    stdin, stdout, stderr = ssh.exec_command(f'find {path} -name "*.metadata"')
    files = stdout.readlines()
    # Filter out any file paths that resemble web links
    return [line.strip() for line in files if not is_web_link(line)]


def extract_notebook_name(metadata_content):
    """Extract notebook name from metadata content, skip if it's a web link."""
    metadata = json.loads(metadata_content)
    notebook_name = metadata.get("visibleName", "Unknown Notebook")
    if is_web_link(notebook_name):
        return None  # Skip this notebook name
    return notebook_name


def fetch_and_organize_notebook_names(ssh, metadata_files):
    """Fetch metadata content, extract notebook names, and organize by directory, skipping web links."""
    notebooks_structure = {}
    for file_path in metadata_files:
        stdin, stdout, stderr = ssh.exec_command(f'cat "{file_path}"')
        metadata_content = "".join(stdout.readlines())
        notebook_name = extract_notebook_name(metadata_content)
        if notebook_name is None:  # Skip over web-linked files
            continue
        directory = os.path.dirname(file_path)
        if directory not in notebooks_structure:
            notebooks_structure[directory] = []
        notebooks_structure[directory].append(notebook_name)
    return notebooks_structure


def print_notebooks_structure(notebooks_structure, prefix=""):
    """Print notebooks structure with indentation for directories."""
    for directory, notebooks in sorted(notebooks_structure.items()):
        short_directory = "/".join(
            directory.split("/")[-2:]
        )  # Simplify directory for printing
        print(f"{prefix}{short_directory}/")
        for notebook in sorted(notebooks):
            print(f"{prefix}    {notebook}")


def main():
    ssh_host = "rm2"  # The hostname of your ReMarkable tablet
    ssh_user = "root"  # Default user for ReMarkable
    path_to_notebooks = "/home/root/.local/share/remarkable/xochitl/"

    # Setup SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ssh_host, username=ssh_user, allow_agent=True)

    # Fetch metadata files, organize, and print notebook names in a structured manner, skipping web links
    metadata_files = fetch_metadata_files(ssh, path_to_notebooks)
    notebooks_structure = fetch_and_organize_notebook_names(ssh, metadata_files)
    print_notebooks_structure(notebooks_structure, "├── ")

    # Cleanup
    ssh.close()


if __name__ == "__main__":
    main()
