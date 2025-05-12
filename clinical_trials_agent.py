import streamlit as st
import requests
import pandas as pd
from io import BytesIO

API_URL = "https://clinicaltrials.gov/api/v2/studies"

def search_clinical_trials(query, location=None, max_results=10):
    params = {"query.term": query, "pageSize": max_results}
    if location:
        params["query.location"] = location
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json().get("studies", [])
    else:
        return []

st.title("ClinicalTrials.gov Study Exporter")

# Mandatory Condition/Disease Field
condition = st.text_input("Condition/Disease (Required):")

# Optional Location Field
location = st.text_input("Location (Optional):")

# Choice to limit or get all results
export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

# Map option to number of results
max_results = 10 if export_option == "Sample (10 results)" else 1000

if st.button("Search and Export to Excel") and condition.strip() != "":
    with st.spinner("Searching ClinicalTrials.gov..."):
        results = search_clinical_trials(condition, location, max_results=max_results)

    if results:
        # Prepare data for export
        data = []
        for study in results:
    protocol = study.get("protocolSection", {})
    id_module = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
    design_module = protocol.get("designModule", {})
    contact_module = protocol.get("contactsLocationsModule", {})

    nct_id = id_module.get("nctId", "N/A")
    title = id_module.get("briefTitle", "N/A")
    study_type = design_module.get("studyType", "N/A")
    sponsor = sponsor_module.get("leadSponsor", {}).get("name", "N/A")
    phase = design_module.get("phaseList", {}).get("phases", ["N/A"])[0]
    status = status_module.get("overallStatus", "N/A")

    # Dates (try structured first, then fallback to posted date text)
    def get_date(struct):
        return struct.get("actual", struct.get("estimated", "-")) if struct else "-"

    start_date = get_date(status_module.get("startDateStruct", {}))
    completion_date = get_date(status_module.get("completionDateStruct", {}))
    primary_completion_date = get_date(status_module.get("primaryCompletionDateStruct", {}))

    # Contact Information - fetch all contacts if available
    contacts = contact_module.get("centralContactList", {}).get("centralContacts", [])
    contact_details = []
    for contact in contacts:
        name = contact.get("name", "-")
        phone = contact.get("phone", "-")
        email = contact.get("email", "-")
        contact_details.append(f"Name: {name}, Phone: {phone}, Email: {email}")
    contact_summary = " | ".join(contact_details) if contact_details else "-"

    # Append data
    data.append({
        "NCT ID": nct_id,
        "Study Type": study_type,
        "Title": title,
        "Sponsor": sponsor,
        "Phase": phase,
        "Status": status,
        "Study Start": start_date,
        "Study Completion": completion_date,
        "Primary Completion": primary_completion_date,
        "Contacts": contact_summary
    })

        df = pd.DataFrame(data)

        # Prepare Excel file for download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Clinical Trials")
        st.download_button(
            label="Download Results as Excel",
            data=output.getvalue(),
            file_name="clinical_trials_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No studies found. Please try a different term.")
else:
    st.info("Please enter a condition/disease to begin search.")

