from flask import Flask, request, jsonify
import uuid
import datetime
import os
import json
import re

app = Flask(__name__)

# Use a local JSON file to serve as our persistent audit log database
LOG_FILE = "audit_log.json"

# THE 4 PARALLEL DETECTION SIGNALS
# ========================================================
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


def calculate_sentence_variance(text):
    """SIGNAL 2: Measures variation in sentence lengths. Human = 1.0, AI = 0.0"""
    # Split text into sentences using common punctuation marks
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) < 2:
        return 0.5  # Neutral baseline for very short texts
        
    lengths = [len(s.split()) for s in sentences]
    mean_length = sum(lengths) / len(lengths)
    
    # Calculate standard deviation (variance)
    variance_sum = sum((x - mean_length) ** 2 for x in lengths)
    variance = (variance_sum / len(lengths)) ** 0.5
    
    # Normalize variance against a baseline benchmark of 15-word variance
    score = variance / 15.0
    return round(min(max(score, 0.0), 1.0), 2)


def calculate_structural_fluidity(text):
    """SIGNAL 3: Measures AI transition word density. Human = 1.0, AI = 0.0"""
    ai_keywords = ["furthermore", "moreover", "additionally", "consequently", "essential to note", "transformative"]
    words = text.lower().split()
    if not words:
        return 1.0
        
    match_count = 0
    for kw in ai_keywords:
        match_count += text.lower().count(kw)
        
    # High density drops the score close to 0.0
    density = match_count / (len(words) / 100.0)  # instances per 100 words
    score = 1.0 - (density * 0.25)
    return round(min(max(score, 0.0), 1.0), 2)


def calculate_linguistic_flaws(text):
    """SIGNAL 4: Looks for casual slang / flaws. Human = 1.0, AI = 0.0"""
    human_keywords = ["gonna", "gotta", "wanna", "honestly", "probably", "lol", "omw", "so i"]
    match_count = 0
    for kw in human_keywords:
        match_count += text.lower().count(kw)
        
    # Presence of casual phrases elevates human score directly towards 1.0
    if match_count >= 2:
        return 1.0
    elif match_count == 1:
        return 0.75
    else:
        return 0.40  # Flat standard fallback if highly pristine


# AUDIT LOG PERSISTENCE
# ========================================================
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



# ROUTE
# ========================================================
@app.route('/submit', methods=['POST'])
def submit_content():
    data = request.get_json() or {}
    text_content = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()
    
    if not text_content or not creator_id:
        return jsonify({"error": "Missing text or creator_id"}), 400
        
    content_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Run all 4 signals in parallel
    s1 = calculate_vocabulary_variety(text_content)
    s2 = calculate_sentence_variance(text_content)
    s3 = calculate_structural_fluidity(text_content)
    s4 = calculate_linguistic_flaws(text_content)
    
    # Weighted Scoring Formula from planning.md
    final_score = (s1 * 0.25) + (s2 * 0.25) + (s3 * 0.20) + (s4 * 0.30)
    final_score = round(final_score, 2)
    
    # Categorize using the score boundaries defined in milestone 2 planning file
    if final_score <= 0.55:
        attribution = "likely_ai"
    elif 0.56 <= final_score <= 0.75:
        attribution = "uncertain"
    else:
        attribution = "likely_human"
        
    response_payload = {
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence_score": final_score,
        "individual_signals": {
            "vocabulary_variety": s1,
            "sentence_variance": s2,
            "structural_fluidity": s3,
            "linguistic_flaws": s4
        },
        "label": "Pending layout assignment",  # Placeholder for Milestone 5
        "status": "classified"
    }
    
    # Save descriptive metrics to log file
    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution,
        "confidence": final_score,
        "signals": response_payload["individual_signals"],
        "status": "classified"
    }
    write_to_audit_log(log_entry)
    
    return jsonify(response_payload), 200


@app.route('/log', methods=['GET'])
def get_audit_log():
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    return jsonify({"entries": logs}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5001)