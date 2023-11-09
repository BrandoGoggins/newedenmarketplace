from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS
import pymongo
import os
import sys
sys.path.append('/root/code/eve-aws')
from utils import mongodbData as mdb
from utils import utilities as utils
import pandas as pd
import json
from utils import ItemIdEnum as item
import numpy as np
from pathlib import Path
import re
import requests
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

# from dotenv import load_dotenv
# from flask_jwt_extended import (
#     JWTManager, create_access_token, jwt_refresh_token_required, get_jwt_identity
# )

# load_dotenv()

app = Flask(__name__)
# app.config['JWT_SECRET_KEY'] = 'K2XqZyRlaAsP1lFtd4OLsqnfSExNcIe6P026xIz1nZI'  # Change this!
# jwt = JWTManager(app)
# Use CORS with your app
CORS(app)

db = mdb.mongoData('eve-orders-the-forge')

dbh = mdb.mongoData('eve-historical-daily-the-forge')

BASE_DIR = Path(__file__).resolve().parent.parent


JWK_ALGORITHM = "RS256"
JWK_ISSUERS = ("login.eveonline.com", "https://login.eveonline.com")
JWK_AUDIENCE = "EVE Online"

app.secret_key = CLIENT_SECRET


def is_roman_numeral(word):
    # Regex to match a Roman numeral
    roman_regex = re.compile(r'^(?=[MDCLXVI])(M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))$', re.IGNORECASE)
    return bool(roman_regex.match(word))

def format_item_name(item_name):
    if not item_name:
        return ''

    # Split the item_name into words, then process each word
    words = item_name.lower().split('_')
    formatted_words = []
    for word in words:
        # If the word is a Roman numeral, capitalize all letters, otherwise just capitalize the first letter
        formatted_word = word.upper() if is_roman_numeral(word) else word.capitalize()
        formatted_words.append(formatted_word)

    # Join the words back together
    return ' '.join(formatted_words)

def validate_eve_jwt(token: str) -> dict:
    """Validate a JWT access token retrieved from the EVE SSO.

    Args:
        token: A JWT access token originating from the EVE SSO
    Returns:
        The contents of the validated JWT access token if there are no errors
    """
    # fetch JWKs URL from meta data endpoint
    res = requests.get(SSO_META_DATA_URL)
    res.raise_for_status()
    data = res.json()
    try:
        jwks_uri = data["jwks_uri"]
    except KeyError:
        raise RuntimeError(
            f"Invalid data received from the SSO meta data endpoint: {data}"
        ) from None

    # fetch JWKs from endpoint
    res = requests.get(jwks_uri)
    res.raise_for_status()
    data = res.json()
    try:
        jwk_sets = data["keys"]
    except KeyError:
        raise RuntimeError(
            f"Invalid data received from the the jwks endpoint: {data}"
        ) from None

    # pick the JWK with the requested alogorithm
    jwk_set = [item for item in jwk_sets if item["alg"] == JWK_ALGORITHM].pop()

    # try to decode the token and validate it against expected values
    # will raise JWT exceptions if decoding fails or expected values do not match
    contents = jwt.decode(
        token=token,
        key=jwk_set,
        algorithms=jwk_set["alg"],
        issuer=JWK_ISSUERS,
        audience=JWK_AUDIENCE,
    )
    return contents


@app.route('/refresh_token', methods=['POST'])
def refresh():
    # This endpoint should require some form of authentication to make sure
    # that only the authenticated user can refresh their access token

    refresh_token = request.json.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    # Prepare the data for the token refresh
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    # Prepare the basic auth header
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)

    # Make the POST request to get the new access token
    response = requests.post(TOKEN_URL, data=data, auth=auth)

    # If the request is successful, the response should contain the new access token
    if response.status_code == 200:
        new_tokens = response.json()
        return jsonify(new_tokens), 200
    else:
        # Log error and return the response
        print(f"Failed to refresh token: {response.json()}")
        return jsonify(response.json()), response.status_code



@app.route('/exchange', methods=['POST'])
def exchange_code_for_token():
    

    code = request.json.get('code')
    
    # Prepare the data for the token exchange
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK_URL,
    }
    
    # Prepare the basic auth header
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)

    # Make the POST request to get the access token
    response = requests.post(TOKEN_URL, data=data, auth=auth)

    # If the request is successful, the response should contain the access token and refresh token
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens['access_token']

        return jsonify(tokens), 200
    else:
        return jsonify(response.json()), response.status_code


