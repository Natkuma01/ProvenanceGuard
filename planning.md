# Provenance Guard  - Planning & Architecture

This document maps out the system architecture, core detection engine logic, and API contracts for the backend system.

---

## Architecture Narrative

When a user submits text for evaluation, the data travels through a single pipeline:

1. **Rate Limiter Middleware:** The system checks how often the user or client has made requests. If the request volume is within safe bounds, the text passes forward. If not, it blocks the request immediately to prevent spam.
2. **Multi-Signal Detection Pipeline:** The raw text enters the classification engine. The engine runs the text through two independent analysis modules (Vocabulary Variety and Sentence Length Variance). Each module produces an individual mathematical score.
3. **Confidence Scorer:** This module takes the individual scores and processes them into a single confidence rating between 0.0 and 1.0. The math intentionally favors human creators to avoid false accusations.
4. **UX Label Engine:** The system converts the final numerical confidence rating into plain, empathetic English text. This step ensures non-technical users can easily understand the decision status.
5. **Audit Logger:** The system creates a permanent record containing the submission ID, a snippet of the text, individual signal scores, the final classification, and the current status.
6. **API Router Response:** The backend returns a structured JSON payload to the user containing the tracking ID, score, and user-facing text label.

---

## Detection Signals

### Signal 1: Vocabulary Variety 
* **What it measures:** The percentage of unique words used compared to the total number of words in the text.
* **Why it works:** Human writers naturally use a varied vocabulary, mixing in descriptive words and random word choices when crafting prose. AI models tend to pick mathematically optimal words repeatedly to stay strictly focused on a topic.
* **Blind Spot:** If a human writes a technical manual, instructional guide, or repetitive chant, the variety score drops drastically, and the tool might mistake it for AI text.

### Signal 2: Sentence Length Variance 
* **What it measures:** The mathematical variance in sentence lengths across the entire document.
* **Why it works:** Humans naturally mix short, sharp sentences with long, winding ideas. This variation creates a rhythmic "burstiness." AI models write text using highly predictable, uniform sentence lengths to keep readability scores stable.
* **Blind Spot:** Very short texts (such as a 3-sentence poem or a short social media post) do not have enough sentences to establish an accurate variance measurement.

### Signal 3: Structural Fluidity & Transitions 
* **What it measures:** The density of formal transition words (*Moreover, Furthermore, Additionally*) and complex punctuation (*em-dashes, semicolons*).
* **Why it works:** AI models write with calculated smoothness. They frequently rely on predictable introductory phrases or clean complex punctuation to link ideas. Humans rarely use these formal transition words repetitively in casual writing.
* **Blind Spot:** A highly academic human essay or a formal business proposal uses these transitions and could trigger a false AI rating.

### Signal 4: Linguistic Flaws & Informal Slang 
* **What it measures:** The presence of conversational contractions (*gonna, gotta*), text abbreviations, or minor grammatical slip-ups.
* **Why it works:** Human creative writing is filled with conversational character speech, stylistic choices, and occasional typos. AI text defaults to grammatically flawless prose, avoids casual slang unless heavily prompted. 
* **Blind Spot:** A polished piece of edited human fiction might have all slang and typos removed, making it look more like AI text to this specific signal.

---

## False Positive Management

Labeling a human creator's original work as AI-generated damages user trust deeply. The system uses three layers of defense to protect human writers:

1. **Uncertainty Buffer:** If the confidence scoring engine falls into a borderline zone (such as 0.50 to 0.65), the system automatically categorizes the text into an "Uncertain" bucket rather than confidently labeling it as AI.
2. **Empathetic Labeling:** Instead of displaying an aggressive warning, the system displays a soft, clear label that invites collaboration: *"We couldn't verify the origin of this text automatically. If you wrote this, please let us know so we can keep our system fair."*
3. **Seamless Appeal Path:** The creator can immediately submit an appeal request. The system instantly flags the database entry as `under_review`, preserving the creator's standing while a human moderator reviews the case.

---

## API Endpoints

### 1. Content Submission
* **Endpoint:** `POST /api/v1/submit`
* **Request Body:**
```json
{
  "content": "Once upon a time, a human writer sat down to create a story..."
}
```
* **Response Body (200 OK):**
```
{
  "submission_id": "sub_102938475",
  "confidence_score": 0.88,
  "classification": "human",
  "transparency_label": "Verified Human Work: This content matches natural human writing patterns.",
  "status": "completed"
}
```


### 2. Sunmit Appeal
* **Endpoint:** `POST /api/v1/appeal`
* **Request Body:**
```json
{
  "submission_id": "sub_102938475",
  "reason": "This text is an excerpt from my handwritten personal journal."
}
```
* **Response Body (200 OK):**
```
{
  "submission_id": "sub_102938475",
  "status": "under_review",
  "message": "Your appeal has been received. A team member will review it shortly."
}
```


### 3. View Audit Log
* **Endpoint:** `GET /api/v1/log`
* **Request Body:** `None`
* **Response Body (200 OK):**
```
{
  "logs": [
    {
      "submission_id": "sub_102938475",
      "timestamp": "2026-06-29T20:12:17Z",
      "signals": {
        "vocabulary_variety": 0.85,
        "sentence_variance": 0.91
      },
      "final_score": 0.88,
      "classification": "human",
      "status": "under_review",
      "appeal_reason": "This text is an excerpt from my handwritten personal journal."
    }
  ]
}
```