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
    """
    Create Gradio UI with repository management and chat functionality, preserving custom CSS.
    """
    namespaces = fetch_namespaces()

    # Define custom CSS
    custom_css = """
        .contain-chatbox {
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        .header-row {
            flex-shrink: 0;
        }
        .full-height-chatbox {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            overflow: hidden;
        }
        .full-height-chatbox > div {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        .full-height-chatbox .wrapper {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        .full-height-chatbox .wrapper > div:last-child {
            flex-grow: 1;
            min-height: 0;
            overflow-y: auto;
        }
        .full-height-chatbox .block {
            padding: 0 !important;
            margin: 0 !important;
        }
        .full-height-chatbox .chatbot {
            height: 100% !important;
            max-height: none !important;
        }
        .full-height-chatbox .chat-bubble {
            margin-bottom: 0 !important;
        }
        .full-height-chatbox .chat-bubble-row {
            margin-bottom: 0 !important;
        }
        .full-height-chatbox .wrapper > div {
            padding: 0 !important;
        }
        .full-height-chatbox .wrapper > .block:first-child {
            display: none !important;
        }
        .full-height-chatbox .examples {
            display: none !important;
        }
        .full-height-chatbox .generate-box {
            margin-bottom: 0 !important;
        }
        .full-height-chatbox .input-row {
            margin-bottom: 0 !important;
        }
        .full-height-chatbox .input-row + div {
            display: none !important;
        }
        .full-height-chatbox .wrapper > div:nth-child(2) {
            flex-grow: 1 !important;
            min-height: 0 !important;
        }
        .centered-markdown {
            text-align: center !important;
            width: 100% !important;
        }
    """

    with gr.Blocks(css=custom_css) as demo:
        namespace_state = gr.State(value=None)
        chat_history = gr.State(value=[])

        with gr.Column(elem_classes="contain-chatbox"):
            gr.Markdown(
                "## Codebase Chat App with Repository Management",
                elem_classes="centered-markdown header-row",
            )

            with gr.Row(elem_classes="header-row"):
                with gr.Column():
                    repo_url_input = gr.Textbox(label="GitHub Repository URL", placeholder="Enter repo URL to clone")
                    clone_button = gr.Button("Git Clone 😺")
                    clone_status = gr.Textbox(label="Clone Status", interactive=False)

                with gr.Column():
                    namespace_dropdown = gr.Dropdown(
                        choices=namespaces,
                        label="Namespace",
                        interactive=True,
                    )

            # Chat container with preserved styles
            with gr.Column(elem_classes="full-height-chatbox", elem_id="chat-container"):
                chatbot = gr.Chatbot(label="Codebase Chatbot", type="messages", elem_id="chatbot")
                message_input = gr.Textbox(placeholder="Enter your message here...")
                send_button = gr.Button("Send")

        def update_namespace_or_clone(repo_url, selected_namespace):
            if repo_url:
                message = submit_repository(repo_url)
                updated_namespaces = fetch_namespaces()
                return gr.update(choices=updated_namespaces, value=None), message, []
            elif selected_namespace:
                # Reset chat history when a namespace is selected
                return gr.update(), f"Selected namespace: {selected_namespace}", []
            return gr.update(), "Please provide a repository URL or select a namespace.", []

        def handle_query(message, history, namespace):
            # Ensure namespace is selected before handling query
            if namespace is None:
                return history + [{"role": "system", "content": "Please select a namespace first!"}], gr.update(value="")
            # Append user message and system response
            response = query_with_history(message, history, namespace)
            return (
                history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}],
                gr.update(value=""),  # Clear input box after sending
            )

        def reset_chat_on_namespace_change(selected_namespace):
            # Reset chat history only when switching namespaces
            if selected_namespace:
                return [], f"Switched to namespace: {selected_namespace}"
            return [], "No namespace selected."

        clone_button.click(
            update_namespace_or_clone,
            inputs=[repo_url_input, namespace_dropdown],
            outputs=[namespace_dropdown, clone_status, chat_history],
        )

        namespace_dropdown.change(
            reset_chat_on_namespace_change,
            inputs=[namespace_dropdown],
            outputs=[chat_history, clone_status],  # Reset chat history only here
        )

        send_button.click(
            handle_query,
            inputs=[message_input, chat_history, namespace_dropdown],
            outputs=[chatbot, message_input],  # Reset message_input only after query
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()
