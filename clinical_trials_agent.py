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

# Mandatory input
condition = st.text_input("Condition/Disease (Required):")

# Optional location input
location = st.text_input("Location (Optional):")

# Export option
export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

# Set result limit
max_results = 10 if export_option == "Sample (10 results)" else 1000

if st.button("Search and Export to Excel") and condition.strip() != "":
    with st.spinner("Searching ClinicalTrials.gov..."):
        results = search_clinical_trials(condition, location, max_results=max_results)

    if results:
        st.subheader("📋 Sample Study Record (Debug)")
        st.json(results[0])  # View one record structure

        data = []

        def extract_dates(struct):
            if not struct:
                return "-", "-"
            date = struct.get("date", "-")
            date_type = struct.get("type", "").upper()
            actual = date if date_type == "ACTUAL" else "-"
            estimated = date if date_type == "ESTIMATED" else "-"
            return actual, estimated

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

            start_actual, start_estimated = extract_dates(status_module.get("startDateStruct", {}))
            primary_actual, primary_estimated = extract_dates(status_module.get("primaryCompletionDateStruct", {}))
            completion_actual, completion_estimated = extract_dates(status_module.get("completionDateStruct", {}))

            # Contacts
            contacts = contact_module.get("centralContactList", {}).get("centralContacts", [])
            contact_details = []
            for contact in contacts:
                name = contact.get("name", "-")
                phone = contact.get("phone", "-")
                email = contact.get("email", "-")
                contact_details.append(f"{name}, {phone}, {email}")
            contact_summary = " | ".join(contact_details) if contact_details else "-"

            # Facilities
            facilities = contact_module.get("facilityList", {}).get("facilities", [])
            facility_details = []
            for facility in facilities:
                name = facility.get("name", "-")
                country = facility.get("location", {}).get("country", "-")
                facility_details.append(f"{name} ({country})")
            location_summary = " | ".join(facility_details) if facility_details else "-"

            data.append({
                "NCT ID": nct_id,
                "Study Type": study_type,
                "Title": title,
                "Sponsor": sponsor,
                "Phase": phase,
                "Status": status,
                "Study Start (Actual)": start_actual,
                "Study Start (Estimated)": start_estimated,
                "Primary Completion (Actual)": primary_actual,
                "Primary Completion (Estimated)": primary_estimated,
                "Study Completion (Actual)": completion_actual,
                "Study Completion (Estimated)": completion_estimated,
                "Contacts": contact_summary,
                "Locations": location_summary
            })

        df = pd.DataFrame(data)

        # Excel download
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
        st.warning("No studies found.")
else:
    st.info("Please enter a condition/disease to begin search.")