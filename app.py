import os
import streamlit as st
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

# Set the default model as requested
DEFAULT_MODEL = "gemini-2.5-flash" 

# --- Core Functions ---

def get_pdf_text(pdf_docs):
    """Reads all uploaded PDF files and returns a single string of text."""
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or " "
        except Exception as e:
            st.error(f"Error reading PDF {pdf.name}: {e}")
            return None
    return text.strip()

def generate_response_from_context(context: str, question: str, api_key: str, model: str) -> str:
    """
    Sends the entire document context and the user's question to the Gemini API
    in a single request for Q&A.
    """
    try:
        # Initialize client with the user's key
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {e}")
        return "Error: Could not initialize Gemini client."

    # Define the system prompt to guide the model
    system_instruction = (
        "You are an expert Q&A assistant. Your task is to answer the user's question based "
        "ONLY on the provided context, which is the text extracted from PDF documents. "
        "If the answer cannot be found in the context, clearly state: 'The answer is not available in the provided documents.'"
        "Maintain a helpful, professional, and detailed tone. Format your answer using markdown for readability."
    )

    # Combine context and question into the user's prompt
    full_prompt = (
        f"CONTEXT FROM UPLOADED DOCUMENTS:\n\n---\n\n{context}\n\n---\n\n"
        f"USER QUESTION: {question}"
    )

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_instruction)],
        temperature=0.3
    )

    try:
        # Call the API
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API call failed. This might be because the context is too large for the model's window. Error: {e}")
        return "Error: Gemini API call failed. Check console for details."

def clear_chat_history():
    """Clears the session state's chat history and document context."""
    st.session_state.messages = [
        {"role": "assistant", "content": "upload some pdfs and ask me a question"}
    ]
    # Also clear the stored PDF text to start fresh
    if "pdf_text" in st.session_state:
        del st.session_state["pdf_text"]

def user_input(user_question, api_key):
    """Handles the user's question by fetching context and calling the single-shot generation."""
    if not api_key:
        return {"output_text": "Error: API Key not set."}
    
    context = st.session_state.get("pdf_text")
    if not context:
        return {"output_text": "Error: PDF documents have not been processed yet. Please upload and process them first."}
    
    # Use the default model for Q&A
    response_text = generate_response_from_context(context, user_question, api_key, DEFAULT_MODEL)
    
    # The output format is simplified since we are not using LangChain's chain output dictionary
    return {"output_text": response_text}

# --- Main Streamlit App ---

def main():
    st.set_page_config(
        page_title="Gemini PDF Chatbot (Single-Shot)",
        page_icon="🤖"
    )

    # 1. Sidebar for Configuration and PDF Upload
    with st.sidebar:
        st.title("Configuration & Menu")
        
        # API Key Input
        default_key = st.session_state.get("gemini_api_key", "")
        api_key_input = st.text_input(
            "1. Enter your Gemini API Key:", 
            type="password",
            value=default_key,
            help="Your key is not stored beyond this session."
        )

        # Update session state with the provided key
        if api_key_input:
            st.session_state.gemini_api_key = api_key_input
            st.info("API Key set!")
        
        # PDF Upload Section
        st.markdown("---")
        st.subheader("2. Upload Documents")
        pdf_docs = st.file_uploader(
            "Upload your PDF Files and Click 'Process'", 
            accept_multiple_files=True
        )
        
        # Processing Button - Now just reads and stores text
        if st.button("Submit & Process"):
            api_key = st.session_state.get("gemini_api_key")
            if not api_key:
                st.error("Please enter your API Key before processing.")
            elif pdf_docs:
                with st.spinner("Processing..."):
                    raw_text = get_pdf_text(pdf_docs)
                    if raw_text:
                        st.session_state.pdf_text = raw_text
                        st.success(f"Successfully loaded {len(raw_text):,} characters of text into context.")
                    else:
                        st.error("Could not extract any text from the uploaded PDFs.")
            else:
                st.warning("Please upload at least one PDF file.")

        st.markdown("---")
        # Clear history button is updated to also clear context
        st.sidebar.button('Clear Chat & Context', on_click=clear_chat_history)

    # 2. Main Content Area (Chat Interface)
    st.title("Chat with PDF files using Gemini 🤖")
    st.caption(f"Model used for Q&A: `{DEFAULT_MODEL}`. The full document text is passed as context.")
    
    # Initialize chat messages
    if "messages" not in st.session_state.keys():
        clear_chat_history()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Handle user input
    if prompt := st.chat_input():
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate assistant response
        if st.session_state.messages[-1]["role"] != "assistant":
            api_key = st.session_state.get("gemini_api_key")

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Pass API key to user_input function
                    response = user_input(prompt, api_key)
                    
                    full_response = response.get('output_text', 'An error occurred or no response was generated.')
                    
                    # Display the final output
                    placeholder = st.empty()
                    placeholder.markdown(full_response)
                    response_text = full_response
            
            # Add assistant message to history
            if response_text is not None:
                message = {"role": "assistant", "content": response_text}
                st.session_state.messages.append(message)


if __name__ == "__main__":
    main()
