import os
import subprocess
from utils.logger import log

def run_terminal_command(command: str) -> str:
    """Runs a silent terminal command in the background."""
    log.info(f"Running terminal command: {command}")
    try:
        # We use a timeout to prevent the agent from getting stuck on an infinite loop command
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        if not output.strip():
            return "Command executed successfully with no output."
        # Truncate output to avoid massive LLM context overload (3000 chars)
        return output[:3000] + ("\n...[output truncated]" if len(output) > 3000 else "")
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 15 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(file_path: str) -> str:
    """Reads the contents of a local file."""
    file_path = os.path.expanduser(file_path)
    log.info(f"Reading file: {file_path}")
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Truncate content to keep prompt size manageable
            return content[:5000] + ("\n...[truncated]" if len(content) > 5000 else "")
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_directory(directory_path: str) -> str:
    """Lists all files and folders in a given directory."""
    directory_path = os.path.expanduser(directory_path)
    log.info(f"Listing directory: {directory_path}")
    try:
        if not os.path.exists(directory_path):
            return f"Error: Directory not found at {directory_path}"
        items = os.listdir(directory_path)
        return "\n".join(items) if items else "Directory is empty."
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def open_file_or_folder(path: str) -> str:
    """Visually opens a file or folder for the user on their screen."""
    path = os.path.expanduser(path)
    log.info(f"Opening file/folder for user: {path}")
    try:
        if not os.path.exists(path):
            return f"Error: Path does not exist: {path}"
        os.startfile(path)
        return f"Successfully opened {path} on the user's screen."
    except Exception as e:
        return f"Error opening path: {str(e)}"

def search_files(directory: str, filename_query: str) -> str:
    """Recursively searches for files/folders matching a query within a directory (Max 10 seconds)."""
    import time
    directory = os.path.expanduser(directory)
    log.info(f"Searching for '{filename_query}' in '{directory}'")
    try:
        if not os.path.exists(directory):
            return f"Error: Directory does not exist: {directory}"
        
        results = []
        start_time = time.time()
        
        for root, dirs, files in os.walk(directory):
            # Timeout after 8 seconds to prevent hanging the AI on massive drives
            if time.time() - start_time > 8:
                results.append("...[Search timed out after 8 seconds. Showing partial results]")
                break
                
            for name in dirs + files:
                if filename_query.lower() in name.lower():
                    results.append(os.path.join(root, name))
                    if len(results) >= 30:
                        results.append("...[Limited to 30 results. Please be more specific]")
                        return "\n".join(results)
                        
        if not results:
            return f"No files matching '{filename_query}' found in {directory}."
        return "\n".join(results)
    except Exception as e:
        return f"Error searching files: {str(e)}"

def web_search(query: str) -> str:
    """Performs a silent web search using DuckDuckGo."""
    log.info(f"Searching web for: {query}")
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No results found."
        
        output = []
        for r in results:
            output.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}")
        return "\n\n".join(output)
    except ImportError:
        log.warning("ddgs not installed. Attempting to install...")
        subprocess.run("pip install ddgs", shell=True)
        return "The search tool was just installed. Please repeat your search."
    except Exception as e:
        return f"Error searching the web: {str(e)}"
