import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from io import BytesIO

st.title("ClinicalTrials.gov Date Extractor")
st.write("Enter a condition or disease to extract study start, primary completion, and study completion dates (Estimated vs Actual).")

condition = st.text_input("Condition/Disease (Required):")

export_option = st.radio(
    "Select Export Option:",
    ("Sample (10 results)", "Get Complete Data (All available)")
)

max_results = 10 if export_option == "Sample (10 results)" else 1000

# API endpoint for searching studies
SEARCH_API_URL = "https://clinicaltrials.gov/api/v2/studies"

def search_nct_ids(condition_term, max_results=10):
    params = {
        "query.term": condition_term,
        "pageSize": max_results
    }
    response = requests.get(SEARCH_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return [study.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
                for study in data.get("studies", [])]
    return []

def extract_estimated_dates_from_first_version(nct_id):
    url = f"https://clinicaltrials.gov/ct2/history/{nct_id}?V_1"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"start": "N/A", "primary": "N/A", "completion": "N/A"}
    except Exception:
        return {"start": "N/A", "primary": "N/A", "completion": "N/A"}

    soup = BeautifulSoup(resp.text, "lxml")
    full_text = soup.get_text(separator=" ").strip()

    def extract(label):
        pattern = rf"{label} Date\s*:?\s*([A-Za-z]+\s+\d{{4}}|\w+\s+\d{{1,2}},\s+\d{{4}})"
        match = re.search(pattern, full_text, re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"

    return {
        "start": extract("Study Start"),
        "primary": extract("Primary Completion"),
        "completion": extract("Study Completion") or extract("Completion")
    }

def extract_actual_dates_from_api(nct_id):
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?fields=study.protocolSection.statusModule"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"start": "N/A", "primary": "N/A", "completion": "N/A"}
    except Exception:
        return {"start": "N/A", "primary": "N/A", "completion": "N/A"}

    data = resp.json()
    study = data.get("study", {})
    status = study.get("protocolSection", {}).get("statusModule", {}) if study else {}

    def get_actual(d):
        if d and d.get("type", "").lower() == "actual":
            return d.get("date", "N/A")
        return "N/A"

    return {
        "start": get_actual(status.get("startDateStruct")),
        "primary": get_actual(status.get("primaryCompletionDateStruct")),
        "completion": get_actual(status.get("completionDateStruct"))
    }

if st.button("Search and Export") and condition.strip():
    with st.spinner("Searching studies and extracting dates..."):
        nct_ids = search_nct_ids(condition.strip(), max_results=max_results)

    if not nct_ids:
        st.warning("No studies found.")
    else:
        results = []
        for nct_id in nct_ids:
            est = extract_estimated_dates_from_first_version(nct_id)
            act = extract_actual_dates_from_api(nct_id)

            results.append({
                "NCT ID": nct_id,
                "Study Start (Estimated)": est["start"],
                "Study Start (Actual)": act["start"],
                "Primary Completion (Estimated)": est["primary"],
                "Primary Completion (Actual)": act["primary"],
                "Study Completion (Estimated)": est["completion"],
                "Study Completion (Actual)": act["completion"]
            })

        df = pd.DataFrame(results)
        st.success(f"{len(results)} studies processed.")
        st.dataframe(df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            label="📥 Download as Excel",
            data=output.getvalue(),
            file_name="clinical_trials_dates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please enter a condition or disease to begin.")
