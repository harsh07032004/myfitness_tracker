import google.generativeai as genai

api_key = "AIzaSyC-fx2XhicQiXCiua2qsjIKtpxk5YI4CQg"
genai.configure(api_key=api_key)

print("Listing available models...")
for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)
