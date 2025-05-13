import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import io

st.title("ClinicalTrials.gov Date Extraction Tool")
st.write("Enter one or more ClinicalTrials.gov NCT IDs to extract the study start, primary completion, and study completion dates (estimated vs actual).")

# Input field for multiple NCT IDs (one per line)
nct_input = st.text_area("NCT ID list (one per line)", height=150, placeholder="e.g.\nNCT01234567\nNCT00876543")

# Function to parse a date string from the HTML (e.g., "September 2009" or "January 15, 2020")
def parse_date_text(date_text: str) -> str:
    """Convert a date text from the site (e.g., 'September 2009' or 'Jan 15, 2020') into YYYY-MM-DD format if possible."""
    date_text = date_text.strip()
    if not date_text:
        return ""
    # Try to parse with pandas to cover various formats
    try:
        # pandas to_datetime can parse partial dates; dayfirst=False by default (Month Day, Year format)
        parsed = pd.to_datetime(date_text, errors='coerce')
        if pd.isna(parsed):
            return date_text  # if parsing failed, return original text
        # Format to YYYY-MM-DD (pandas will put 01 for day if only month-year given)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return date_text

# Only proceed when the user clicks the button
if st.button("Extract Dates"):
    # Split input by newlines and commas, filter out any empty strings
    raw_ids = re.split(r"[\s,;]+", nct_input.strip())
    nct_ids = [id.strip() for id in raw_ids if id.strip()]
    if not nct_ids:
        st.error("Please enter at least one NCT ID.")
    else:
        results = []  # list to collect results for each trial
        for nct_id in nct_ids:
            # Initialize fields with default empty or "N/A"
            start_est = primary_comp_est = comp_est = ""
            start_act = primary_comp_act = comp_act = ""
            start_act_type = primary_comp_act_type = comp_act_type = None

            # 1. Fetch first version of the study record
            hist_url = f"https://clinicaltrials.gov/ct2/history/{nct_id}?V_1"
            try:
                resp = requests.get(hist_url, timeout=10)
            except Exception as e:
                resp = None
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # The study status info is often in a table cell within an element with id 'StudyStatusBody'
                status_section = soup.find(id='StudyStatusBody')
                if status_section:
                    status_text = status_section.get_text(separator=" ").strip()
                    # Extract Study Start (initial)
                    match = re.search(r"Study Start\s*Date?:\s*([A-Za-z0-9, ]+)", status_text)
                    if match:
                        raw_date = match.group(1).strip()
                        # Remove any bracket like [Actual] or [Anticipated] if present, for initial we assume anticipated if not labeled
                        raw_date = re.sub(r"\[.*?\]", "", raw_date).strip()
                        start_est = parse_date_text(raw_date)
                    # Extract Primary Completion (initial)
                    match = re.search(r"Primary Completion\s*Date?:\s*([A-Za-z0-9, \[\]]+)", status_text)
                    if match:
                        raw_text = match.group(1).strip()
                        # Check for label in brackets (Anticipated/Actual)
                        type_match = re.search(r"\[([\w\s]+)\]", raw_text)
                        if type_match:
                            # We don't actually need to store the 'estimated' label for the first version, but we note its presence
                            # Removing the bracketed part to get the date
                            raw_date = re.sub(r"\s*\[.*?\]", "", raw_text).strip()
                        else:
                            raw_date = raw_text  # no explicit label
                        primary_comp_est = parse_date_text(raw_date)
                    # Extract Study Completion (initial)
                    match = re.search(r"Study Completion\s*Date?:\s*([A-Za-z0-9, \[\]]+)", status_text)
                    if not match:
                        # Sometimes it might be just "Completion Date" in older records
                        match = re.search(r"Completion Date\s*:\s*([A-Za-z0-9, \[\]]+)", status_text)
                    if match:
                        raw_text = match.group(1).strip()
                        type_match = re.search(r"\[([\w\s]+)\]", raw_text)
                        if type_match:
                            raw_date = re.sub(r"\s*\[.*?\]", "", raw_text).strip()
                        else:
                            raw_date = raw_text
                        comp_est = parse_date_text(raw_date)
            else:
                # Could not retrieve the first version page
                st.warning(f"Could not retrieve initial version for {nct_id}.")
            
            # 2. Fetch latest version data via API
            api_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?fields=study.protocolSection.statusModule"
            try:
                resp2 = requests.get(api_url, timeout=10)
            except Exception as e:
                resp2 = None
            if resp2 and resp2.status_code == 200:
                data = resp2.json()
                # The API returns a dictionary; the 'studies' key might contain a list of one study
                # Check if data is nested under 'studies'
                if 'studies' in data:
                    studies = data['studies']
                    study_data = studies[0] if studies else {}
                else:
                    # In case the API returns a single study object directly
                    study_data = data.get('study', data)
                status_mod = {}
                if study_data:
                    status_mod = study_data.get('protocolSection', {}).get('statusModule', {})
                # Extract current dates and their types
                if status_mod.get('startDateStruct'):
                    start_act = status_mod['startDateStruct'].get('date', "")
                    start_act_type = status_mod['startDateStruct'].get('type', "")
                if status_mod.get('primaryCompletionDateStruct'):
                    primary_comp_act = status_mod['primaryCompletionDateStruct'].get('date', "")
                    primary_comp_act_type = status_mod['primaryCompletionDateStruct'].get('type', "")
                if status_mod.get('completionDateStruct'):
                    comp_act = status_mod['completionDateStruct'].get('date', "")
                    comp_act_type = status_mod['completionDateStruct'].get('type', "")
            else:
                st.warning(f"Could not retrieve current data via API for {nct_id}.")
            
            # Interpret the types for actual vs estimated in the latest data:
            # We'll only treat the date as "Actual" if the type indicates actual.
            # If the latest type is still anticipated/estimated, we'll output N/A in the Actual column (since actual date not confirmed yet).
            if start_act_type and start_act_type.lower() != "actual":
                start_act = ""  # not an actual date yet
            if primary_comp_act_type and primary_comp_act_type.lower() != "actual":
                primary_comp_act = ""  # still anticipated, so no actual date
            if comp_act_type and comp_act_type.lower() != "actual":
                comp_act = ""

            # Use "N/A" or empty string for any missing values for clarity
            if not start_est: start_est = "N/A"
            if not primary_comp_est: primary_comp_est = "N/A"
            if not comp_est: comp_est = "N/A"
            if not start_act: start_act = "N/A"
            if not primary_comp_act: primary_comp_act = "N/A"
            if not comp_act: comp_act = "N/A"

            results.append({
                "NCT ID": nct_id,
                "Start Date (Estimated)": start_est,
                "Primary Completion (Estimated)": primary_comp_est,
                "Study Completion (Estimated)": comp_est,
                "Start Date (Actual)": start_act,
                "Primary Completion (Actual)": primary_comp_act,
                "Study Completion (Actual)": comp_act
            })
        
        # Create DataFrame and display results
        df = pd.DataFrame(results)
        st.write("### Extraction Results")
        st.dataframe(df)

        # Prepare Excel download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        st.download_button(
            label="💾 Download Excel",
            data=excel_data,
            file_name="ClinicalTrials_Dates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )