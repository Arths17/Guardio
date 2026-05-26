from google import genai
client = genai.Client(api_key=" AIzaSyBUQ86lYxqV3TUnSTybTLK6L4khPBAyq3Q")
prompt = input("Enter your prompt: ")
response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    config={
        "system_instruction": "You are a helpful assistant that provides concise and accurate information about cybersecurity. You are are a friendly mentor who is always eager to share knowledge and help others understand complex cybersecurity concepts in a simple way. You can provide explanations, tips, and best practices related to cybersecurity topics.",
    },
    contents=prompt
)

print(response.text)






'''
text = "Hey, are you down to grab some pizza later? I'm starving!"

response = client.models.generate_content(
    model="gemini-3.1-flash-lite-preview",
    config={
        "system_instruction": "Only output the translated text"
    },
    contents=f"Translate the following text to German: {text}"
)

print(response.text)
'''