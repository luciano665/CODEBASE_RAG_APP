import os
from git import Repo  # Use GitPython for cloning
from fastapi import HTTPException
from pydantic import BaseModel

CLONE_DIR = "./cloned_repos"

class RepoRequest(BaseModel):
    repo_url: str

async def clone_repo(request: RepoRequest):
    """Cloning a public GitHub repository."""
    repo_url = request.repo_url
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(CLONE_DIR, repo_name)

    try:
        # Create the directory if it doesn't exist
        if not os.path.exists(CLONE_DIR):
            os.makedirs(CLONE_DIR)

        # Check if the repository has already been cloned
        if os.path.exists(repo_path):
            return {"status": "already_cloned", "repo_path": repo_path}

        # Clone the repository directly using GitPython
        Repo.clone_from(repo_url, repo_path)
        
        return {"status": "cloned", "repo_path": repo_path}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))