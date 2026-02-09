import gspread
import requests
from bs4 import BeautifulSoup
from flask import Flask
from google.oauth2.service_account import Credentials

import progress_calculator as pc


def get_gcsb_profile_details(public_profile_url):
    if not public_profile_url.startswith("https://www.skills.google/public_profiles/"):
        raise ValueError(
            "Please enter a valid public Google Cloud Skills Boost profile URL."
        )

    response = requests.get(public_profile_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch profile. HTTP {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    name_tag = soup.find("h1")
    name = name_tag.text.strip() if name_tag else "Unknown"

    badges = []
    for badge in soup.find_all("div", class_="profile-badge"):
        title = badge.find("span")
        badges.append(title.text.strip() if title else "Unknown Badge")

    completed, arcade_game, progress, percent = pc.progress(badges)

    return {
        "name": name,
        "skill_badges": completed,
        "arcade_game": arcade_game,
        "progress": progress,
        "percent": percent,
    }


# =============== WRITE TO GOOGLE SHEETS ===============
def write_to_google_sheet(sheet_name, data):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1

    # Create header row if sheet is empty
    if not sheet.get_all_values():
        sheet.append_row(
            [
                "Name",
                "No. of Skill Badges Completed",
                "No. of Arcade Games Completed",
                "Progress %",
                "Completion Status",
            ]
        )

    # Get all current data in sheet
    records = sheet.get_all_records()
    names = [record["Name"] for record in records]

    # Check if name already exists
    if data["name"] in names:
        # +2 because sheet rows are 1-indexed and we have a header row
        row_index = names.index(data["name"]) + 2
        sheet.update(
            f"A{row_index}:E{row_index}",
            [
                [
                    data["name"],
                    data["skill_badges"],
                    data["arcade_game"],
                    data["progress"],
                    data["percent"],
                ]
            ],
        )
        print(f"🔄 Updated existing entry for {data['name']}.")
    else:
        sheet.append_row(
            [
                data["name"],
                data["skill_badges"],
                data["arcade_game"],
                data["progress"],
                data["percent"],
            ]
        )
        print(f"✅ Added new entry for {data['name']}.")


app = Flask(__name__)


@app.route("/")
def home():
    with open("updated_entries.csv", encoding="utf-8-sig") as csv_file:
        for url in csv_file:
            profile_url = url.strip()
            print(profile_url)
            profile_data = get_gcsb_profile_details(profile_url)
            print(profile_data)
            write_to_google_sheet("GCSJ Tracker", profile_data)
    return "Updating data"


# =============== MAIN ===============
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
