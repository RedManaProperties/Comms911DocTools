import os
import streamlit as st
import json
import base64
from PyPDF2 import PdfReader
from google import genai
from google.genai import types
from io import BytesIO

# Set the default model for policy generation (using user's choice: gemini-2.5-flash)
POLICY_GENERATION_MODEL = "gemini-2.5-flash"

# Define all available TERT policy sections for the dropdown
POLICY_SECTIONS = {
    "Section 1.0: Purpose, Scope, and Authority": "Purpose, Scope, and Authority",
    "Section 2.0: Definitions and Acronyms": "Definitions and Acronyms",
    "Section 3.0: TERT Personnel Minimum Qualifications and Training": "Qualifications and Training",
    "Section 4.0: Activation and Deployment Steps": "Activation and Deployment Steps",
    "Section 5.0: Logistics, Finance, and Equipment": "Logistics and Finance", 
    "Section 6.0: Safety, Wellness, and Post-Mission Review": "Safety and Review", 
}


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

def generate_policy_section(
    section_title: str,
    user_inputs: dict,
    policy_context: str,
    api_key: str,
    model: str
) -> str:
    """
    Generates a TERT policy section using Gemini, ensuring compliance with NJTI-TERT standards.
    """
    if not api_key:
        return "Error: Gemini API Key is missing. Please enter it in the sidebar."

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Error: Failed to initialize Gemini client: {e}"

    # --- Section-Specific Prompt Guidance (Ensures correct format/content) ---
    section_specific_prompt_guidance = ""

    if section_title.startswith("Section 1.0"):
        section_specific_prompt_guidance = """
        For this section, you MUST define the program's Purpose (using the TERT Program Goal input), Scope (clearly defining what TERT covers and does not cover), and Authority (referencing the State Authority Reference input). Use standard policy language and separate the three components clearly with subheadings.
        """
    elif section_title.startswith("Section 2.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST define all standard TERT terms (e.g., TERT, PSAP, AHJ, TERT Team Leader, TERT Liaison, EMAC) based on the APCO/NENA standard. Additionally, you MUST include definitions for the following local roles/systems provided by the user: {user_inputs.get('local_roles_to_define')}. Format the output as a clean, alphabetical Markdown definition list (e.g., **TERM**: Definition.).
        """
    elif section_title.startswith("Section 3.0"):
        section_specific_prompt_guidance = """
        For this section, you MUST detail the minimum training and qualification requirements for all TERT personnel (Telecommunicators, Team Leaders, and Supervisors). You must strictly adhere to all SECTION 3.0 HARD CONSTRAINTS listed below. Ensure the local background check and additional local training requirements are clearly integrated.
        """
    elif section_title.startswith("Section 4.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST provide a detailed, step-by-step procedure for TERT Activation and Deployment. Structure the content into three logical subsections: **I. Requesting PSAP Role**, **II. Activation Procedures**, and **III. TERT Package Requirements**.
        - Activation Procedures MUST detail the process using the Local Request Mechanism: {user_inputs.get('local_request_mechanism')}.
        - TERT Package Requirements MUST list the Essential TERT Package Items: {user_inputs.get('tert_package_items')} as provided by the Requesting PSAP.
        - Use numbered lists or clear bullet points for all procedural steps.
        """
    elif section_title.startswith("Section 5.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST establish policies for financial management, reimbursement, and equipment. The policy MUST detail:
        1. **Reimbursement:** Use the mechanism: {user_inputs.get('reimbursement_mechanism')}
        2. **Per Diem/Expenses:** Detail the use of the daily limit of {user_inputs.get('daily_expense_limit')} and the required expense documentation.
        3. **Equipment Provisioning:** Clarify who provides equipment based on: {user_inputs.get('equipment_provision')}. Use subheadings for clarity.
        """
    elif section_title.startswith("Section 6.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST detail all protocols for TERT member safety, wellness, and post-mission procedures. The policy MUST include:
        1. **Safety Protocols:** Implement on-site safety using the guidance: {user_inputs.get('on_site_safety_protocol')}.
        2. **Critical Incident Stress Management (CISM):** Detail access to CISM services using the reference: {user_inputs.get('cism_policy_reference')}.
        3. **Post-Mission Review:** Make the TERT Deployment Review completion mandatory, to be completed within the following timeframe: {user_inputs.get('post_mission_review_requirement')}.
        """
    else:
        section_specific_prompt_guidance = "Provide a comprehensive policy section based on all available inputs and TERT best practices."

    # --- Compliance-Focused System Instruction (Final Assembly) ---
    system_instruction = f"""
    You are a legal policy writer and certified NJTI-TERT expert for a Public Safety Answering Point (PSAP).
    Your task is to write the complete text for the policy section titled: "{section_title}".
    The generated policy MUST be compliant with the APCO/NENA ANS 1.105.2-2015 Standard for TERT Deployment.

    **GENERAL CONSTRAINTS & CONTEXT (For all Sections):**
    - Agency Legal Name: {user_inputs.get('agency_name')}
    - Authority Having Jurisdiction (AHJ): {user_inputs.get('ahj_name')}
    - TERT Program Goal: {user_inputs.get('ter_program_goal')}
    - State Authority Reference: {user_inputs.get('state_authority_reference')}
    
    **--- SECTION-SPECIFIC GENERATION INSTRUCTIONS ---**
    {section_specific_prompt_guidance}

    **--- KEY CONSTRAINTS FOR REFERENCE (Always present for consistency) ---**
    **SECTION 3.0 HARD CONSTRAINTS (Qualifications and Training):**
    - TERT Telecommunicators MUST have successfully completed: FEMA IS-144, FEMA IS-100, and FEMA IS-700.
    - TERT Team Leaders MUST additionally complete: FEMA IS-200 and FEMA IS-800.
    - Local Background Check: {user_inputs.get('background_check')}
    - Additional Required Training: {user_inputs.get('additional_training')}
    
    **OPTIONAL CONTEXT:**
    - The following text, extracted from existing local policies or agreements, should be used for context and consistency, but NEVER override the Hard Constraints:
    ---
    {policy_context if policy_context else "No external document context provided."}
    ---
    
    The final output MUST be a formal, professional policy section written in clear Markdown format, suitable for inclusion in a TERT Policy Manual. Do not include any introductory or concluding remarks outside the policy text itself.
    """
    
    user_query = f"Generate the full text for the policy section: {section_title} using all provided context and constraints."
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_instruction)],
        temperature=0.4
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


