import os
import streamlit as st
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

# Set the default model for policy generation
POLICY_GENERATION_MODEL = "gemini-2.5-flash"

# --- Policy Generation Functions ---

def get_pdf_text(pdf_docs):
    """Reads all uploaded PDF files and returns a single string of text."""
    text = ""
    for pdf in pdf_docs:
        try:
            # Note: PyPDF2 is used here, ensure it is in requirements.txt
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or " "
        except Exception as e:
            st.error(f"Error reading PDF {pdf.name}: {e}")
            return None
    return text.strip()

def generate_policy_section(
    section_title: str,
    user_inputs: dict,
    policy_context: str,
    api_key: str,
    model: str
) -> str:
    """
    Generates a TERT policy section using Gemini, ensuring compliance with NJTI-TERT standards.
    The policy_context can include text from uploaded documents.
    """
    if not api_key:
        return "Error: Gemini API Key is missing. Please enter it in the sidebar."

    try:
        # Initialize client with the user's key
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Error: Failed to initialize Gemini client: {e}"

    # --- Compliance-Focused System Instruction (Hardcoded NJTI-TERT Requirements) ---
    system_instruction = f"""
    You are a legal policy writer and certified NJTI-TERT expert for a Public Safety Answering Point (PSAP).
    Your task is to write the complete text for the policy section titled: "{section_title}".
    The generated policy MUST be compliant with the APCO/NENA ANS 1.105.2-2015 Standard for TERT Deployment.

    **HARD CONSTRAINTS (NJTI-TERT Minimum Training):**
    1. TERT Telecommunicators MUST have successfully completed: FEMA IS-144, FEMA IS-100, and FEMA IS-700.
    2. TERT Team Leaders MUST additionally complete: FEMA IS-200 and FEMA IS-800.

    **AGENCY & LOCAL CONTEXT:**
    - Agency Legal Name: {user_inputs.get('agency_name')}
    - Authority Having Jurisdiction (AHJ): {user_inputs.get('ahj_name')}
    - Required Background Check: {user_inputs.get('background_check')}
    - Additional Required Training: {user_inputs.get('additional_training')}

    **OPTIONAL CONTEXT:**
    - The following text, extracted from existing local policies or agreements, should be used for context and consistency, but NEVER override the Hard Constraints:
    ---
    {policy_context if policy_context else "No external document context provided."}
    ---
    
    The final output MUST be a formal, professional policy section written in clear Markdown format, suitable for inclusion in a TERT Policy Manual. Do not include any introductory or concluding remarks outside the policy text itself.
    """

    # User Query to trigger generation
    user_query = f"Generate the full text for the policy section: {section_title} using all provided context and constraints."
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_instruction)],
        temperature=0.4 # Slightly higher temperature for policy creativity but still low for formality
    )

    try:
        with st.spinner(f"Generating policy section '{section_title}' using {model}..."):
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        return response.text
    except Exception as e:
        st.error(f"Gemini API call failed. Error: {e}")
        return "Error: Failed to generate policy. Check the API key or console for details."


# --- Main Streamlit App ---

