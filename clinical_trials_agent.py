import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

API_URL = "https://clinicaltrials.gov/api/v2/studies"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def search_clinical_trials(query, location=None, max_results=10):
    params = {"query.term": query, "pageSize": max_results}
    if location:
        params["query.location"] = location
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json().get("studies", [])
    return []

def get_dates_from_study_page(nct_id):
    url = f"https://clinicaltrials.gov/study/{nct_id}"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "lxml")

    fields = {
        "Study Start": ("Study Start (Estimated)", "Study Start (Actual)"),
        "Primary Completion": ("Primary Completion (Estimated)", "Primary Completion (Actual)"),
        "Study Completion": ("Study Completion (Estimated)", "Study Completion (Actual)")
    }

    results = {
        "Study Start (Estimated)": "-",
        "Study Start (Actual)": "-",
        "Primary Completion (Estimated)": "-",
        "Primary Completion (Actual)": "-",
        "Study Completion (Estimated)": "-",
        "Study Completion (Actual)": "-"
    }

    rows = soup.find_all("dt")
    for dt in rows:
        label = dt.text.strip()
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        text = dd.text.strip()
        for key, (est_key, act_key) in fields.items():
            if label.startswith(key):
                if "actual" in text.lower():
                    results[act_key] = text
                elif "estimated" in text.lower():
                    results[est_key] = text
                else:
                    # if no label, treat as estimated
                    results[est_key] = text
    return results

# --- Streamlit UI ---
st.title("ClinicalTrials.gov Study Exporter (Stable Date Scraper)")

condition = st.text_input("Condition/Disease (Required):")
location = st.text_input("Location (Optional):")

export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

max_results = 10 if export_option == "Sample (10 results)" else 1000

if st.button("Search and Export to Excel") and condition.strip():
    with st.spinner("Fetching clinical trial data..."):
        results = search_clinical_trials(condition, location, max_results)

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

            # Scrape study detail page for dates
            dates = get_dates_from_study_page(nct_id)

            # Contacts
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
            location_details = []
            for facility in facilities:
                name = facility.get("name", "-")
                country = facility.get("location", {}).get("country", "-")
                location_details.append(f"{name} ({country})")
            location_summary = " | ".join(location_details) if location_details else "-"

            data.append({
                "NCT ID": nct_id,
                "Study Type": study_type,
                "Title": title,
                "Sponsor": sponsor,
                "Phase": phase,
                "Status": status,
                "Study Start (Estimated)": dates["Study Start (Estimated)"],
                "Study Start (Actual)": dates["Study Start (Actual)"],
                "Primary Completion (Estimated)": dates["Primary Completion (Estimated)"],
                "Primary Completion (Actual)": dates["Primary Completion (Actual)"],
                "Study Completion (Estimated)": dates["Study Completion (Estimated)"],
                "Study Completion (Actual)": dates["Study Completion (Actual)"],
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
        st.warning("No results found.")
else:
    st.info("Please enter a condition/disease to begin search.")