def clear_session_state():
    """Clears all dynamic session state variables."""
    st.session_state.generated_sections = {}
    st.session_state.pdf_context = ""
    st.session_state.show_full_draft = False
    # No need to clear restored_inputs, as we are no longer using it for restoration.
    st.rerun()

# --- Placeholder for Export/Import Functions (DISABLED) ---
# The functions below were removed/disabled to restore stability:
# def load_session_state(uploaded_file):
#     ...
# def create_export_data(user_inputs: dict):
#     ...
# -----------------------------------------------------------


# --- Main Streamlit App ---

def main():
    st.set_page_config(
        page_title="NJTI-TERT Policy Generator",
        page_icon="🚨",
        layout="wide"
    )

    # --- Initialize Session State Keys ---
    if 'generated_sections' not in st.session_state:
        st.session_state.generated_sections = {}
    if 'pdf_context' not in st.session_state:
        st.session_state.pdf_context = ""
    if 'show_full_draft' not in st.session_state:
        st.session_state.show_full_draft = False
    
    # Define stable default values for all widgets
    DEFAULTS = {
        'agency_name': "City of Willow Creek 9-1-1 Emergency Communications Center",
        'ahj_name': "Willow Creek County Public Safety Commission",
        'ter_program_goal': "To provide mutual aid and staffing relief to PSAPs affected by natural disasters, planned events, or critical incidents that compromise continuity of operations.",
        'state_authority_reference': "Inter-Agency Mutual Aid Agreement (MAA-2024-001) as authorized by State Statute 48-9-904 et. seq.",
        'local_roles_to_define': "PSAP Manager; Communications Unit Leader (COML); Local CAD System (Fire); Local Radio System.",
        'background_check': "Standard Agency Fingerprint-based Check",
        'additional_training': "Annual NIMS Refresher; Local CAD System Certification (Level 1); 40 hours of on-the-job mentorship.",
        'local_request_mechanism': "PSAP Manager contacts County EMA who then contacts the State TERT Coordinator via secure channel.",
        'tert_package_items': "PSAP Floor Plan; Primary Radio Channel List; CAD System Login Protocol; Local Acronym Sheet.",
        'reimbursement_mechanism': "Deploying agency seeks reimbursement via State TERT Program/Federal EMAC upon declaration.",
        'equipment_provision': "Deploying PSAP provides personal gear (laptop, headset). Receiving PSAP ensures operational radio and CAD access.",
        'daily_expense_limit': "$75 per day",
        'cism_policy_reference': "Access provided through County Employee Assistance Program (EAP) or State CISM Team (Policy 12.3).",
        'post_mission_review_requirement': "Must be submitted within 72 hours of demobilization.",
        'on_site_safety_protocol': "Required buddy system, daily check-in/out with TERT Team Leader, and adherence to Requesting PSAP's physical security procedures."
    }

    # Helper function to get the current or default value
    def get_input_value(key):
        # This relies on the Streamlit widget reading its value from session state if it exists,
        # or falling back to the hardcoded default.
        return DEFAULTS.get(key, '') 
    
    # --- 1. Sidebar for Configuration and Session Management ---
    with st.sidebar:
        st.title("🚨 TERT Policy Config")
        st.caption("Generate compliant TERT policies using Gemini and NJTI-TERT standards.")
        st.markdown("---")

        # API Key Input
        st.subheader("1. Gemini API Key")
        api_key_input = st.text_input(
            "Enter your Gemini API Key:",
            type="password",
            help="Your key is not stored beyond this session."
        )
        st.session_state.gemini_api_key = api_key_input
        st.markdown("---")
        
        # PDF Upload Section
        st.subheader("2. Optional: Local Context Documents")
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

        # 🛑 IMPORT/EXPORT SECTION IS DISABLED HERE TO PREVENT HANGS 🛑
        
        # Clear Button
        if st.button('Clear All Session Data', help="Wipes all inputs, generated sections, and PDF context.", use_container_width=True):
            clear_session_state()


    # --- 2. Main Content Area - Input Fields ---
    st.header("Step 1: Customize Your TERT Program Inputs")
    
    # 1A. General Agency Info
    col1, col2 = st.columns(2)
    with col1:
        agency_name = st.text_input(
            "Agency Legal Name (Requesting/Host PSAP):",
            value=get_input_value('agency_name'),
            help="The legal name of your center.",
            key='agency_name_input'
        )
    with col2:
        ahj_name = st.text_input(
            "Authority Having Jurisdiction (AHJ) Name:",
            value=get_input_value('ahj_name'),
            help="The governing body or entity (e.g., County EMA, City Council).",
            key='ahj_name_input'
        )

    # 1B. Section 1.0 Inputs (Purpose and Authority)
    st.subheader("Section 1.0 Inputs: Purpose and Authority")
    ter_program_goal = st.text_area(
        "Primary Goal of Your TERT Program:",
        value=get_input_value('ter_program_goal'),
        help="Customize the high-level mission of your program.",
        key='ter_program_goal_input'
    )
    state_authority_reference = st.text_input(
        "State/Local Authority Reference (e.g., MOU, Statute number):",
        value=get_input_value('state_authority_reference'),
        help="Reference the legal document that authorizes TERT deployments.",
        key='state_authority_reference_input'
    )
    
    # 1C. Section 2.0 Inputs (Definitions and Acronyms)
    st.subheader("Section 2.0 Inputs: Definitions")
    local_roles_to_define = st.text_area(
        "List any key local roles or systems that need defining (e.g., 'CAD System', 'Regional Coordinator'):",
        value=get_input_value('local_roles_to_define'),
        help="Enter items separated by a semicolon or new line.",
        key='local_roles_to_define_input'
    )

    # 1D. Section 3.0 Inputs (Personnel & Training)
    st.subheader("Section 3.0 Inputs: Personnel & Training Requirements")
    st.info("The application will hardcode the mandatory FEMA IS-144, IS-100, and IS-700 requirements.")
    
    background_check_options = ["Standard Agency Fingerprint-based Check", "State-Level Background Check Only", "No Additional Requirements Beyond Initial Employment"]
    current_bg_check = get_input_value('background_check')
    background_check_index = background_check_options.index(current_bg_check) if current_bg_check in background_check_options else 0
    background_check = st.selectbox(
        "Local Background Check Requirement:",
        options=background_check_options,
        index=background_check_index,
        help="Select your PSAP's specific policy.",
        key='background_check_input'
    )
    
    additional_training = st.text_area(
        "List any additional *local* training requirements (e.g., PSAP-specific CAD/Radio certification):",
        value=get_input_value('additional_training'),
        help="Enter items separated by a semicolon or new line.",
        key='additional_training_input'
    )

    # 1E. Section 4.0 Inputs (Activation and Deployment Steps)
    st.subheader("Section 4.0 Inputs: Activation and Deployment")
    local_request_mechanism = st.text_area(
        "Local Request Mechanism:",
        value=get_input_value('local_request_mechanism'),
        help="Briefly describe the local process to initiate a request.",
        key='local_request_mechanism_input'
    )
    tert_package_items = st.text_area(
        "Essential TERT Package Items (e.g., PSAP Map, Radio Channel List, Access Codes):",
        value=get_input_value('tert_package_items'),
        help="List key documents/items the requesting agency must provide.",
        key='tert_package_items_input'
    )
    
    # 1F. Section 5.0 Inputs (Logistics and Finance)
    st.subheader("Section 5.0 Inputs: Logistics and Finance")
    reimbursement_mechanism = st.text_input(
        "Primary Reimbursement Mechanism:",
        value=get_input_value('reimbursement_mechanism'),
        help="How is the deployment funding handled (EMAC, State Budget, MOU)?",
        key='reimbursement_mechanism_input'
    )
    equipment_provision = st.text_area(
        "Equipment Provisioning Responsibility:",
        value=get_input_value('equipment_provision'),
        help="Clarify who provides equipment.",
        key='equipment_provision_input'
    )
    daily_expense_limit = st.text_input(
        "Daily Per Diem/Expense Limit:",
        value=get_input_value('daily_expense_limit'),
        help="Set the limit for unreimbursed expenses (e.g., meals, incidentals).",
        key='daily_expense_limit_input'
    )

    # 1G. Section 6.0 Inputs (Safety and Wellness)
    st.subheader("Section 6.0 Inputs: Safety, Wellness, and Review")
    cism_policy_reference = st.text_input(
        "Critical Incident Stress Management (CISM) Policy Reference:",
        value=get_input_value('cism_policy_reference'),
        help="The official resource for post-incident stress management.",
        key='cism_policy_reference_input'
    )
    
    review_options = [
        "Must be submitted within 72 hours of demobilization.",
        "Must be submitted within 7 calendar days of demobilization.",
        "Required within 30 days of the mission end."
    ]
    current_review_req = get_input_value('post_mission_review_requirement')
    review_index = review_options.index(current_review_req) if current_review_req in review_options else 0
    post_mission_review_requirement = st.selectbox(
        "Post-Mission Review Completion Requirement:",
        options=review_options,
        index=review_index,
        help="Define the mandatory timeframe for the TERT Deployment Review.",
        key='post_mission_review_requirement_input'
    )
    on_site_safety_protocol = st.text_area(
        "On-Site Safety and Security Protocols:",
        value=get_input_value('on_site_safety_protocol'),
        help="Specific safety rules for deployed members.",
        key='on_site_safety_protocol_input'
    )


    # Package all user inputs into a dictionary (Read from current Streamlit session state keys where applicable)
    user_inputs = {
        'agency_name': agency_name,
        'ahj_name': ahj_name,
        'ter_program_goal': ter_program_goal,
        'state_authority_reference': state_authority_reference,
        'local_roles_to_define': local_roles_to_define,
        'background_check': background_check,
        'additional_training': additional_training,
        'local_request_mechanism': local_request_mechanism,
        'tert_package_items': tert_package_items,
        'reimbursement_mechanism': reimbursement_mechanism,
        'equipment_provision': equipment_provision,
        'daily_expense_limit': daily_expense_limit,
        'cism_policy_reference': cism_policy_reference,
        'post_mission_review_requirement': post_mission_review_requirement,
        'on_site_safety_protocol': on_site_safety_protocol
    }

    st.markdown("---")
    # --- Step 2: Generate Policy Sections ---
    st.header("Step 2: Generate Selected Policy Section")
    
    # Dropdown to select the section
    selected_section_title = st.selectbox(
        "Choose the TERT Policy Section to Generate:",
        options=list(POLICY_SECTIONS.keys()),
        index=0,
        key='section_select_dropdown'
    )
    
    # Single generation button
    if st.button(f"Generate '{selected_section_title}'", key="generate_selected_section", use_container_width=True):
        if not st.session_state.get('gemini_api_key'):
            st.error("Please enter your Gemini API Key in the sidebar to proceed.")
        else:
            st.session_state.show_full_draft = False 
            pdf_context = st.session_state.get('pdf_context', '')
            
            generated_text = generate_policy_section(
                section_title=selected_section_title,
                user_inputs=user_inputs,
                policy_context=pdf_context,
                api_key=st.session_state.gemini_api_key,
                model=POLICY_GENERATION_MODEL
            )
            st.session_state.generated_sections[selected_section_title] = generated_text
            st.success(f"Policy section '{selected_section_title}' generated successfully!")
            st.rerun() 


    # --- 3. Main Content Area - Output Display and Actions ---
    st.markdown("---")
    st.header("Generated Policy Sections")
    
    if st.session_state.generated_sections:
        
        # Display all generated sections in collapsible expanders
        sorted_sections = sorted(st.session_state.generated_sections.keys())
        
        for title in sorted_sections:
            # Determine if this section was the one just generated to keep it expanded
            is_expanded = (title == selected_section_title)
            
            with st.expander(title, expanded=is_expanded or (title not in st.session_state.generated_sections)):
                # Use a unique key for each text area to prevent conflicts
                session_key = f"policy_edit_area_{title.replace(' ', '_').replace(':', '')}"
                
                current_text = st.session_state.generated_sections.get(title, "Policy text empty. Regenerate or paste content here.")
                
                st.session_state.generated_sections[title] = st.text_area(
                    "Review and Edit Generated Policy Text:",
                    current_text,
                    height=400,
                    key=session_key
                )
        
        # Calculate full policy text for both download and display
        full_policy_text = "\n\n---\n\n".join(
            [f"## {title}\n\n{content}" for title, content in st.session_state.generated_sections.items()]
        )
        
        # --- Final Actions: Download and Display Button ---
        st.subheader("Final Draft Actions")
        col_down, col_view = st.columns(2) # Reduced to 2 columns

        with col_down:
            st.download_button(
                label="Download Full Draft Policy (Markdown)",
                data=full_policy_text,
                file_name="draft_tert_policy.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col_view:
            if st.button("Display Full Draft Policy", use_container_width=True):
                st.session_state.show_full_draft = not st.session_state.show_full_draft
                st.rerun() 
        
        # The Export button is gone, simplifying the final actions UI.

        # Display the formatted policy preview if the state is set
        if st.session_state.show_full_draft:
            with st.expander("Formatted Policy Preview (Human Readable)", expanded=True):
                st.markdown(full_policy_text)

        
    else:
        st.info("No policy sections have been generated yet. Complete Step 1 and use the dropdown in Step 2 to generate content.")


if __name__ == "__main__":
    main()
