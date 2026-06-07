import json

with open("C:\\Users\\Abhishek\\OneDrive\\Documents\\AIML Projects\\Transcript Intelligence\\Classifier\\master_meetings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

meetings = data.get("meetings", [])

print(type(meetings))
print(len(meetings))
if meetings:
    print(meetings[0].keys())
else:
    print("No meetings found")