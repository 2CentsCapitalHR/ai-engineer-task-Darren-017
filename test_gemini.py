# test_gemini.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

PREFERRED_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    # add any future models you want to prefer here
]

def pick_model_name() -> str:
    """
    Auto-detects available models for this API key and returns the best match that
    supports generateContent, preferring the names in PREFERRED_MODELS.
    Falls back to the first available generative model if none of the preferred
    names are present.
    """
    models = list(genai.list_models())
    if not models:
        raise RuntimeError("No models returned by API. Check your API key and project access.")

    # Build index: {model_name -> model_obj} and filter for generateContent support
    generative = {}
    for m in models:
        # Some client versions expose supported methods under this attribute:
        methods = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            generative[m.name] = m

    if not generative:
        # As a fallback, accept models that *look* text-capable
        for m in models:
            if any(k in m.name for k in ["gemini-1.5", "gemini-pro", "flash", "pro"]):
                generative[m.name] = m

    if not generative:
        raise RuntimeError(
            "No generative models available for this key/project. "
            "Confirm your Gemini API key and that the account has access."
        )

    # Prefer known good models in order
    for preferred in PREFERRED_MODELS:
        if preferred in generative:
            return preferred

    # Otherwise just pick the first generative model (stable choice)
    # Sort for deterministic behavior
    return sorted(generative.keys())[0]

def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found.\n"
            "Create a .env in your project folder with:\n"
            "GEMINI_API_KEY=YOUR_ACTUAL_KEY"
        )

    genai.configure(api_key=api_key)

    model_name = pick_model_name()
    print(f"Using model: {model_name}")

    model = genai.GenerativeModel(model_name)

    prompt = "Write a short legal disclaimer in 2 sentences."
    response = model.generate_content(prompt)

    print("\nGemini Response:\n")
    print(response.text)

if __name__ == "__main__":
    main()
