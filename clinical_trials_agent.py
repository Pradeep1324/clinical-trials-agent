st.title("ClinicalTrials.gov Study Summary Viewer")

search_term = st.text_input("Enter a condition or keyword to search for clinical trials:")

if search_term:
    with st.spinner("Searching ClinicalTrials.gov..."):
        results = search_clinical_trials(search_term, max_results=5)

    if results:
        for study in results:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            contact_module = protocol.get("contactsLocationsModule", {})

            # Extracting required fields
            nct_id = id_module.get("nctId", "N/A")
            brief_title = id_module.get("briefTitle", "N/A")
            study_type = design_module.get("studyType", "N/A")
            sponsor = sponsor_module.get("leadSponsor", {}).get("name", "N/A")
            phase = design_module.get("phaseList", {}).get("phases", ["N/A"])[0]
            status = status_module.get("overallStatus", "N/A")

            # Study Dates
            start_date_struct = status_module.get("startDateStruct", {})
            start_date_actual = start_date_struct.get("actual", "-")
            start_date_estimated = start_date_struct.get("estimated", "-")

            completion_date_struct = status_module.get("completionDateStruct", {})
            completion_date_actual = completion_date_struct.get("actual", "-")
            completion_date_estimated = completion_date_struct.get("estimated", "-")

            primary_completion_date_struct = status_module.get("primaryCompletionDateStruct", {})
            primary_completion_date_actual = primary_completion_date_struct.get("actual", "-")
            primary_completion_date_estimated = primary_completion_date_struct.get("estimated", "-")

            # Contact Information
            central_contact = contact_module.get("centralContactList", {}).get("centralContacts", [{}])[0]
            contact_name = central_contact.get("name", "-")
            contact_phone = central_contact.get("phone", "-")
            contact_email = central_contact.get("email", "-")

            # Display the information
            st.markdown(f"### {brief_title}")
            st.write(f"- **NCT ID**: {nct_id}")
            st.write(f"- **Study Type**: {study_type}")
            st.write(f"- **Sponsor**: {sponsor}")
            st.write(f"- **Phase**: {phase}")
            st.write(f"- **Status**: {status}")
            st.write(f"- **Study Start Date**: Estimated - {start_date_estimated}, Actual - {start_date_actual}")
            st.write(f"- **Study Completion Date**: Estimated - {completion_date_estimated}, Actual - {completion_date_actual}")
            st.write(f"- **Primary Completion Date**: Estimated - {primary_completion_date_estimated}, Actual - {primary_completion_date_actual}")
            st.write("#### Central Contact")
            st.write(f"- **Name**: {contact_name}")
            st.write(f"- **Phone**: {contact_phone}")
            st.write(f"- **Email**: {contact_email}")
            st.markdown("---")
    else:
        st.write("No studies found.")
