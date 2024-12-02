import gradio as gr
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backend API URL
API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")


def fetch_namespaces():
    """Fetch namespaces from the backend."""
    try:
        response = requests.get(f"{API_URL}/namespaces")
        if response.status_code == 200:
            return response.json().get("namespaces", [])
        else:
            print(f"Failed to fetch namespaces. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching namespaces: {e}")
        return []


def submit_repository(repo_url):
    """Clone and index a new repository by sending it to the backend."""
    try:
        response = requests.post(f"{API_URL}/submit-repo", json={"repo_url": repo_url})
        if response.status_code == 200:
            return response.json().get("message", "Repository indexed successfully! 🚀")
        else:
            return f"Error: {response.json().get('detail', 'Unknown error')}"
    except Exception as e:
        return f"Failed to clone repository: {str(e)}"


def query_with_history(message, history, namespace):
    """Query the backend with the chat history."""
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
    """
    Create Gradio UI with repository management and chat functionality.
    """
    namespaces = fetch_namespaces()

    with gr.Blocks() as demo:
        namespace_state = gr.State(value=None)
        chat_history = gr.State(value=[])

        with gr.Column():
            gr.Markdown("## Codebase Chat App with Repository Management")
            
            gr.Markdown("""
            **Instructions:**
            1. Enter the GitHub repository URL you wish to clone and click **Git Clone 😺**.
            2. After cloning, to see the new repository appear in the namespace dropdown, type any character into the URL box and click **Git Clone 😺** again.
            3. Select the desired namespace from the dropdown.
            4. Use the chatbot below to interact with the selected codebase.
            5. I'm so sorry for this :( , I'm currently working on it 🙂‍↕️
            """)
            
            with gr.Row():
                repo_url_input = gr.Textbox(label="GitHub Repository URL", placeholder="Enter repo URL to clone")
                clone_button = gr.Button("Git Clone 😺")
                clone_status = gr.Textbox(label="Clone Status", interactive=False)

                namespace_dropdown = gr.Dropdown(
                    choices=namespaces, label="Namespace", interactive=True
                )

            chatbot = gr.Chatbot(label="Codebase Chatbot", type="messages")
            message_input = gr.Textbox(placeholder="Enter your message here...")
            send_button = gr.Button("Send")

        def update_namespace_or_clone(repo_url, current_namespace):
            """Update namespace dropdown or clone repository."""
            if repo_url:
                message = submit_repository(repo_url)
                updated_namespaces = fetch_namespaces()
                return (
                    gr.update(choices=updated_namespaces, value=None),  # Update namespace dropdown
                    message,  # Show clone status
                    [],  # Clear chat history after cloning
                    None  # Reset namespace_state
                )
            return gr.update(), "Please provide a repository URL.", current_namespace, current_namespace

        def handle_query(message, history, namespace):
            """Handle query submission while preserving chat history."""
            if namespace is None:
                new_history = history + [("System", "Please select a namespace first!")]
                return new_history, new_history, gr.update(value="")
            response = query_with_history(message, history, namespace)
            new_history = history + [(message, response)]
            return (
                new_history,
                new_history,  # Update chat_history state
                gr.update(value=""),  # Clear input box after sending
            )

        def reset_chat_on_namespace_change(selected_namespace, current_namespace):
            """Reset chat history only when switching namespaces."""
            if selected_namespace != current_namespace:
                return [], selected_namespace, f"Switched to namespace: {selected_namespace}"
            return chat_history.value, current_namespace, "No namespace change."

        # Bind clone button to namespace update
        clone_button.click(
            update_namespace_or_clone,
            inputs=[repo_url_input, namespace_state],
            outputs=[namespace_dropdown, clone_status, chat_history, namespace_state],
        )

        # Bind namespace dropdown to chat reset
        namespace_dropdown.change(
            reset_chat_on_namespace_change,
            inputs=[namespace_dropdown, namespace_state],
            outputs=[chat_history, namespace_state, clone_status],
        )

        # Bind send button to query handler
        send_button.click(
            handle_query,
            inputs=[message_input, chat_history, namespace_dropdown],
            outputs=[chatbot, chat_history, message_input],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()