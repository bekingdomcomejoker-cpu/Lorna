# Creating Custom Skills

This guide shows you how to extend the Agent Framework with your own skills.

## Skill Basics

A skill is a Python file in the `skills/` directory with a `skill()` function.

### Minimal Skill

```python
# skills/my_skill.py
from typing import Dict, Any

def skill(**kwargs) -> Dict[str, Any]:
    """Your skill description."""
    return {"status": "success", "result": "Your result here"}
```

## Skill Examples

### 1. Google Drive Integration

```python
# skills/google_drive.py
from typing import Dict, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def skill(action: str, **kwargs) -> Dict[str, Any]:
    """
    Interact with Google Drive.
    
    Args:
        action: 'list', 'download', 'upload'
        file_id: File ID (for download)
        folder_id: Folder ID (for list)
        file_path: Local file path (for upload)
    """
    try:
        # Initialize Drive API
        creds = Credentials.from_service_account_file('credentials.json')
        service = build('drive', 'v3', credentials=creds)
        
        if action == "list":
            results = service.files().list(
                q=f"'{kwargs.get('folder_id')}' in parents",
                spaces='drive',
                fields='files(id, name, mimeType)',
                pageSize=10
            ).execute()
            return {"status": "success", "files": results.get('files', [])}
        
        elif action == "download":
            request = service.files().get_media(fileId=kwargs.get('file_id'))
            # Download logic here
            return {"status": "success", "message": "Downloaded"}
        
        elif action == "upload":
            # Upload logic here
            return {"status": "success", "message": "Uploaded"}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"error": str(e)}
```

### 2. Database Query Skill

```python
# skills/database.py
from typing import Dict, Any
import sqlite3

def skill(action: str, query: str = "", db_path: str = "data.db") -> Dict[str, Any]:
    """
    Query a SQLite database.
    
    Args:
        action: 'query' or 'execute'
        query: SQL query
        db_path: Path to database file
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if action == "query":
            cursor.execute(query)
            results = cursor.fetchall()
            return {"status": "success", "results": results}
        
        elif action == "execute":
            cursor.execute(query)
            conn.commit()
            return {"status": "success", "rows_affected": cursor.rowcount}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
```

### 3. Email Skill

```python
# skills/email.py
from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def skill(
    action: str,
    to: str = "",
    subject: str = "",
    body: str = "",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    sender_email: str = "",
    sender_password: str = ""
) -> Dict[str, Any]:
    """
    Send emails.
    
    Args:
        action: 'send'
        to: Recipient email
        subject: Email subject
        body: Email body
        sender_email: Your email
        sender_password: Your email password (or app-specific password)
    """
    try:
        if action == "send":
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return {"status": "success", "message": f"Email sent to {to}"}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"error": str(e)}
```

### 4. Web Scraping Skill

```python
# skills/web_scraper.py
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup

def skill(url: str, selector: str = "") -> Dict[str, Any]:
    """
    Scrape a web page.
    
    Args:
        url: URL to scrape
        selector: CSS selector for elements to extract
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if selector:
            elements = soup.select(selector)
            data = [elem.get_text(strip=True) for elem in elements]
        else:
            data = soup.get_text(strip=True)
        
        return {"status": "success", "data": data}
    
    except Exception as e:
        return {"error": str(e)}
```

### 5. Code Execution Skill (with safety)

```python
# skills/code_executor.py
from typing import Dict, Any
import subprocess
import os

def skill(language: str, code: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute code safely (Python, JavaScript, etc.).
    
    Args:
        language: 'python', 'javascript', 'bash'
        code: Code to execute
        timeout: Execution timeout in seconds
    """
    try:
        if language == "python":
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
        elif language == "javascript":
            result = subprocess.run(
                ["node", "-e", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
        elif language == "bash":
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
        else:
            return {"error": f"Unsupported language: {language}"}
        
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    except subprocess.TimeoutExpired:
        return {"error": f"Execution timeout after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}
```

## Skill Development Tips

1. **Keep it simple**: One skill = one responsibility
2. **Handle errors**: Always return `{"error": "..."}` on failure
3. **Document parameters**: Use docstrings for clarity
4. **Test locally**: Run your skill function directly before adding to agent
5. **Use environment variables**: Store API keys in `.env` files
6. **Return consistent format**: Always return a dictionary

## Testing Your Skill

```python
# test_my_skill.py
from skills.my_skill import skill

# Test the skill directly
result = skill(param1="value1", param2="value2")
print(result)
```

## Deploying Your Skill

1. Save as `skills/my_skill.py`
2. Restart the agent (it auto-loads)
3. Use in conversation: "Use my_skill to do X"

## Skill Registry

The agent automatically discovers and loads all `.py` files in the `skills/` directory (except those starting with `_`).

To see loaded skills:
```python
from agent import Agent
agent = Agent()
print(agent.skill_registry.list_skills())
```

## Advanced: Async Skills

For long-running operations, you can use async:

```python
# skills/async_skill.py
import asyncio
from typing import Dict, Any

async def async_operation():
    await asyncio.sleep(2)
    return "Done!"

def skill(**kwargs) -> Dict[str, Any]:
    """Skill with async operations."""
    result = asyncio.run(async_operation())
    return {"status": "success", "result": result}
```

## Troubleshooting

**Skill not loading?**
- Check file is in `skills/` directory
- Ensure it has a `skill()` function
- Check console for import errors

**Skill not being called?**
- Make sure the agent understands what it does (improve docstring)
- Check the LLM is parsing the action name correctly
- Try: "Use web_search to find X"

**Skill execution fails?**
- Add try/except blocks
- Return error dictionary on failure
- Check environment variables and API keys
