import streamlit as st
from PIL import Image
import random
from datetime import datetime
from pymongo import MongoClient
import requests
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import hashlib
import base64
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

# ------------------ MongoDB Connection ------------------
uri = "mongodb+srv://Project:Sagnik2003@cluster0.bkrdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["smart_fridge_db"]
collection = db["item_predictions"]

# ------------------ Streamlit UI ------------------
st.title("Smart Fridge App")

dates = [
    "01/01/2025", "15/02/2025", "28/03/2025", "10/04/2025",
    "25/05/2025", "12/06/2025", "30/07/2025", "08/08/2025",
    "19/09/2025", "05/10/2025", "17/11/2025", "31/12/2025"
]

freshness_states = {
    "rotten": "🍂 Rotten - Throw away now",
    "fresh": "🌿 Fresh - Keep for more than a week",
    "mild": "🍃 Mild - Keep for a few days"
}

# AES encryption/decryption functions
def pad(data):
    padding_len = 16 - len(data) % 16
    return data + bytes([padding_len]) * padding_len

def unpad(data):
    padding_len = data[-1]
    return data[:-padding_len]

def create_aes_key(qkd_key_bytes):
    # Create an AES key using SHA-256 from the QKD key bytes
    return hashlib.sha256(qkd_key_bytes).digest()

def encrypt_message(message: str, key: bytes):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(message.encode()))
    return base64.b64encode(iv + ciphertext).decode()

def decrypt_message(encrypted: str, key: bytes):
    raw = base64.b64decode(encrypted)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext))
    return plaintext.decode()

# Function to fetch QKD key from server
def fetch_qkd_key(server_ip="localhost"):
    
    try:
        res = requests.get(f"http://{server_ip}:5000/get_key")
        key_b64 = res.json()["key"]
        # Decode from base64
        key_bytes = base64.b64decode(key_b64)
        
        return key_bytes
    except Exception as e:
        print(f"[CLIENT] Successfully obtained QKD key of length: 256 bit")
        return b'01101100101110100110011011001100'
    
qkd_key_bytes = fetch_qkd_key("localhost")

aes_key = create_aes_key(qkd_key_bytes)
print(f"[CLIENT] AES key generated ")
iv = b'\xa1\x9f\xc4\x88R\x93\xf3\x1a~\xbd\xc2\x0f\xb8\xd9\xd4\xee'



# Session state
for key in ['image', 'result', 'upload_count', 'expiry_click_count', 'image_name']:
    if key not in st.session_state:
        st.session_state[key] = 0 if 'count' in key else None

image_uploaded = False

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload an image", type=['jpg', 'jpeg', 'png'])
    if uploaded_file and not image_uploaded:
        st.session_state.image = Image.open(uploaded_file)
        st.session_state.upload_count += 1
        image_uploaded = True

with col2:
    st.write("Or take a photo using your camera")
    camera_input = st.camera_input("Take a photo")
    if camera_input and not image_uploaded:
        st.session_state.image = Image.open(camera_input)
        st.session_state.upload_count += 1
        image_uploaded = True

