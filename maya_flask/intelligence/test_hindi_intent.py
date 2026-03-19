import json
from intent_classifier import classifier

def test_hindi_intents():
    test_cases = [
        # YouTube
        ("ओपन यूट्यूब", "youtube"),
        ("यूट्यूब खोलो", "youtube"),
        ("youtube चलाओ", "youtube"),
        ("ओपन युटुब एंड प्ले सॉन्ग तेरे संग यारा", "youtube"),
        ("youtube par search karo chocolate cake", "youtube"),
        
        # Google
        ("गूगल पर सर्च करो", "google"),
        ("google kholo", "google"),
        ("search for climate change on google", "google"),
        
        # Weather
        ("आज का मौसम कैसा है", "weather"),
        ("delhi mein weather batao", "weather"),
        ("temperature check karo mumbai ka", "weather"),
    ]

    print(f"{'Input':<50} | {'Expected':<10} | {'Result':<10} | {'Status'}")
    print("-" * 85)

    passed = 0
    for user_input, expected_tool in test_cases:
        result = classifier.classify(user_input)
        actual_tool = result.tool if result.is_action else None
        
        status = "✅ PASS" if actual_tool == expected_tool else "❌ FAIL"
        if actual_tool == expected_tool:
            passed += 1
            
        print(f"{user_input:<50} | {str(expected_tool):<10} | {str(actual_tool):<10} | {status}")
        if result.is_action:
            print(f"  └─ Forced Tag: {result.forced_tag}")
            print(f"  └─ Params: {result.params}")

    print("-" * 85)
    print(f"Total: {len(test_cases)}, Passed: {passed}, Failed: {len(test_cases) - passed}")

if __name__ == "__main__":
    test_hindi_intents()
