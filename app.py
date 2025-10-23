import os
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

# --- Core Functions ---

def get_pdf_text(pdf_docs):
    """Reads all uploaded PDF files and returns a single string of text."""
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    """Splits the raw text into smaller, manageable chunks."""
    # Using a large chunk size/overlap suitable for documents where context preservation is key
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000, chunk_overlap=1000
    )
    chunks = splitter.split_text(text)
    return chunks

def get_vector_store(chunks, api_key):
    """Creates embeddings for text chunks and stores them in a FAISS vector store."""
    if not api_key:
        st.error("API Key is missing for embedding generation.")
        return

    # Initialize embeddings with the provided API key
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key # Pass API key directly to LangChain component
    )
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    # Save the vector store locally for quick retrieval later
    vector_store.save_local("faiss_index")
    st.success("Embedding storage successful!")

def get_conversational_chain(api_key):
    """Loads and configures the Question-Answering chain."""
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details.
    If the answer is not in the provided context, just say, "answer is not available in the context", do not provide the wrong answer.\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """
    # Changed model from "gemini-pro" to the default: "gemini-2.5-flash"
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key, # Pass API key directly to LangChain component
        temperature=0.3,
    )
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    chain = load_qa_chain(llm=model, chain_type="stuff", prompt=prompt)
    return chain

def clear_chat_history():
    """Clears the session state's chat history."""
    st.session_state.messages = [
        {"role": "assistant", "content": "upload some pdfs and ask me a question"}
    ]

def user_input(user_question, api_key):
    """Handles the user's question, performs similarity search, and calls the QA chain."""
    if not api_key:
        st.error("API Key is missing. Please enter it in the sidebar.")
        return {"output_text": "Error: API Key not set."}

    # Initialize embeddings with the provided API key for loading/searching the DB
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key # Pass API key directly to LangChain component
    )

    # Load the vector store
    if not os.path.exists("faiss_index"):
        st.warning("Please process the PDFs first.")
        return {"output_text": "Error: PDF documents have not been processed yet."}

    new_db = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
    
    # Perform similarity search to find relevant context
    docs = new_db.similarity_search(user_question)

    # Get the conversational chain, passing the API key
    chain = get_conversational_chain(api_key)

    # Run the chain
    response = chain(
        {"input_documents": docs, "question": user_question},
        return_only_outputs=True
    )

    return response

# --- Main Streamlit App ---

def main():
    st.set_page_config(
        page_title="Gemini PDF Chatbot",
        page_icon="🤖"
    )

    # 1. Sidebar for Configuration and PDF Upload
    with st.sidebar:
        st.title("Configuration & Menu")
        
        # API Key Input (New)
        # Check if key is already in session state and pre-fill the input
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
        
        # Processing Button
        if st.button("Submit & Process"):
            api_key = st.session_state.get("gemini_api_key")
            if not api_key:
                st.error("Please enter your API Key before processing.")
            elif pdf_docs:
                with st.spinner("Processing..."):
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)
                    get_vector_store(text_chunks, api_key)
            else:
                st.warning("Please upload at least one PDF file.")

        st.markdown("---")
        st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

    # 2. Main Content Area (Chat Interface)
    st.title("Chat with PDF files using Gemini 🤖")
    
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

            if not api_key:
                response_text = "Please enter your Gemini API Key in the sidebar before asking a question."
            elif not os.path.exists("faiss_index"):
                 response_text = "Please upload and process your PDF documents first."
            else:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        # Pass API key to user_input function
                        response = user_input(prompt, api_key)
                        
                        full_response = response.get('output_text', 'An error occurred or no response was generated.')
                        
                        placeholder = st.empty()
                        # Streamlit doesn't natively stream LangChain outputs this way, 
                        # so we display the final output once available.
                        placeholder.markdown(full_response)
                        response_text = full_response
            
            # Add assistant message to history
            if response_text is not None:
                message = {"role": "assistant", "content": response_text}
                st.session_state.messages.append(message)


if __name__ == "__main__":
    main()
