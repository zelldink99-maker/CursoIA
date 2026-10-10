from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
print(bool(os.getenv("GEMINI_API_KEY")))
# o el nombre de tu variable, si tu proveedor no es Gemini