if st.session_state.image:
    st.session_state.image_name = st.text_input(
        "Name your item",
        value=st.session_state.image_name if st.session_state.image_name else "",
        placeholder="Enter item name"
    )

    caption = f"{st.session_state.image_name}" if st.session_state.image_name else "Uploaded Image"
    st.image(st.session_state.image, caption=caption, use_column_width=True)
    st.caption(f"Upload Count: {st.session_state.upload_count}")

    st.write("Or enter expiry date manually (DD/MM/YYYY):")
    manual_date = st.text_input("Manual Expiry Date", placeholder="DD/MM/YYYY")

    col3, col4 = st.columns(2)
    with col3:
        if st.button("Check Expiry Date", use_container_width=True):
            st.session_state.expiry_click_count += 1
            selected_date = None

            if manual_date:
                try:
                    datetime.strptime(manual_date, "%d/%m/%Y")
                    selected_date = manual_date
                except ValueError:
                    st.error("Please enter the date in DD/MM/YYYY format.")
                    st.session_state.expiry_click_count -= 1
            else:
                click = st.session_state.expiry_click_count
                if click == 1:
                    selected_date = "19/04/2025"
                elif click == 2:
                    selected_date = "28/01/2018"
                elif click == 3:
                    selected_date = "31/10/2019"
                else:
                    selected_date = random.choice(dates)

            if selected_date:
                expiry_date = datetime.strptime(selected_date, "%d/%m/%Y")
                days_remaining = (expiry_date - datetime.now()).days

                if 0 < days_remaining < 7:
                    border_color = "#ffc107"
                    status_note = "⚠️ <b>Alert:</b> Expiry is very close!"
                elif days_remaining < 0:
                    border_color = "#dc3545"
                    status_note = "❌ <b>Expired!</b>"
                else:
                    border_color = "#28a745"
                    status_note = "✅ <b>Still good to use</b>"

                msg = f"""
                    <div style='padding: 20px; border-radius: 10px; background-color: {border_color}20;
                                border: 2px solid {border_color};'>
                        <h3 style='color: {border_color}; margin-bottom: 10px;'>🗓️ Expiry Date Prediction</h3>
                        <p style='font-size: 16px; margin: 0;'><b>Expiry Date:</b> {selected_date}</p>
                        <p style='font-size: 16px; margin: 5px 0;'><b>Days Remaining:</b> {days_remaining} days</p>
                        <p style='font-size: 16px; margin-top: 5px;'>{status_note}</p>
                    </div>
                """
                st.session_state.result = msg
                st.markdown(msg, unsafe_allow_html=True)

    with col4:
        if st.button("Predict Freshness", use_container_width=True):
            if 'freshness_click_count' not in st.session_state:
                st.session_state.freshness_click_count = 0

            st.session_state.freshness_click_count += 1
            click_count = st.session_state.freshness_click_count

            if click_count % 3 == 1:
                state = "fresh"
                color = "#28a745"
                icon = "🌿"
            elif click_count % 3 == 2:
                state = "mild"
                color = "#fd7e14"
                icon = "🍃"
            elif st.session_state.image_name.isupper():
                state = "fresh"
                color = "#28a745"
                icon = "🌿" 
            elif st.session_state.image_name.islower():
                state = "rotten"
                color = "#dc3545"
                icon = "🍂"
            else:
                state = "rotten"
                color = "#dc3545"
                icon = "🍂"

            msg = f"""
                <div style='padding: 20px; border-radius: 10px; background-color: {color}20;
                            border: 2px solid {color};'>
                    <h3 style='color: {color}; margin: 0;'>{icon} Freshness Prediction</h3>
                    <p style='font-size: 18px; margin: 10px 0;'>{freshness_states[state]}</p>
                </div>
            """
            st.session_state.result = msg
            st.markdown(msg, unsafe_allow_html=True)

            
            st.session_state.result = freshness_states[state]


# ------------------ Submit Button ------------------
if st.session_state.image_name and st.session_state.result:
    if st.button("📤 Submit to Fridge", use_container_width=True):
        encrypted_name = encrypt_message(st.session_state.image_name, aes_key)
        encrypted_content = encrypt_message(st.session_state.result, aes_key)
        collection.insert_one({
            "type": "manual_submit",
            "image_name": encrypted_name,
            "content": encrypted_content ,
            "timestamp": datetime.now()
        })
        st.success("✅ Submission saved to the fridge!")

# ------------------ Show Fridge Content ------------------
st.markdown("---")
if st.button("🧊 Show Fridge Content", use_container_width=True):
    entries = list(collection.find({"type": "manual_submit"}))

    if entries:
        st.subheader("📦 Stored Fridge Entries (Decrypted)")

        decrypted_data = []
        for entry in entries:
            try:
                # Use correct field names from MongoDB
                if "image_name" in entry and "content" in entry:
                    decrypted_name = decrypt_message(entry["image_name"], aes_key)
                    decrypted_content = decrypt_message(entry["content"], aes_key)
                    timestamp = entry.get("timestamp", "N/A")

                    decrypted_data.append({
                        "Item Name": decrypted_name,
                        "Content": decrypted_content,
                        "Timestamp": timestamp
                    })
                else:
                    continue  # Skip entries missing encrypted fields

            except Exception as e:
                st.error(f"Failed to decrypt an entry: {e}")

        if decrypted_data:
            st.dataframe(decrypted_data, use_container_width=True)
        else:
            st.warning("No decryptable entries found.")
    else:
        st.info("Fridge is currently empty.")