def main():
    st.set_page_config(
        page_title="NJTI-TERT Policy Generator",
        page_icon="🚨",
        layout="wide"
    )

    # State initialization for policy sections
    if 'generated_sections' not in st.session_state:
        st.session_state.generated_sections = {}

    # 1. Sidebar for Configuration and PDF Upload
    with st.sidebar:
        st.title("🚨 TERT Policy Config")
        st.caption("Generate compliant TERT policies using Gemini and NJTI-TERT standards.")
        st.markdown("---")

        # API Key Input
        api_key_input = st.text_input(
            "1. Enter your Gemini API Key:",
            type="password",
            help="Your key is not stored beyond this session."
        )
        st.session_state.gemini_api_key = api_key_input
        st.markdown("---")
        
        # Policy Context (PDF) Upload Section
        st.subheader("2. Optional: Local Context Documents (PDF)")
        pdf_docs = st.file_uploader(
            "Upload your existing local PSAP policies or mutual aid agreements (PDFs).",
            accept_multiple_files=True
        )
        
        if st.button("Extract PDF Context"):
            if pdf_docs:
                with st.spinner("Extracting text from documents..."):
                    raw_text = get_pdf_text(pdf_docs)
                    if raw_text:
                        st.session_state.pdf_context = raw_text
                        st.success(f"Successfully loaded {len(raw_text):,} characters of local context.")
                    else:
                        st.error("Could not extract any text from the uploaded PDFs.")
            else:
                st.session_state.pdf_context = ""
                st.warning("No PDFs uploaded.")

        st.markdown("---")
        if st.button('Clear All Generated Sections'):
            st.session_state.generated_sections = {}
            st.session_state.pdf_context = ""
            st.rerun()


    # 2. Main Content Area - Input Fields
    st.title("NJTI-TERT Policy Generation Tool")
    st.caption(f"Using Model: `{POLICY_GENERATION_MODEL}`. Policy sections are based on NJTI-TERT (APCO/NENA ANS 1.105.2-2015).")

    # --- Step 1: General Policy Inputs (Used across all sections) ---
    st.header("Step 1: General PSAP & Authority Information")
    col1, col2 = st.columns(2)
    
    with col1:
        agency_name = st.text_input(
            "Agency Legal Name (Requesting/Host PSAP):",
            value="City of Willow Creek 9-1-1 Emergency Communications Center",
            help="The legal name of your center."
        )
    with col2:
        ahj_name = st.text_input(
            "Authority Having Jurisdiction (AHJ) Name:",
            value="Willow Creek County Public Safety Commission",
            help="The governing body or entity (e.g., County EMA, City Council)."
        )

    # Policy details for Section 3
    st.subheader("Section 3.0 Inputs: Personnel & Training Requirements")
    st.info("The application will hardcode the mandatory FEMA IS-144, IS-100, and IS-700 requirements.")
    
    background_check = st.selectbox(
        "Local Background Check Requirement:",
        options=[
            "Standard Agency Fingerprint-based Check",
            "State-Level Background Check Only",
            "No Additional Requirements Beyond Initial Employment"
        ],
        help="Select your PSAP's specific policy."
    )
    
    additional_training = st.text_area(
        "List any additional *local* training requirements (e.g., PSAP-specific CAD/Radio certification):",
        value="Annual NIMS Refresher; Local CAD System Certification (Level 1); 40 hours of on-the-job mentorship.",
        help="Enter items separated by a semicolon or new line."
    )

    # Package user inputs into a dictionary
    user_inputs = {
        'agency_name': agency_name,
        'ahj_name': ahj_name,
        'background_check': background_check,
        'additional_training': additional_training
    }

    st.markdown("---")
    # --- Step 2: Generate Policy Section ---
    st.header("Step 2: Generate Policy Section 3.0 (Qualifications and Training)")
    
    if st.button("Generate Policy Section 3.0"):
        if not st.session_state.get('gemini_api_key'):
            st.error("Please enter your Gemini API Key in the sidebar to proceed.")
        else:
            section_title = "Section 3.0: TERT Personnel Minimum Qualifications and Training"
            
            # Retrieve PDF context if it was successfully loaded
            pdf_context = st.session_state.get('pdf_context', '')
            
            # Generate the content
            generated_text = generate_policy_section(
                section_title=section_title,
                user_inputs=user_inputs,
                policy_context=pdf_context,
                api_key=st.session_state.gemini_api_key,
                model=POLICY_GENERATION_MODEL
            )
            
            # Store the generated section
            st.session_state.generated_sections[section_title] = generated_text
            st.success(f"Policy section '{section_title}' generated successfully!")
            st.rerun() # Rerun to update the display


    # 3. Main Content Area - Output Display
    st.markdown("---")
    st.header("Generated Policy Sections")
    
    if st.session_state.generated_sections:
        
        # Display the latest generated section (Section 3.0 for now)
        section_to_display = "Section 3.0: TERT Personnel Minimum Qualifications and Training"
        if section_to_display in st.session_state.generated_sections:
            st.subheader(section_to_display)
            # Use an editable text area for review and final editing
            st.session_state.generated_sections[section_to_display] = st.text_area(
                "Review and Edit Generated Policy Text:",
                st.session_state.generated_sections[section_to_display],
                height=600,
                key="policy_edit_area"
            )
        
        # Final Download Option (for all collected sections)
        full_policy_text = "\n\n---\n\n".join(
            [f"## {title}\n\n{content}" for title, content in st.session_state.generated_sections.items()]
        )
        
        st.download_button(
            label="Download Full Draft Policy (Markdown)",
            data=full_policy_text,
            file_name="draft_tert_policy.md",
            mime="text/markdown"
        )
        
    else:
        st.info("No policy sections have been generated yet. Complete Step 1 and click 'Generate Policy Section 3.0' in Step 2.")


if __name__ == "__main__":
    main()
