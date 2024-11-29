import gradio as gr
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend API URL
API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")


def fetch_namespaces():
    """
    Fetch namespaces (repositories) from the backend.
    """
    try:
        response = requests.get(f"{API_URL}/namespaces")
        if response.status_code == 200:
            return response.json().get("namespaces", [])
    except Exception as e:
        print(f"Error fetching namespaces: {e}")
    return []


def submit_repository(repo_url):
    """
    Clone and index a new repository by sending it to the backend.
    """
    try:
        response = requests.post(f"{API_URL}/submit-repo", json={"repo_url": repo_url})
        if response.status_code == 200:
            return response.json().get("message", "Repository indexed successfully! 🚀")
        else:
            return f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return f"Failed to clone repository: {str(e)}"


def query_with_history(message, history, namespace):
    """
    Query the backend with history.
    """
    try:
        formatted_history = [
            {"role": "user", "content": human} if i % 2 == 0 else {"role": "assistant", "content": ai}
            for i, (human, ai) in enumerate(history)
        ]
        payload = {"query": message, "history": formatted_history, "namespace": namespace}
        response = requests.post(f"{API_URL}/query", json=payload)
        if response.status_code == 200:
            return response.json().get("answer", "No response.")
        else:
            return f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return f"Failed to process query: {str(e)}"


def create_ui():
    namespaces = fetch_namespaces()

    with gr.Blocks() as demo:
        gr.Markdown("## Codebase Chat App with Repository Management")

        # Shared state for the namespace
        namespace_state = gr.State(value=None)

        with gr.Row():
            with gr.Column():
                repo_url_input = gr.Textbox(label="GitHub Repository URL", placeholder="Enter repo URL to clone")
                clone_button = gr.Button("Clone Repository")
                clone_status = gr.Textbox(label="Clone Status", interactive=False)

            with gr.Column():
                namespace_dropdown = gr.Dropdown(
                    choices=namespaces,
                    label="Namespace",
                    interactive=True,
                )

        # Chat interface
        chat = gr.ChatInterface(
            lambda message, history: query_with_history(message, history, namespace_state.value),
            title="Codebase Chat",
            examples=["What does this repo do?", "Explain this function."],
        )

        # Handlers for namespace selection and repository cloning
        def update_namespace_or_clone(repo_url, selected_namespace):
            if repo_url:
                message = submit_repository(repo_url)
                updated_namespaces = fetch_namespaces()
                return (
                    gr.update(choices=updated_namespaces, value=None),
                    gr.update(value=message),
                    None,
                )
            elif selected_namespace:
                namespace_state.value = selected_namespace
                return gr.update(), gr.update(), None
            return gr.update(), "Please provide a repository URL or select a namespace.", None

        clone_button.click(
            update_namespace_or_clone,
            inputs=[repo_url_input, namespace_dropdown],
            outputs=[namespace_dropdown, clone_status, namespace_state],
        )

        namespace_dropdown.change(
            update_namespace_or_clone,
            inputs=[repo_url_input, namespace_dropdown],
            outputs=[namespace_dropdown, clone_status, namespace_state],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()
