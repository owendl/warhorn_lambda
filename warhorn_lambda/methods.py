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



if __name__ == "__main__":
    print("testing")

    with open("warhorn_creds.json") as file: # Use file to refer to the file object
        creds = json.load(file)
    with open("warhorn_queries.json") as file:
        warhorn_queries =json.load(file)
    
    
    req = Request("https://warhorn.net/graphql", method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header("Authorization", "bearer " + creds["user_access_token"])

    

    