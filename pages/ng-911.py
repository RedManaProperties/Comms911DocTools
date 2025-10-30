import os
import streamlit as st
import json
import base64
from PyPDF2 import PdfReader
from google import genai
from google.genai import types
from io import BytesIO

# Set the default model for policy generation
POLICY_GENERATION_MODEL = "gemini-2.5-flash"

# --- MODIFIED: Define all available NG9-1-1 policy sections for the dropdown ---
POLICY_SECTIONS = {
    "Section 1.0: Purpose, Scope, and Authority (NG9-1-1)": "Purpose, Scope, and Authority",
    "Section 2.0: NG9-1-1 Terminology and Acronyms": "Definitions and Acronyms",
    "Section 3.0: Multimedia and Non-Voice Call Handling Protocols": "Multimedia and Text/Media Handling",
    "Section 4.0: Geospatial Data and Location Management": "GIS and Location Management",
    "Section 5.0: Data Retention, Logging, and Interoperability": "Data and Records",
    "Section 6.0: Cybersecurity, Resilience, and ESInet Monitoring": "Security and Resilience",
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
    Generates an NG9-1-1 policy section using Gemini, based on NENA/APCO best practices.
    """
    if not api_key:
        return "Error: Gemini API Key is missing. Please enter it in the sidebar."

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Error: Failed to initialize Gemini client: {e}"

    # --- Section-Specific Prompt Guidance (Ensures correct format/content) ---
    section_specific_prompt_guidance = ""

    # --- MODIFIED: NG9-1-1 PROMPT LOGIC ---
    if section_title.startswith("Section 1.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST define the program's Purpose (using the NG9-1-1 Program Goal input), Scope (clearly defining the transition from E9-1-1 to the ESInet system), and Authority (referencing the State Authority Reference input). Use standard policy language and separate the three components clearly with subheadings. The scope must emphasize support for {user_inputs.get('future_media_support')}.
        """
    elif section_title.startswith("Section 2.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST define all standard NG9-1-1 terms (e.g., NG9-1-1, ESInet, PSAP, ECRF, ESRP, GIS) based on the NENA i3 standard. Additionally, you MUST include definitions for the following local roles/systems provided by the user: {user_inputs.get('local_roles_to_define')}. Format the output as a clean, alphabetical Markdown definition list (e.g., **TERM**: Definition.).
        """
    elif section_title.startswith("Section 3.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST detail the operational protocols for handling non-voice communications. The policy MUST include:
        1. **Text-to-911 Protocol:** Detail the handling and transfer protocol based on the following: {user_inputs.get('text_handling_protocol')}.
        2. **Multimedia Policy:** Define rules for receiving and storing user-provided photos and videos, based on the following: {user_inputs.get('multimedia_policy_guidance')}.
        3. **Real-Time Text (RTT):** Mandate compliance with RTT standards for accessibility.
        """
    elif section_title.startswith("Section 4.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST provide detailed policies for location data management. Structure the content into three logical subsections: **I. GIS Data Maintenance**, **II. Location Discrepancy Protocol**, and **III. Geodetic Routing Requirements**.
        - GIS Data Maintenance MUST detail the update frequency: {user_inputs.get('gis_maintenance_frequency')}.
        - Location Discrepancy Protocol MUST define the required actions when caller location data and reported location conflict, based on: {user_inputs.get('location_discrepancy_protocol')}.
        - Policy MUST state that location is determined by **geospatial routing** via the ECRF/ESRP.
        """
    elif section_title.startswith("Section 5.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST establish policies for data retention, access, and sharing. The policy MUST detail:
        1. **Records Retention:** Use the time period: {user_inputs.get('retention_period_policy')} and specify it covers all media types.
        2. **Interoperability:** Define the mandatory data elements (e.g., ANI/ALI, event notes, media links) that must be transferred along with a call to another PSAP via the ESInet.
        3. **Access and Redaction:** Detail the procedures for public records requests and the required redaction protocol for sensitive multimedia based on: {user_inputs.get('redaction_protocol')}. Use subheadings for clarity.
        """
    elif section_title.startswith("Section 6.0"):
        section_specific_prompt_guidance = f"""
        For this section, you MUST detail all protocols for NG9-1-1 system security and resilience. The policy MUST include:
        1. **Cybersecurity Measures:** Detail mandatory security practices based on the following guidance: {user_inputs.get('cybersecurity_protocol')}.
        2. **Contingency Plan (COOP):** Detail the backup and failover process using the guidance: {user_inputs.get('failover_plan_reference')}.
        3. **System Monitoring:** Make monitoring of the ESInet and Core Services mandatory, with all discrepancies reported to the responsible entity: {user_inputs.get('monitoring_entity')}.
        """
    else:
        section_specific_prompt_guidance = "Provide a comprehensive policy section based on all available inputs and NG9-1-1 best practices."

    # --- Compliance-Focused System Instruction (Final Assembly) ---
    system_instruction = f"""
    You are a legal policy writer and certified **NG9-1-1 Policy Expert** for a Public Safety Answering Point (PSAP).
    Your task is to write the complete text for the policy section titled: "{section_title}".
    The generated policy MUST be compliant with the **NENA i3 Standard** and APCO/NENA NG9-1-1 best practices.

    **GENERAL CONSTRAINTS & CONTEXT (For all Sections):**
    - Agency Legal Name: {user_inputs.get('agency_name')}
    - Authority Having Jurisdiction (AHJ): {user_inputs.get('ahj_name')}
    - NG9-1-1 Program Goal: {user_inputs.get('ng911_program_goal')}
    - State Authority Reference: {user_inputs.get('state_authority_reference')}
    
    **--- SECTION-SPECIFIC GENERATION INSTRUCTIONS ---**
    {section_specific_prompt_guidance}

    **--- KEY CONSTRAINTS FOR REFERENCE (Always present for consistency) ---**
    The policy must reflect the transition to a geospatial routing model and the use of the Emergency Services IP Network (ESInet).

    **OPTIONAL CONTEXT:**
    - The following text, extracted from existing local policies or agreements, should be used for context and consistency, but NEVER override the NENA i3 standards:
    ---
    {policy_context if policy_context else "No external document context provided."}
    ---
    
    The final output MUST be a formal, professional policy section written in clear Markdown format, suitable for inclusion in an NG9-1-1 Policy Manual. Do not include any introductory or concluding remarks outside the policy text itself.
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
    if 'generated_sections' in st.session_state:
        st.session_state.generated_sections = {}
    if 'pdf_context' in st.session_state:
        st.session_state.pdf_context = ""
    if 'show_full_draft' in st.session_state:
        st.session_state.show_full_draft = False
    st.rerun()


# --- Main Streamlit App ---

def main():
    st.set_page_config(
        page_title="NG9-1-1 Policy Generator",
        page_icon="📡", # Changed icon
        layout="wide"
    )

    # --- Initialize Session State Keys ---
    if 'generated_sections' not in st.session_state:
        st.session_state.generated_sections = {}
    if 'pdf_context' not in st.session_state:
        st.session_state.pdf_context = ""
    if 'show_full_draft' not in st.session_state:
        st.session_state.show_full_draft = False
    
    # --- MODIFIED: Define stable default values for all NG9-1-1 widgets ---
    DEFAULTS = {
        'agency_name': "City of Willow Creek 9-1-1 Emergency Communications Center",
        'ahj_name': "Willow Creek County Public Safety Commission",
        'ng911_program_goal': "To fully transition the PSAP to the State ESInet to support all forms of digital communication, enhance system resilience, and improve emergency data sharing.",
        'state_authority_reference': "State 9-1-1 Act, Title 5, Chapter 32 (NG9-1-1 Funding and Governance)",
        'local_roles_to_define': "ESInet Manager; GIS Data Steward; Cybersecurity Liaison; NENA i3 Compliance Officer.",
        'future_media_support': "Text, Photos, Video, and real-time sensor data.",
        
        # Section 3.0 Inputs
        'text_handling_protocol': "Text-to-911 is primary for deaf/hard of hearing or situations where voice is unsafe. Protocols must prioritize RTT over SMS.",
        'multimedia_policy_guidance': "Telecommunicator must request media for verification only, and a supervisor must approve storage/sharing outside the CAD/logging system.",
        
        # Section 4.0 Inputs
        'gis_maintenance_frequency': "Monthly update of all road centerlines and annual revalidation of all Emergency Service Boundaries (ESBs).",
        'location_discrepancy_protocol': "If caller location (GIS) and reported location conflict, the Telecommunicator must attempt to confirm the caller's stated location while simultaneously validating the geospatial data.",
        
        # Section 5.0 Inputs
        'retention_period_policy': "Ten (10) years for all voice, text, CAD, and multimedia data.",
        'redaction_protocol': "All multimedia (photos/video) must be fully redacted to remove PII prior to release for public records requests.",
        
        # Section 6.0 Inputs
        'cybersecurity_protocol': "Mandatory use of multi-factor authentication, annual security training, and compliance with the NENA NG-SEC Standard.",
        'failover_plan_reference': "Referenced in COOP Policy 15.1, requiring immediate failover to the geodiverse alternate PSAP upon ESInet failure detection.",
        'monitoring_entity': "State 9-1-1 Office/System Administrator (SA) is the primary entity for ESInet monitoring and discrepancy reporting.",
    }

    # Helper function to get the current or default value
    def get_input_value(key):
        return DEFAULTS.get(key, '')
        
    # --- 1. Sidebar for Configuration and Session Management ---
    with st.sidebar:
        st.title("📡 NG9-1-1 Policy Config")
        st.caption("Generate NENA i3-compliant NG9-1-1 policies using Gemini.")
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
            "Upload your existing local PSAP policies or agreements (PDFs).",
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

        # Clear Button
        if st.button('Clear All Session Data', help="Wipes all inputs, generated sections, and PDF context.", use_container_width=True):
            clear_session_state()


    # --- 2. Main Content Area - Input Fields ---
    st.header("Step 1: Customize Your NG9-1-1 Program Inputs")
    
    # 1A. General Agency Info
    col1, col2 = st.columns(2)
    with col1:
        agency_name = st.text_input(
            "Agency Legal Name:",
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
    ng911_program_goal = st.text_area(
        "Primary Goal of Your NG9-1-1 Program:",
        value=get_input_value('ng911_program_goal'),
        help="Customize the high-level mission of your transition to NG9-1-1.",
        key='ng911_program_goal_input'
    )
    state_authority_reference = st.text_input(
        "State/Local Authority Reference (e.g., State 9-1-1 Act, Statute number):",
        value=get_input_value('state_authority_reference'),
        help="Reference the legal document that authorizes the NG9-1-1 transition.",
        key='state_authority_reference_input'
    )
    future_media_support = st.text_area(
        "Expected Future Media Support:",
        value=get_input_value('future_media_support'),
        help="What new data types will the PSAP be prepared for (e.g., Text, Photos, Video, Sensor Data)?",
        key='future_media_support_input'
    )
    
    # 1C. Section 2.0 Inputs (Definitions and Acronyms)
    st.subheader("Section 2.0 Inputs: Definitions")
    local_roles_to_define = st.text_area(
        "List any key local roles or systems specific to NG9-1-1 that need defining (e.g., 'GIS Data Steward', 'ESInet Manager'):",
        value=get_input_value('local_roles_to_define'),
        help="Enter items separated by a semicolon or new line.",
        key='local_roles_to_define_input'
    )

    # 1D. Section 3.0 Inputs (Multimedia & Non-Voice)
    st.subheader("Section 3.0 Inputs: Multimedia and Non-Voice Call Handling")
    text_handling_protocol = st.text_area(
        "Text-to-911 (SMS/RTT) Handling Protocol:",
        value=get_input_value('text_handling_protocol'),
        help="Describe the mandatory use case and priority (e.g., RTT over SMS).",
        key='text_handling_protocol_input'
    )
    multimedia_policy_guidance = st.text_area(
        "Multimedia (Photo/Video) Policy Guidance:",
        value=get_input_value('multimedia_policy_guidance'),
        help="Define rules for receiving, viewing, and supervisor approval for user-submitted media.",
        key='multimedia_policy_guidance_input'
    )

    # 1E. Section 4.0 Inputs (GIS and Location Management)
    st.subheader("Section 4.0 Inputs: Geospatial Data and Location Management")
    gis_maintenance_frequency = st.text_input(
        "GIS Data Maintenance Frequency:",
        value=get_input_value('gis_maintenance_frequency'),
        help="Mandatory update schedule for call routing data (e.g., 'Monthly update of road centerlines').",
        key='gis_maintenance_frequency_input'
    )
    location_discrepancy_protocol = st.text_area(
        "Location Discrepancy Protocol:",
        value=get_input_value('location_discrepancy_protocol'),
        help="Action taken when GIS-routed location conflicts with the caller's reported location.",
        key='location_discrepancy_protocol_input'
    )
    
    # 1F. Section 5.0 Inputs (Data Retention and Sharing)
    st.subheader("Section 5.0 Inputs: Data Retention, Logging, and Sharing")
    retention_period_policy = st.text_input(
        "Mandatory Records Retention Period:",
        value=get_input_value('retention_period_policy'),
        help="The legal requirement for keeping all records (voice, text, media).",
        key='retention_period_policy_input'
    )
    redaction_protocol = st.text_area(
        "Public Records/Redaction Protocol:",
        value=get_input_value('redaction_protocol'),
        help="How is sensitive data (PII, graphic media) handled before records release?",
        key='redaction_protocol_input'
    )

    # 1G. Section 6.0 Inputs (Cybersecurity and Resilience)
    st.subheader("Section 6.0 Inputs: Cybersecurity and Resilience")
    cybersecurity_protocol = st.text_area(
        "Cybersecurity Policy Requirements:",
        value=get_input_value('cybersecurity_protocol'),
        help="List mandatory security measures (e.g., MFA, NENA NG-SEC compliance).",
        key='cybersecurity_protocol_input'
    )
    failover_plan_reference = st.text_area(
        "COOP/Failover Plan Reference:",
        value=get_input_value('failover_plan_reference'),
        help="The official reference for the system backup and failover process.",
        key='failover_plan_reference_input'
    )
    monitoring_entity = st.text_input(
        "ESInet Monitoring and Discrepancy Reporting Entity:",
        value=get_input_value('monitoring_entity'),
        help="Who is responsible for 24/7 ESInet performance and security monitoring?",
        key='monitoring_entity_input'
    )


    # Package all user inputs into a dictionary (Read from current Streamlit session state keys where applicable)
    user_inputs = {
        'agency_name': agency_name,
        'ahj_name': ahj_name,
        'ng911_program_goal': ng911_program_goal,
        'state_authority_reference': state_authority_reference,
        'local_roles_to_define': local_roles_to_define,
        'future_media_support': future_media_support,
        'text_handling_protocol': text_handling_protocol,
        'multimedia_policy_guidance': multimedia_policy_guidance,
        'gis_maintenance_frequency': gis_maintenance_frequency,
        'location_discrepancy_protocol': location_discrepancy_protocol,
        'retention_period_policy': retention_period_policy,
        'redaction_protocol': redaction_protocol,
        'cybersecurity_protocol': cybersecurity_protocol,
        'failover_plan_reference': failover_plan_reference,
        'monitoring_entity': monitoring_entity
    }

    st.markdown("---")
    # --- Step 2: Generate Policy Sections ---
    st.header("Step 2: Generate Selected Policy Section")
    
    # Dropdown to select the section
    selected_section_title = st.selectbox(
        "Choose the NG9-1-1 Policy Section to Generate:",
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
                
                # Allow user to edit and save changes to the session state
                edited_text = st.text_area(
                    "Review and Edit Generated Policy Text:",
                    current_text,
                    height=400,
                    key=session_key
                )
                # Important: Update the session state with the potentially edited text
                st.session_state.generated_sections[title] = edited_text
        
        # Calculate full policy text for both download and display
        full_policy_text = "\n\n---\n\n".join(
            [f"## {title}\n\n{content}" for title, content in st.session_state.generated_sections.items()]
        )
        
        # --- Final Actions: Download and Display Button ---
        st.subheader("Final Draft Actions")
        col_down, col_view = st.columns(2) 

        with col_down:
            st.download_button(
                label="Download Full Draft Policy (Markdown)",
                data=full_policy_text,
                file_name="draft_ng911_policy.md", # Changed file name
                mime="text/markdown",
                use_container_width=True
            )
        
        with col_view:
            if st.button("Display Full Draft Policy", use_container_width=True):
                st.session_state.show_full_draft = not st.session_state.show_full_draft
                st.rerun() 
        
        # Display the formatted policy preview if the state is set
        if st.session_state.show_full_draft:
            with st.expander("Formatted Policy Preview (Human Readable)", expanded=True):
                st.markdown(full_policy_text)

        
    else:
        st.info("No policy sections have been generated yet. Complete Step 1 and use the dropdown in Step 2 to generate content.")


if __name__ == "__main__":
    main()
