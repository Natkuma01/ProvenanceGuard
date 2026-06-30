from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
import datetime
import os
import json
import re

app = Flask(__name__)
LOG_FILE = "audit_log.json"

# Set up global rate limiter with local in-memory storage tracking
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# ==============================================================================
# DETECTORS AND LOOKUPS
# ==============================================================================

def get_transparency_label(score):
    """Maps confidence scores directly to verbatim planning.md label strings."""
    if score <= 0.55:
        return "Content Note: Automated detection systems indicate this text closely matches patterns found in machine-generated writing."
    elif 0.56 <= score <= 0.75:
        return "Label Unverified: Our automated system could not confidently determine the origin of this text. If you are the creator, your attribution status will remain active while we look closer."
    else:
        return "Verified Human Work: This content exhibits natural stylistic variations and authentic human writing patterns."

def calculate_vocabulary_variety(text):
    clean_text = re.sub(r'[^\w\s]', '', text.lower())
    words = clean_text.split()
    if not words:
        return 1.0
    return round(len(set(words)) / len(words), 2)

def calculate_sentence_variance(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) < 2:
        return 0.5
    lengths = [len(s.split()) for s in sentences]
    mean_length = sum(lengths) / len(lengths)
    variance_sum = sum((x - mean_length) ** 2 for x in lengths)
    variance = (variance_sum / len(lengths)) ** 0.5
    return round(min(max(variance / 15.0, 0.0), 1.0), 2)

def calculate_structural_fluidity(text):
    ai_keywords = ["furthermore", "moreover", "additionally", "consequently", "essential to note", "transformative"]
    words = text.lower().split()
    if not words:
        return 1.0
    match_count = sum(text.lower().count(kw) for kw in ai_keywords)
    density = match_count / (len(words) / 100.0) if words else 0
    return round(min(max(1.0 - (density * 0.25), 0.0), 1.0), 2)

def calculate_linguistic_flaws(text):
    human_keywords = ["gonna", "gotta", "wanna", "honestly", "probably", "lol", "omw", "so i"]
    match_count = sum(text.lower().count(kw) for kw in human_keywords)
    if match_count >= 2: return 1.0
    if match_count == 1: return 0.75
    return 0.40

def calculate_trailing_participles(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 1.0
        
    participle_count = 0
    non_participles = {"thing", "something", "anything", "nothing", "everything", "during", "morning", "evening", "ring", "spring", "king", "wing", "sing"}

    for s in sentences:
        if ',' in s:
            parts = s.split(',')
            last_part = parts[-1].strip().lower()
            if last_part:
                words = last_part.split()
                if words:
                    first_word = re.sub(r'[^\w]', '', words[0])
                    if first_word.endswith('ing') and first_word not in non_participles and len(first_word) > 3:
                        participle_count += 1
                        
    ratio = participle_count / len(sentences)
    score = 1.0 - (ratio * 2.5)
    return round(min(max(score, 0.0), 1.0), 2)

# ==============================================================================
# AUDIT LOG PERSISTENCE LOGIC
# ==============================================================================

def read_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def write_logs(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.route('/submit', methods=['POST'])
@limiter.limit("5 per minute; 60 per hour") # Defensible production safety rate limit
def submit_content():
    data = request.get_json() or {}
    text_content = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()
    
    if not text_content or not creator_id:
        return jsonify({"error": "Missing text or creator_id"}), 400
        
    content_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    s1 = calculate_vocabulary_variety(text_content)
    s2 = calculate_sentence_variance(text_content)
    s3 = calculate_structural_fluidity(text_content)
    s4 = calculate_linguistic_flaws(text_content)
    s5 = calculate_trailing_participles(text_content)
    
    final_score = round((s1 * 0.20) + (s2 * 0.20) + (s3 * 0.15) + (s4 * 0.30) + (s5 * 0.15), 2)
    
    if final_score <= 0.55:
        attribution = "likely_ai"
    elif 0.56 <= final_score <= 0.75:
        attribution = "uncertain"
    else:
        attribution = "likely_human"
        
    label_text = get_transparency_label(final_score)
    
    response_payload = {
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence_score": final_score,
        "individual_signals": {
            "vocabulary_variety": s1,
            "sentence_variance": s2,
            "structural_fluidity": s3,
            "linguistic_flaws": s4,
            "trailing_participles": s5
        },
        "transparency_label": label_text,
        "status": "completed"
    }
    
    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution,
        "confidence": final_score,
        "signals": response_payload["individual_signals"],
        "transparency_label": label_text,
        "status": "completed",
        "appeal_reasoning": None
    }
    
    logs = read_logs()
    logs.append(log_entry)
    write_logs(logs)
    
    return jsonify(response_payload), 200



@app.route('/appeal', methods=['POST'])
def appeal_decision():
    data = request.get_json() or {}
    content_id = data.get("content_id", "").strip()
    reasoning = data.get("creator_reasoning", "").strip()
    
    if not content_id or not reasoning:
        return jsonify({"error": "Missing content_id or creator_reasoning"}), 400
        
    logs = read_logs()
    record_found = False
    
    for entry in logs:
        if entry["content_id"] == content_id:
            entry["status"] = "under_review"
            entry["appeal_reasoning"] = reasoning
            # Enforce the unverified fallback UX label during review
            entry["transparency_label"] = get_transparency_label(0.65)
            record_found = True
            break
            
    if not record_found:
        return jsonify({"error": f"Submission with ID {content_id} not found."}), 404
        
    write_logs(logs)
    
    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received. Our team will review it shortly."
    }), 200

