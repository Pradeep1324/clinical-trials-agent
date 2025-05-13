import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

API_URL = "https://clinicaltrials.gov/api/v2/studies"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; clinical-trial-scraper/1.0)"
}

def search_clinical_trials(query, location=None, max_results=10):
    params = {"query.term": query, "pageSize": max_results}
    if location:
        params["query.location"] = location
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json().get("studies", [])
    else:
        return []

def extract_dates_from_version(nct_id, version="1"):
    url = f"https://clinicaltrials.gov/ct2/history/{nct_id}?V_{version}"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "lxml")

    table = soup.find("table", {"id": "study-info-table"})
    dates = {"start": "-", "primary": "-", "completion": "-"}

    if table:
        rows = table.find_all("tr")
        for row in rows:
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True)
            value = td.get_text(strip=True)

            if "Study Start" in label and dates["start"] == "-":
                dates["start"] = value
            elif "Primary Completion" in label and dates["primary"] == "-":
                dates["primary"] = value
            elif "Study Completion" in label and dates["completion"] == "-":
                dates["completion"] = value

    return dates

st.title("ClinicalTrials.gov Study Exporter (with Historic Dates)")

condition = st.text_input("Condition/Disease (Required):")
location = st.text_input("Location (Optional):")

export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

max_results = 10 if export_option == "Sample (10 results)" else 1000

if st.button("Search and Export to Excel") and condition.strip() != "":
    with st.spinner("Searching ClinicalTrials.gov..."):
        results = search_clinical_trials(condition, location, max_results=max_results)

    if results:
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

            # Get Estimated from first version, Actual from latest
            estimated_dates = extract_dates_from_version(nct_id, version="1")
            actual_dates = extract_dates_from_version(nct_id, version="latest")

            # Central Contacts
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
                "Study Start (Estimated)": estimated_dates["start"],
                "Study Start (Actual)": actual_dates["start"],
                "Primary Completion (Estimated)": estimated_dates["primary"],
                "Primary Completion (Actual)": actual_dates["primary"],
                "Study Completion (Estimated)": estimated_dates["completion"],
                "Study Completion (Actual)": actual_dates["completion"],
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