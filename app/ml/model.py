import json
import os
import google.generativeai as genai
from flask import current_app

class FoodClassifier:
    def __init__(self, data_path):
        self.data_path = data_path
        self.food_data = self._load_data()
        self.classes = list(self.food_data.keys())
        
        # Configure Gemini API
        # Always use environment variables for API keys in production!
        api_key = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE") # Placeholder for local testing
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            print("WARNING: GEMINI_API_KEY environment variable not set or is placeholder.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _load_data(self):
        with open(self.data_path, 'r') as f:
            return json.load(f)

    def estimate_from_text(self, food_description):
        """
        Estimates nutrition from a text description (e.g., "2 eggs and toast")
        """
        try:
            prompt = f"""
            You are a Nutritionist API. 
            Analyze this food text: "{food_description}"
            
            Return a JSON object with these keys ONLY (no markdown):
            {{
                "dish": "Short Standard Name",
                "nutrition": {{
                    "calories": integer,
                    "protein": float (grams),
                    "carbs": float (grams),
                    "fat": float (grams),
                    "unit": "serving size description"
                }},
                "vitamins": ["List of 3 key vitamins/minerals"]
            }}
            """
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(text)
        except Exception as e:
            print(f"Error estimating text: {e}")
            return None

    def chat_with_coach(self, user_message, user_context):
        """
        Chat with the AI Coach.
        user_context: string describing user's current stats/goals.
        Returns: { "reply": "text", "action": "type", "data": {} }
        """
        try:
            prompt = f"""
            You are a personal Fitness Coach named 'Titan Coach'.
            User Context: {user_context}
            User Message: "{user_message}"
            
            Your job is to reply helpfully AND take action if needed.
            
            If the user wants to log food (e.g., "I ate an apple"), set action="log_food".
            If the user changes goals (e.g., "I want to bulk", "Set calories to 3000"), set action="update_goal".
            Otherwise, set action="none".
            
            Return a JSON object ONLY:
            {{
                "reply": "Your helpful text response here.",
                "action": "none" OR "log_food" OR "update_goal",
                "data": {{
                    "food_name": "Apple", "calories": 95, "protein": 0.5 (if logging food),
                    "goal_calories": 3000 (if updating goal)
                }}
            }}
            """
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(text)
        except Exception as e:
            print(f"Chat Error: {e}")
            return {"reply": "I'm having trouble thinking right now.", "action": "none"}

    def analyze_body(self, image_path):
        """
        Estimates physical stats from a full-body photo.
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_parts = [{"mime_type": "image/jpeg", "data": image_data}]

            prompt = """
            You are a Fitness AI. Analyze the person in this photo for the purpose of calculating BMI and Calorie Goals.
            
            Estimate the following based on visual proportions:
            1. Gender (Male/Female)
            2. Approximate Height in cm (assume average adult if unclear, e.g., 170-180cm for men, 160-170cm for women)
            3. Approximate Weight in kg (based on build and height)
            
            Return a JSON object with these keys ONLY:
            {
                "gender": "Male" or "Female",
                "height": float (cm),
                "weight": float (kg),
                "body_fat": "Low" or "Medium" or "High"
            }
            If you strictly cannot determine a human is present, return null.
            """
            
            response = self.model.generate_content([prompt, image_parts[0]])
            text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(text)
            
        except Exception as e:
            print(f"Body Analysis Error: {e}")
            return None

    def predict(self, image_path):
        """
        Uses Gemini Vision to identify the food item.
        """
        try:
            # 1. Prepare the image for Gemini
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_parts = [
                {
                    "mime_type": "image/jpeg", # Assumes jpeg/png
                    "data": image_data
                }
            ]

            # 2. Construct the Prompt
            # We give it the list of known foods to restrict its answer if possible,
            # but also allow it to be smart.
            known_foods = ", ".join(self.classes)
            prompt = f"""
            You are an expert Indian Food Nutritionist. 
            Identify the main dish in this image.
            
            Return a JSON object with these keys ONLY (no markdown):
            {{
                "dish": "Name of Dish",
                "nutrition": {{
                    "calories": integer,
                    "protein": float (grams),
                    "carbs": float (grams),
                    "fat": float (grams),
                    "unit": "serving size"
                }},
                "vitamins": ["List of 3 key vitamins/minerals"],
                "advice": "One sentence advice on if this is healthy."
            }}
            """

            # 3. Call Gemini API
            response = self.model.generate_content([prompt, image_parts[0]])
            result_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(result_text)

        except Exception as e:
            print(f"Error calling Gemini: {e}")
            # Fallback
            return {
                "dish": "Error Identifying",
                "nutrition": {
                    "calories": 0,
                    "unit": "-",
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0
                },
                "advice": "Could not analyze."
            }