from flask import Flask, request, jsonify
import uuid
import datetime
import os
import json
import re

app = Flask(__name__)

# Use a local JSON file to serve as our persistent audit log database
LOG_FILE = "audit_log.json"

def calculate_vocabulary_variety(text):
    """
    SIGNAL 1: Vocabulary Variety (Type-Token Ratio)
    Measures the ratio of unique words to total words.
    Returns a float score between 0.0 (Very repetitive/AI-like) and 1.0 (Very diverse/Human-like).
    """
    # Clean text: remove punctuation and turn into lowercase
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    words = clean_text.split()
    
    # Edge case: Empty text or no words
    if not words:
        return 1.0
        
    total_words = len(words)
    unique_words = len(set(words))
    
    # Simple type-token ratio calculation
    score = unique_words / total_words
    return round(score, 2)

def write_to_audit_log(entry):
    """Helper function to read, append, and save records to the audit log file."""
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            # Handle empty or corrupted log files safely
            logs = []
            
    logs.append(entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

@app.route('/submit', methods=['POST'])
def submit_content():
    """Endpoint for content attribution analysis."""
    data = request.get_json() or {}
    text_content = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()
    
    # Simple input validation
    if not text_content or not creator_id:
        return jsonify({"error": "Missing required fields: 'text' and 'creator_id'"}), 400
        
    # Generate unique content_id and current timestamp
    content_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Execute our first signal
    signal_1_score = calculate_vocabulary_variety(text_content)
    
    # Determine placeholder attribution based on our single operational signal
    # A low vocabulary diversity flags content as likely AI for now
    if signal_1_score < 0.60:
        attribution = "likely_ai"
    else:
        attribution = "likely_human"
        
    # Create the response object using milestone placeholder values for missing components
    response_payload = {
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "signal_1_vocab_score": signal_1_score,
        "confidence": 0.50, # Placeholder value until Milestone 4 blending
        "label": "Pending full verification model mapping", # Placeholder value until Milestone 5 layout
        "status": "classified"
    }
    
    # Save a copy to our structured logging system
    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution,
        "confidence": response_payload["confidence"],
        "signal_1_score": signal_1_score,
        "status": response_payload["status"]
    }
    write_to_audit_log(log_entry)
    
    return jsonify(response_payload), 200

@app.route('/log', methods=['GET'])
def get_audit_log():
    """Endpoint that returns all current system audit logs."""
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
            
    return jsonify({"entries": logs}), 200

if __name__ == '__main__':
    # Run server locally on default port 5000
    app.run(debug=True, port=5001)