@app.route('/log', methods=['GET'])
def get_audit_log():
    return jsonify({"entries": read_logs()}), 200


@app.route('/analytics', methods=['GET'])
def get_analytics():
    """
    STRETCH GOAL: Analytics Dashboard Endpoint
    Computes real-time system metrics directly from the persistent logs file.
    """
    logs = read_logs()
    total_submissions = len(logs)
    
    # Handle the empty state gracefully
    if total_submissions == 0:
        return jsonify({
            "total_submissions_processed": 0,
            "detection_pattern_ratios": {
                "likely_ai_percentage": 0.0,
                "likely_human_percentage": 0.0,
                "uncertain_percentage": 0.0
            },
            "appeal_rate_percentage": 0.0,
            "average_system_confidence_score": 0.0
        }), 200

    ai_count = 0
    human_count = 0
    uncertain_count = 0
    appealed_count = 0
    total_confidence = 0.0
    
    for entry in logs:
        # 1. Count Verdict Patterns
        attr = entry.get("attribution")
        if attr == "likely_ai":
            ai_count += 1
        elif attr == "likely_human":
            human_count += 1
        elif attr == "uncertain":
            uncertain_count += 1
            
        # 2. Count Appeals (entries that are under review or have an appeal reason)
        if entry.get("status") == "under_review" or entry.get("appeal_reasoning") is not None:
            appealed_count += 1
            
        # 3. Sum for Average Confidence
        total_confidence += entry.get("confidence", 0.0)
        
    # Calculate percentages and round cleanly
    verdict_ratios = {
        "likely_ai_percentage": round((ai_count / total_submissions) * 100, 1),
        "likely_human_percentage": round((human_count / total_submissions) * 100, 1),
        "uncertain_percentage": round((uncertain_count / total_submissions) * 100, 1)
    }
    
    # Appeal rate is calculated against total submissions
    appeal_rate = round((appealed_count / total_submissions) * 100, 1)
    avg_confidence = round(total_confidence / total_submissions, 2)
    
    return jsonify({
        "total_submissions_processed": total_submissions,
        "detection_pattern_ratios": verdict_ratios,
        "appeal_rate_percentage": appeal_rate,
        "average_system_confidence_score": avg_confidence
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)