@app.route('/get_item/<item_name>/<item_type>')
def get_item(item_name: str, item_type: str):
    print(f"**Received name: {item_name}, Item Type: {item_type}**")
    if item_type == 'type':
        df = db.syncPullLastDocument(item_name)
        df = df.sort_values(by=['issued'], ascending=False)

        if df is not None:
            return df.to_json(orient="records"), 200
    return jsonify({"error": "Data not found for the given ID"}), 404

@app.route('/get_bubble_data', methods=['POST'])
def get_bubble_data():
    data = request.json
    selected_id = data.get('selectedValue')
    id_type = data.get('itemType') # New parameter. Should be 'group' or 'type'

    print(f"Received ID: {selected_id}, ID Type: {id_type}")

    if not selected_id or not id_type:
        return jsonify({"error": "selectedValue or idType not provided in the request."}), 400
    
    with open(BASE_DIR / "visualization" / "marketGroups.json", "r") as f:
        market_data = json.load(f)
    
    # Depending on the id_type, choose the extraction method
    if id_type == "type":
        all_entries = utils.extract_types_by_type_id(market_data, selected_id)

    
    print(all_entries)
    # Fetch data for these types
    combined_df = pd.DataFrame()
    for entry in all_entries:
        print(f"Processing {entry['item_name']}")
        temp_df = pd.DataFrame(dbh.syncPullAllCollectionDocuments(entry['item_name']))
        temp_df = temp_df.sort_values(by=['date'], ascending=False)
        if temp_df.empty:
            continue
        top_row = temp_df.iloc[[0]] # Note: Using [[0]] will ensure we still get a DataFrame, not a Series
        top_row["percent_profit"] = (top_row['average'] - top_row['lowest']) / top_row['lowest'] * 100
        combined_df = pd.concat([combined_df, top_row], ignore_index=True) # Combine the dataframes
    combined_df['volume'] = combined_df['volume'].astype(float)
    combined_df['adjusted_volume'] = np.sqrt(combined_df['volume'])
    combined_df = combined_df.sort_values(by='percent_profit', ascending=False)
    
    # Convert DataFrame to JSON and return
    return combined_df.to_json(orient="records"), 200


@app.route('/get_graph_data', methods=['POST'])
async def get_graph_data():
    # Extract selected value from request
    data = request.json
    id_type = data.get('itemType')
    print(f'**{id_type}**')
    df = pd.DataFrame()
    
    if id_type == "type":
        selected_value = data.get('selectedValue')
        print(f'{selected_value}***')
        if not selected_value:
            return jsonify({"error": "selectedValue not provided in the request."}), 400
        df = dbh.syncPullAllCollectionDocuments(selected_value)
        if df is None:
            return jsonify({"error": "No data found for the selected value."}), 404

    df = df.sort_values(by=['date'], ascending=False)

    return df.to_json(orient="records"), 200

@app.route('/get_character_id')
def get_character_id():
    auth_header = request.headers.get('Authorization')
    
    if auth_header:
        # Split the header into 'Bearer' and the token part
        parts = auth_header.split()
        
        if parts[0].lower() != 'bearer':
            return jsonify({"message": "Authorization header must start with Bearer"}), 401
        elif len(parts) == 1:
            return jsonify({"message": "Token not found"}), 401
        elif len(parts) > 2:
            return jsonify({"message": "Authorization header must be Bearer token"}), 401

        access_token = parts[1]
        
    jwt = validate_eve_jwt(access_token)
    character_id = jwt["sub"].split(":")[2]
    character_name = jwt["name"]
    print(f"**Received character ID: {character_id}**")
    print(f"**Received character name: {character_name}**")
    if not access_token:
        return 'No access token found. Please login first.'

    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(VERIFY_URL, headers=headers)
    print(f"**Received response: {response}**")
    if response.status_code == 200:
        character_data = response.json()
        print(f"**Received character data: {character_data}**")
        return jsonify(character_data)
    else:
        return 'Error retrieving character ID'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
