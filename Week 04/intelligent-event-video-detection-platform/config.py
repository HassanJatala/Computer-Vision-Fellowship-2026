from dotenv import load_dotenv
import os

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
DATABASE_PATH = os.getenv("DATABASE_PATH")
DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", 0.5))
TRACKER = os.getenv("TRACKER")
DWELL_THRESHOLD_SECONDS = int(os.getenv("DWELL_THRESHOLD_SECONDS", 60))
OCCUPANCY_THRESHOLD = int(os.getenv("OCCUPANCY_THRESHOLD", 10))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")