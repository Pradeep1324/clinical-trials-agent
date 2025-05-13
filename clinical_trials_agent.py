import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from xml.etree import ElementTree as ET

API_URL = "https://clinicaltrials.gov/api/v2/studies"
XML_BASE_URL = "https://clinicaltrials.gov/ct2/show"

def search_clinical_trials(query, location=None, max_results=10):
    params = {"query.term": query, "pageSize": max_results}
    if location:
        params["query.location"] = location
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json().get("studies", [])
    return []

def extract_dates_and_phase_from_xml(nct_id):
    url = f"{XML_BASE_URL}/{nct_id}?displayxml=true"
    response = requests.get(url)
    results = {
        "Phase": "-",
        "Study Start (Estimated)": "-",
        "Study Start (Actual)": "-",
        "Primary Completion (Estimated)": "-",
        "Primary Completion (Actual)": "-",
        "Study Completion (Estimated)": "-",
        "Study Completion (Actual)": "-"
    }

    if response.status_code != 200:
        return results

    try:
        root = ET.fromstring(response.content)

        # Phase
        phase_elem = root.find("phase")
        if phase_elem is not None:
            results["Phase"] = phase_elem.text.strip()

        # Date logic
        def extract_date(tag, label):
            elems = root.findall(tag)
            for el in elems:
                type_ = el.attrib.get("type", "").lower()
                value = el.text.strip()
                if "actual" in type_:
                    results[f"{label} (Actual)"] = value
                elif "estimated" in type_:
                    results[f"{label} (Estimated)"] = value
                else:
                    # fallback if no type
                    results[f"{label} (Estimated)"] = value

        extract_date("start_date", "Study Start")
        extract_date("primary_completion_date", "Primary Completion")
        extract_date("completion_date", "Study Completion")

    except Exception as e:
        print(f"XML parsing error for {nct_id}: {e}")

    return results

# --- Streamlit UI ---
st.title("ClinicalTrials.gov Exporter (Reliable XML Version)")

condition = st.text_input("Condition/Disease (Required):")
location = st.text_input("Location (Optional):")

export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

max_results = 10 if export_option == "Sample (10 results)" else 1000

if st.button("Search and Export to Excel") and condition.strip():
    with st.spinner("Fetching data..."):
        results = search_clinical_trials(condition, location, max_results)

    if results:
        data = []

        for study in results:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            contact_module = protocol.get("contactsLocationsModule", {})

            nct_id = id_module.get("nctId", "N/A")
            title = id_module.get("briefTitle", "N/A")
            study_type = design_module.get("studyType", "N/A")
            sponsor = sponsor_module.get("leadSponsor", {}).get("name", "N/A")
            status = protocol.get("statusModule", {}).get("overallStatus", "N/A")

            # Extract date & phase from XML
            xml_data = extract_dates_and_phase_from_xml(nct_id)

            # Contact Info
            contacts = contact_module.get("centralContactList", {}).get("centralContacts", [])
            contact_details = []
            for contact in contacts:
                name = contact.get("name", "-")
                phone = contact.get("phone", "-")
                email = contact.get("email", "-")
                contact_details.append(f"{name}, {phone}, {email}")
            contact_summary = " | ".join(contact_details) if contact_details else "-"

            # Locations
            facilities = contact_module.get("facilityList", {}).get("facilities", [])
            locations = []
            for facility in facilities:
                name = facility.get("name", "-")
                country = facility.get("location", {}).get("country", "-")
                locations.append(f"{name} ({country})")
            location_summary = " | ".join(locations) if locations else "-"

            data.append({
                "NCT ID": nct_id,
                "Study Type": study_type,
                "Title": title,
                "Sponsor": sponsor,
                "Phase": xml_data["Phase"],
                "Status": status,
                "Study Start (Estimated)": xml_data["Study Start (Estimated)"],
                "Study Start (Actual)": xml_data["Study Start (Actual)"],
                "Primary Completion (Estimated)": xml_data["Primary Completion (Estimated)"],
                "Primary Completion (Actual)": xml_data["Primary Completion (Actual)"],
                "Study Completion (Estimated)": xml_data["Study Completion (Estimated)"],
                "Study Completion (Actual)": xml_data["Study Completion (Actual)"],
                "Contacts": contact_summary,
                "Locations": location_summary
            })

        df = pd.DataFrame(data)

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
