import requests
import json

url = "http://localhost:5001/submit"

tests = {
    "1_Clearly_AI": "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment.",
    
    "2_Clearly_Human": "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better. probably won't go back unless someone drags me there",
    
    "3_Formal_Human_Borderline": "The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and the unintended consequences of prolonged low interest rates on equity and real estate valuations.",
    
    "4_Edited_AI_Borderline": "I've been thinking a lot about remote work lately. There are genuine tradeoffs — flexibility and no commute on one side, isolation and blurred work-life boundaries on the other. Studies show productivity varies widely by individual and role type."
}

for name, text in tests.items():
    payload = {"text": text, "creator_id": f"user-{name}"}
    response = requests.post(url, json=payload)
    res_data = response.json()
    
    print(f"--- TEST CASE: {name} ---")
    print("Content ID: ", res_data.get("content_id"))
    print("Computed Score:", res_data.get("confidence_score"))
    print("Assigned Category:", res_data.get("attribution"))
    print("Signals Raw:", json.dumps(res_data.get("individual_signals"), indent=2))
    print("\n")