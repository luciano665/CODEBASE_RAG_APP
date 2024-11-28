"""Testing of endpoints"""

from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

@patch("main.clone_repo")
def test_submit_repo(mock_clone_repo):
    mock_clone_repo.return_value = {"status": "success", "message": "Repository cloned successfully."}
    repo_data = {"repo_url": "https://github.com/luciano665/Churn-Prediction_V.f.git"}
    response = client.post("/submit-repo", json=repo_data)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "message" in json_data
    assert json_data["message"] == "Repository cloned successfully."

def test_submit_repo_invalid_url():
    repo_data = {"repo_url": "not_a_valid_url"}
    response = client.post("/submit-repo", json=repo_data)
    assert response.status_code == 400  # Update based on how you handle invalid URLs
    assert "Invalid URL" in response.json()["detail"]

@patch("main.query_codebase")
def test_query_codebase(mock_query_codebase):
    mock_query_codebase.return_value = {"answer": "The main function initializes the app."}
    query_data = {"query": "What does the main function do?"}
    response = client.post("/query", json=query_data)
    assert response.status_code == 200
    json_data = response.json()
    assert "answer" in json_data
    assert json_data["answer"] == "The main function initializes the app."

def test_query_codebase_empty_query():
    query_data = {"query": ""}
    response = client.post("/query", json=query_data)
    assert response.status_code == 422  # FastAPI's default response for invalid input
    assert "Invalid query" in response.json()["detail"]
