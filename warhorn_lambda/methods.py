import os
from datetime import datetime
from urllib.request import Request, urlopen
# from urllib.parse
import pandas as pd
import json


def get_submissions(sheet_id):
    SHEET_ID = sheet_id
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
    df = pd.read_csv(url)
    return df

def submit_warhorn(req, query="{me{id,name}}", vars = {}):
    data = {"query" : query, "variables" : vars}
    data = json.dumps(data)
    data = data.encode()
    r = urlopen(req, data=data)
    content = json.loads(r.read().decode("utf-8"))
    content["status"]= r.getcode()
    return content

def get_event_id(req,event_str):
    content = submit_warhorn(req,warhorn_queries["event_query"],vars ={"slug":event_str})
    return content["data"]["event"]["id"]

def get_gm_role_id(req, event_str):
    content = submit_warhorn(req, warhorn_queries["event_roles"], vars = {"slug":event_str})
    for d in content["data"]["event"]["roles"]:
        if d["name"]=="GM":
            return d["id"]

def fix_date(string):
    l =string.split(", ")
    date = datetime.strptime(l[1] + " " + l[2], "%B %d %Y")
    return date.strftime("%Y-%m-%d")

def fix_start_time(string):
    time = datetime.strptime(string, "%I:%M:%S %p")
    return time.strftime("%H:%M:%S")




def main(token, sheet_id, event_str):
    
    df = get_submissions(sheet_id)
    df["slug"]= event_str

    # Updating column names to match queries and mutations submitted
    df.rename(columns=col_rename, inplace=True)

    # Dropping extra columns from google sheet
    df.dropna(axis = 1, how ="all", inplace=True) 
    
    # Fixing date format
    df["date"]=df["date"].apply(fix_date)
    df["start_time"]=df["start_time"].apply(fix_start_time)

    # Dropping any rows missing required values except for art column
    clean_df = df.dropna(axis=0, subset=[x for x in col_rename.values() if x != "art"], how="any")
    dropped_df = df[~df.index.isin(clean_df.index)]
    

    
    
    

    req = Request("https://warhorn.net/graphql", method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header("Authorization", "bearer " + token)
    
    eventId = get_event_id(req, event_str)
    roleId = get_gm_role_id(req, event_str)

    clean_df["eventId"] = eventId
    clean_df["roleId"] = roleId

    entries = clean_df.to_dict("records")

    #######################################
    # TODO Manually removing the first entry because it is a D&D game that causes issues in testing but I can't remove it from the original sheet since I don't own it.
    # NEED TO DELETE
    entries.pop(0)
    #######################################

    for e in entries:
        print(e)    

if __name__ == "__main__":
    print("testing")
    
    with open("col_rename.json") as file:
        col_rename = json.load(file)

    with open("warhorn_creds.json") as file: # Use file to refer to the file object
        creds = json.load(file)
    
    with open("warhorn_queries.json") as file:
        warhorn_queries =json.load(file)

    
    main(creds["user_access_token"], creds["sheet_id"], creds["event_str"])
    
    

    