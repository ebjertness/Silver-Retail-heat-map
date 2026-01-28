import pandas as pd
import requests
from io import StringIO
from datetime import datetime

COT_URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"

def fetch_cot():
    # Download zip
    r = requests.get(COT_URL)
    z = zipfile.ZipFile(BytesIO(r.content))
    file_name = z.namelist()[0]

    # Read data
    df = pd.read_csv(z.open(file_name), sep=",")
    
    # Filter COMEX Silver
    silver = df[df["Market_and_Exchange_Names"].str.contains("SILVER - COMMODITY EXCHANGE INC", na=False)]
    
    # Retail proxy = Non-reportable
    silver["retail_net"] = silver["NonRept_Long_All"] - silver["NonRept_Short_All"]

    out = silver[[
        "Report_Date_as_YYYY-MM-DD",
        "retail_net",
        "Open_Interest_All"
    ]]

    out.columns = ["date", "retail_net", "open_interest"]
    out["date"] = pd.to_datetime(out["date"])

    out.to_csv("cot_data.csv", index=False)

if __name__ == "__main__":
    fetch_cot()
