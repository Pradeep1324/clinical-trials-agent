import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

def get_nct_ids(condition, max_studies=20):
    print("🔍 Fetching NCT IDs...")
    url = "https://clinicaltrials.gov/api/query/study_fields"
    params = {
        "expr": condition,
        "fields": "NCTId",
        "min_rnk": 1,
        "max_rnk": max_studies,
        "fmt": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return [s["NCTId"][0] for s in response.json()["StudyFieldsResponse"]["StudyFields"]]

def fetch_dates_from_xml(nct_id):
    base_url = f"https://clinicaltrials.gov/api/query/full_studies"
    params = {"expr": nct_id, "fmt": "json"}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    study_data = response.json()
    actual, estimated = {}, {}

    try:
        study = study_data['FullStudiesResponse']['FullStudies'][0]['Study']
        protocol = study.get("ProtocolSection", {})
        status = protocol.get("StatusModule", {})

        def extract_dates(source, target):
            for date_field in ["StudyStartDate", "PrimaryCompletionDate", "CompletionDate"]:
                val = source.get(date_field)
                if val:
                    text = val.get("#text", "-")
                    type_ = val.get("@Type", "Estimated")
                    if type_.lower() == "actual":
                        target[date_field] = text
                    else:
                        target[f"{date_field}_Estimated"] = text

        extract_dates(status, actual)

    except Exception as e:
        print(f"⚠️ Error parsing XML for {nct_id}: {e}")

    return {**actual, **estimated}

def fetch_estimated_from_html(nct_id):
    print(f"🌐 Scraping estimated dates for {nct_id}...")
    url = f"https://clinicaltrials.gov/study/{nct_id}/history"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    estimated = {}

    try:
        rows = soup.select("table tbody tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) >= 4 and "First posted" in cells[2]:
                break  # Stop early
            if len(cells) >= 4 and cells[3]:
                for key in ["Study Start Date", "Primary Completion Date", "Study Completion Date"]:
                    if key in cells[2] and "Estimated" in cells[3]:
                        estimated_key = key.replace(" ", "") + "_Estimated"
                        estimated[estimated_key] = cells[3].replace("Estimated", "").strip()
    except Exception as e:
        print(f"⚠️ Error scraping estimated dates for {nct_id}: {e}")

    return estimated

def fetch_all_fields(nct_id):
    print(f"📄 Processing: {nct_id}")
    url = f"https://clinicaltrials.gov/api/query/full_studies?expr={nct_id}&fmt=json"
    response = requests.get(url)
    study = response.json()['FullStudiesResponse']['FullStudies'][0]['Study']

    try:
        protocol = study['ProtocolSection']
        sponsor = protocol['IdentificationModule'].get("OrganizationName", "-")
        title = protocol['IdentificationModule'].get("BriefTitle", "-")
        study_type = protocol['DesignModule'].get("StudyType", "-")
        phase = protocol['DesignModule'].get("Phase", "-")
        status = protocol['StatusModule'].get("OverallStatus", "-")

        contact_info = protocol.get("ContactsLocationsModule", {}).get("CentralContactList", {}).get("CentralContact", {})
        contact_name = contact_info.get("Name", "-")
        contact_phone = contact_info.get("Phone", "-")
        contact_email = contact_info.get("Email", "-")

        actual_dates = fetch_dates_from_xml(nct_id)
        estimated_dates = fetch_estimated_from_html(nct_id)

        return {
            "NCT ID": nct_id,
            "Brief Title": title,
            "Sponsor": sponsor,
            "Study Type": study_type,
            "Phase": phase,
            "Status": status,
            "Study Start Date Estimated": estimated_dates.get("StudyStartDate_Estimated", "-"),
            "Study Start Date Actual": actual_dates.get("StudyStartDate", "-"),
            "Primary Completion Date Estimated": estimated_dates.get("PrimaryCompletionDate_Estimated", "-"),
            "Primary Completion Date Actual": actual_dates.get("PrimaryCompletionDate", "-"),
            "Study Completion Date Estimated": estimated_dates.get("StudyCompletionDate_Estimated", "-"),
            "Study Completion Date Actual": actual_dates.get("CompletionDate", "-"),
            "Contact Name": contact_name,
            "Contact Phone": contact_phone,
            "Contact Email": contact_email
        }

    except Exception as e:
        print(f"⚠️ Error fetching details for {nct_id}: {e}")
        return {}

def fetch_trials_by_condition(condition):
    nct_ids = get_nct_ids(condition)
    all_trials = []
    for nct in nct_ids:
        trial = fetch_all_fields(nct)
        if trial:
            all_trials.append(trial)
        time.sleep(0.5)
    return pd.DataFrame(all_trials)

if __name__ == "__main__":
    print("🚀 Script started")
    condition = input("Enter condition/disease name: ")
    df = fetch_trials_by_condition(condition)
    filename = f"clinical_trials_{condition}.xlsx"
    df.to_excel(filename, index=False)
    print(f"✅ Data saved to {filename}")
