import os
import hmac
import json
import re
import time
import logging
from collections import defaultdict
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from knowledge_base import KNOWLEDGE_BASE
except ImportError:  # app still runs, just without the reference-protocol layer
    KNOWLEDGE_BASE = []

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("doctorvet")

VERSION = "6.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Optional: set DOCTORVET_ACCESS_CODE on the server so only people who know the code can use your paid Gemini key.
ACCESS_CODE = os.environ.get("DOCTORVET_ACCESS_CODE", "")
# Default = Gemini 3.8 Flash (GA). If it ever fails (renamed/retired/no access on this key), the next model in
# FALLBACK_MODELS is tried automatically. gemini-2.5-flash is kept at the end of the chain as a long-lived safety
# net since Google has said the 2.5 models keep being served "until further notice" even though 3.x is now default.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.6-flash,gemini-2.5-flash").split(",") if m.strip()]
# IMPORTANT (Sept 2026): Google now requires "auth keys" (the default for any key created in AI Studio after
# 28 May 2026). Old unrestricted "standard" keys were rejected from 19 June 2026, and ALL standard keys stop
# working from September 2026. If every request fails with an auth/permission error regardless of model, this is
# almost always the reason - go to Google AI Studio -> API Keys and create a fresh key (it will be an auth key
# automatically), then update GEMINI_API_KEY.
# Optional public-deployment switch: hide exact drug doses and leave them to the veterinarian.
HIDE_DOSES = os.environ.get("DOCTORVET_HIDE_DOSES", "0") == "1"
CRITIC_MODEL = os.environ.get("DOCTORVET_CRITIC_MODEL", MODEL_NAME)
CRITIC_ENABLED = os.environ.get("DOCTORVET_CRITIC", "1") != "0"

app = FastAPI(title="DoctorVet AI - Veterinary Diagnostic Support", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your real domain in production
    allow_credentials=False,  # we use a header (X-Access-Code), never cookies — "*" + credentials is invalid/unsafe together
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception:
    client = None

# Simple in-memory rate limit (per IP, per process). Use a proper gateway/Redis if you deploy several workers.
RATE_LIMIT_REQUESTS = int(os.environ.get("DOCTORVET_RATE_LIMIT", "20"))
RATE_LIMIT_WINDOW = 60
_request_log: dict = defaultdict(list)
_last_prune = time.time()


def client_ip(request: Request) -> str:
    """Real client IP behind a reverse proxy (Render/Hugging Face/etc. set X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request):
    global _last_prune
    ip = client_ip(request)
    now = time.time()

    # Housekeeping: drop IPs with no recent activity so this dict can't grow forever on a long-lived server.
    if now - _last_prune > RATE_LIMIT_WINDOW:
        for key in [k for k, v in _request_log.items() if not v or now - v[-1] >= RATE_LIMIT_WINDOW]:
            del _request_log[key]
        _last_prune = now

    recent = [t for t in _request_log[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(recent) >= RATE_LIMIT_REQUESTS:
        _request_log[ip] = recent
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")
    recent.append(now)
    _request_log[ip] = recent


def friendly_ai_error(exc: Exception) -> str:
    """Never leak keys/internal details to the browser; the full error goes to the server log."""
    text = str(exc).lower()
    if "api key" in text or "api_key" in text or "permission" in text or "unauthenticated" in text or "credential" in text:
        return "AI service is not configured correctly on the server. Please contact the app owner."
    if "quota" in text or "rate" in text or "429" in text or "resource_exhausted" in text:
        return "The AI service is busy right now. Please try again in a minute."
    if "safety" in text or "blocked" in text:
        return "The AI could not analyse this file. Please try a clearer photo of the animal."
    return "Analysis failed. Please try again with a clearer photo, or try again later."


IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/avi"}
ALLOWED_TYPES = IMAGE_TYPES | VIDEO_TYPES
MAX_IMAGES = 4
# Gemini inline uploads must stay under ~20 MB total request size
MAX_TOTAL_BYTES = 20 * 1024 * 1024

DISCLAIMER = (
    "This is an AI-assisted visual screening, not a laboratory-confirmed or in-person "
    "diagnosis. A photo cannot measure heart rate, blood values or internal disease. "
    "Confirm the diagnosis and every drug dose with a licensed veterinarian before treatment."
)

# Visual-only screening should never claim near-certainty.
MAX_VISUAL_CONFIDENCE = 85

# ----------------------------------------------------------------------------- species helpers
SPECIES_ALIASES = {
    "cow": "cattle", "cows": "cattle", "calf": "cattle", "bull": "cattle", "ox": "cattle",
    "bovine": "cattle", "gaay": "cattle", "gai": "cattle", "heifer": "cattle",
    "bhains": "buffalo", "buffaloes": "buffalo", "buffalo": "buffalo",
    "bakri": "goat", "goats": "goat", "kid": "goat",
    "bher": "sheep", "lamb": "sheep", "ram": "sheep", "ewe": "sheep",
    "oont": "camel", "dromedary": "camel", "camels": "camel",
    "chicken": "poultry", "hen": "poultry", "broiler": "poultry", "layer": "poultry",
    "murgi": "poultry", "rooster": "poultry", "chick": "poultry", "turkey": "poultry", "quail": "poultry",
    "batakh": "duck", "ducks": "duck",
    "kutta": "dog", "puppy": "dog", "dogs": "dog",
    "billi": "cat", "kitten": "cat", "cats": "cat",
    "ghora": "horse", "foal": "horse", "mare": "horse", "stallion": "horse",
    "gadha": "donkey", "khargosh": "rabbit", "soor": "pig", "swine": "pig",
}
CANONICAL = {"cattle", "buffalo", "goat", "sheep", "camel", "poultry", "duck", "dog", "cat",
             "horse", "donkey", "pig", "rabbit"}
FOOD_ANIMALS = {"cattle", "buffalo", "goat", "sheep", "camel", "poultry", "duck", "pig", "rabbit"}


def canonical_species(*texts: str) -> set:
    found = set()
    for text in texts:
        for word in re.findall(r"[a-z]+", (text or "").lower()):
            if word in CANONICAL:
                found.add(word)
            elif word in SPECIES_ALIASES:
                found.add(SPECIES_ALIASES[word])
    return found


# Typical rectal temperature ranges (deg C) for a quick fever / hypothermia flag.
NORMAL_TEMP_C = {
    "camel": (36.0, 38.6), "cattle": (38.0, 39.5), "buffalo": (37.5, 39.3),
    "goat": (38.5, 40.0), "sheep": (38.5, 40.0), "horse": (37.2, 38.6),
    "donkey": (36.5, 38.5), "dog": (38.0, 39.3), "cat": (38.1, 39.3),
    "poultry": (40.5, 43.0), "duck": (40.5, 43.0), "pig": (38.0, 39.5), "rabbit": (38.5, 40.0),
}

# ----------------------------------------------------------------------------- prompts
SYSTEM_INSTRUCTION = """You are DoctorVet AI, a veterinary clinical decision-support system. You reason like a careful, board-certified veterinary clinician performing a visual examination, following WOAH, FAO, WSAVA and standard veterinary-textbook knowledge.

CLINICAL METHOD (follow in order):
1. Verify the image(s)/video actually show an animal and are adequate. If not, set indeterminate=true and explain what photo is needed.
2. Identify species, approximate age class and body condition. Do not assume the species given by the user - verify it visually and say so if it conflicts.
3. Record ONLY findings you can actually see (posture, gait, coat/skin, eyes, nose, mouth, udder, hooves/pads, feathers, discharges, swelling, wounds, respiration effort). Never invent findings. When several images are given, cross-check them.
4. List what CANNOT be assessed from a photo (heart/respiratory rate, mucous membrane colour if not visible, blood tests, internal organs).
5. Use the owner's clinical history (age, temperature, duration, weight, symptoms) as supporting context only. An abnormal temperature raises suspicion of infection but does not identify a disease.
6. Build a ranked differential diagnosis. Give a primary diagnosis only if the visible evidence supports it; otherwise use a syndromic/descriptive diagnosis (e.g. "vesicular lesions - cause undetermined").
7. Note evidence for AND against the primary diagnosis.
8. Assign severity and urgency honestly, and list confirmatory tests a real vet would do.

HONESTY RULES (critical):
- Never fabricate certainty. Visual-only confidence must be calibrated: rarely above 85%. Use lower values when several diseases look alike.
- If unsure, say "Indeterminate" and ask for more information/photos. This is correct behaviour, not a failure.

TREATMENT & SAFETY RULES:
- Use generic (INN) drug names. Give dose_mg_per_kg as a number when a standard weight-based dose exists, plus route, frequency and duration. If you are not confident of a dose, leave dose_mg_per_kg null and write "dose per vet - confirm weight-based dose". NEVER do total-dose arithmetic yourself - the server calculates it from body weight.
- Antibiotics only when bacterial disease is plausible (antimicrobial stewardship). Do not recommend antibiotics for viral diseases except for secondary-infection cover, and say so.
- For food-producing animals (cattle, buffalo, goat, sheep, camel, poultry, ducks, pigs) always state the MEAT and MILK/EGG WITHDRAWAL period for each drug. Never suggest chloramphenicol, nitrofurans, clenbuterol, stilbenes, or metronidazole for food animals.
- Species hazards: never paracetamol/acetaminophen or permethrin in cats; warn about ivermectin in Collie-type dogs (MDR1); avoid NSAIDs in dehydrated animals or with kidney disease; no human drugs unless a recognised veterinary use.
- CAMELS (dromedaries): they differ from cattle - do not copy cattle doses blindly and never dose by "cow-sized" guess; weight must be estimated carefully. Camels are extremely sensitive to ionophore feed additives (monensin, salinomycin, lasalocid) - warn if contaminated poultry/cattle feed is possible. Important camel diseases to consider: sarcoptic mange, trypanosomiasis (surra), camel pox, contagious ecthyma, papillomatosis, calf diarrhoea, pneumonia, brucellosis, haemorrhagic septicaemia, caseous lymphadenitis/abscesses, ringworm, tick infestation, foot/pad injury, anthrax, rabies, and MERS-CoV carriage (public-health hazard). Raw camel milk/meat can carry brucellosis, tuberculosis and MERS-CoV: advise boiling/pasteurising milk and cooking meat.
- If a NOTIFIABLE / reportable disease is plausible (FMD, HPAI/bird flu, Newcastle, PPR, rabies, anthrax, lumpy skin disease, brucellosis, CCPP, sheep/goat pox etc.) set notifiable_suspected.suspected=true, advise isolation, biosecurity and contacting the local livestock/animal-health authority, and do NOT suggest home treatment that delays reporting.
- If the disease is zoonotic (rabies, brucellosis, anthrax, camel pox, ecthyma, mange, ringworm, avian influenza, MERS-CoV, leptospirosis, etc.) set zoonotic_risk.present=true with concrete human-protection steps.
- Never advise the owner to euthanise; say a vet should assess prognosis.
- Include practical supportive care: hydration, feeding, housing, isolation, hygiene.
- Provide a short farmer-friendly summary in Roman Urdu (urdu_summary) AND the same summary in Urdu script (urdu_script_summary) that repeat the key action steps and warnings clearly.

OUTPUT: valid JSON only, matching the requested schema exactly. No markdown, no commentary outside JSON."""

CRITIC_SYSTEM = """You are the DoctorVet AI Critic - a senior veterinary reviewer who checks a colleague's draft report. You did NOT see the images; you must not add, remove or change any visual finding, species, image_quality or not_assessable entry.
Your job:
- Challenge false positives: lower confidence_percent, reorder differentials or set indeterminate=true if the evidence does not support the primary diagnosis.
- Fix medical logic: remove unsupported, unsafe or wrongly-targeted drugs; correct dose_mg_per_kg to standard published ranges or set it to null with 'dose per vet'; make sure every medicine for a food animal has a withdrawal statement; keep antimicrobial stewardship (no antibiotics for purely viral disease except secondary cover).
- Make the treatment consistent with the REFERENCE PROTOCOLS provided (when relevant to the diagnosis).
- Make sure notifiable_suspected and zoonotic_risk are set correctly and that isolation/biosecurity/human-protection advice is present.
- Keep the Roman Urdu and Urdu-script summaries consistent with any changes.
Return the complete corrected report as valid JSON with exactly the same schema and field names. No markdown."""

JSON_SCHEMA_DESCRIPTION = """{
  "species_detected": "string",
  "age_class": "string (e.g. calf, adult, unknown)",
  "body_condition": "string",
  "image_quality": "string (adequate / limited / poor and why)",
  "clinical_findings": ["only findings visible in the image(s)"],
  "not_assessable": ["things a photo cannot show"],
  "primary_diagnosis": "string",
  "confidence_percent": 0,
  "key_evidence": ["evidence supporting the primary diagnosis"],
  "evidence_against": ["findings that argue against it"],
  "differentials": [
    {"name": "string", "likelihood": "High | Medium | Low", "reasoning": "string", "how_to_differentiate": "string"}
  ],
  "severity": "Low | Moderate | High | Critical",
  "severity_reasoning": "string",
  "urgency": "Emergency - vet now | Same day | Within 48 hours | Routine / monitor",
  "notifiable_suspected": {"suspected": false, "disease": "string", "action": "string"},
  "zoonotic_risk": {"present": false, "notes": "string"},
  "immediate_actions": ["first things to do right now"],
  "medicines": [
    {"name": "generic name", "dose_mg_per_kg": null, "dose": "text dose e.g. '0.2 mg/kg' or 'dose per vet'", "route": "string", "frequency": "string", "duration": "string", "withdrawal": "meat/milk/egg withdrawal or 'n/a (non-food animal)'", "notes": "cautions / Roman Urdu instruction"}
  ],
  "treatment_steps": ["string"],
  "supportive_care": ["string"],
  "confirmatory_tests": ["string"],
  "prevention": ["string"],
  "follow_up": "string",
  "red_flags": ["signs that mean get a vet immediately"],
  "info_needed": ["extra photos or history that would improve accuracy"],
  "urdu_summary": "string in Roman Urdu (English letters)",
  "urdu_script_summary": "the same short farmer-friendly summary written in proper URDU SCRIPT (اردو), simple words, NOT Roman Urdu",
  "indeterminate": false
}"""

FOOD_DRUGS_BANNED = (
    "chloramphenicol", "nitrofuran", "furazolidone", "nitrofurazone", "furaltadone",
    "clenbuterol", "diethylstilbestrol", "stilbene", "metronidazole", "dimetridazole",
    "ronidazole", "dapsone",
)
CAT_UNSAFE_DRUGS = ("paracetamol", "acetaminophen", "permethrin")
IONOPHORES = ("monensin", "salinomycin", "lasalocid", "narasin", "maduramicin", "ionophore")
URGENCY_ORDER = ["Routine / monitor", "Within 48 hours", "Same day", "Emergency - vet now"]


# ----------------------------------------------------------------------------- knowledge base retrieval
def looks_like_declared_image(mime: str, data: bytes) -> bool:
    """Reject files whose real content does not match the declared image type."""
    if mime == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return True   # videos: content types are too varied to check reliably


def keyword_in_text(keyword: str, hay: str) -> bool:
    """Whole-word match (so short keywords like 'hs' or 'ib' never match inside other words)."""
    pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?:s|es)?(?![a-z0-9])"
    return re.search(pattern, hay) is not None


def match_entries(text: str, species_tags: set, limit: int = 4):
    """Return knowledge-base entries whose keywords appear in `text` and that apply to the species."""
    hay = (text or "").lower()
    scored = []
    for entry in KNOWLEDGE_BASE:
        hits = sum(1 for k in entry["keywords"] if keyword_in_text(k, hay))
        if not hits:
            continue
        applies = "all" in entry["species"] or (species_tags and species_tags & set(entry["species"]))
        if species_tags and not applies:
            continue
        # entries written specifically for the detected species rank first
        specific = 2 if (species_tags and set(entry["species"]) <= species_tags) else 0
        scored.append((hits * 2 + specific + (1 if applies else 0), entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:limit]]


def diagnosis_text(data: dict, focus_disease: str) -> str:
    parts = [str(data.get("primary_diagnosis", ""))]
    for d in data.get("differentials") or []:
        parts.append(str(d.get("name", "")) if isinstance(d, dict) else str(d))
    parts.append(focus_disease or "")
    return " | ".join(parts)


# ----------------------------------------------------------------------------- helpers
def to_float(value: str, low: float, high: float) -> Optional[float]:
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def extract_json(raw_text: str):
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def build_prompt(species, symptoms, focus_disease, age, temperature, duration, weight, n_files, is_video,
                 sex="", breed="", region="", bcs="") -> str:
    parts = [
        ("Examine the attached video" if is_video else f"Examine the {n_files} attached image(s) of the same animal")
        + " and produce the clinical report as JSON matching exactly this schema:\n"
        + JSON_SCHEMA_DESCRIPTION,
        "Requirements: at least 3 differentials when possible; every medicine must have frequency and "
        "withdrawal filled; confidence_percent is an integer 0-100 for how well the VISIBLE evidence supports "
        "the primary diagnosis.",
    ]
    history = []
    if species:
        history.append(f"species given by uploader: {species} (verify visually)")
    if breed:
        history.append(f"breed: {breed}")
    if sex:
        history.append(f"sex: {sex}")
    if age:
        history.append(f"age: {age}")
    if region:
        history.append(f"region/province: {region} (consider locally common diseases, but do not force them)")
    if weight is not None:
        history.append(f"body weight: {weight:g} kg")
    if bcs:
        history.append(f"owner-assessed body condition score: {bcs}")
    if temperature is not None:
        history.append(f"rectal temperature: {temperature:g} C")
    if duration:
        history.append(f"duration of illness: {duration}")
    if symptoms:
        history.append(f"owner-reported symptoms: {symptoms}")
    if history:
        parts.append("Clinical history (supporting context only): " + "; ".join(history) + ".")
    if focus_disease:
        parts.append(
            f"The uploader wants this case specifically screened for: {focus_disease}. State clearly how likely it "
            "is (and which visible signs support or oppose it), but still report any other condition you observe. "
            "Do not force this diagnosis."
        )
    return "\n\n".join(parts)


def _is_auth_error(exc: Exception) -> bool:
    """True only for errors that will fail identically on every model (a bad/blocked/missing API key), so
    retrying other models is pointless. Bare '401'/'403' are deliberately NOT matched here: Gemini also
    returns 403 for a model-specific permission problem (e.g. this key has no access to just one preview
    model), and in that case the fallback models genuinely can work - stopping early would break them for
    no reason. A real key problem virtually always also includes one of the phrases below."""
    text = str(exc).lower()
    return any(t in text for t in (
        "api key not valid", "api_key_invalid", "invalid api key", "api key expired",
        "unauthenticated", "permission_denied", "permission denied",
    ))


def generate_json(model_name: str, contents, system: str):
    """Call Gemini and parse JSON. Tries the fallback models if the first one is unavailable.
    Note: temperature/top_p/top_k are deprecated for the Gemini 3.x models, so they are not sent."""
    chain = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error = None
    for name in chain:
        try:
            response = client.models.generate_content(
                model=name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(response, "text", None) if response else None
            if text:
                return extract_json(text), text, name
            last_error = RuntimeError("empty response from " + name)
        except Exception as exc:
            last_error = exc
            if _is_auth_error(exc):
                logger.warning("Model %s failed with an auth/key error - not trying other models (they would "
                               "fail the same way). Check GEMINI_API_KEY.", name)
                break
            logger.warning("Model %s failed (%s); trying next fallback if any", name, type(exc).__name__)
    raise last_error if last_error else RuntimeError("no model available")


def generate_text(model_name: str, contents):
    """Plain-text Gemini call with the same fallback chain (used for speech-to-text)."""
    chain = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error = None
    for name in chain:
        try:
            response = client.models.generate_content(model=name, contents=contents)
            text = getattr(response, "text", None) if response else None
            if text is not None:
                return text
            last_error = RuntimeError("empty response from " + name)
        except Exception as exc:
            last_error = exc
            if _is_auth_error(exc):
                logger.warning("Model %s failed with an auth/key error - not trying other models. Check GEMINI_API_KEY.", name)
                break
            logger.warning("Model %s failed for transcription (%s); trying next fallback if any", name, type(exc).__name__)
    raise last_error if last_error else RuntimeError("no model available")


def run_critic(draft: dict, protocols: list, history_text: str):
    """Second-pass text-only review. Returns a corrected report or None (keep the draft)."""
    if not client:
        return None
    ref = "\n\n".join(f"- {p['name']}: {p['protocol']}" for p in protocols) or "(none matched)"
    prompt = (
        f"CLINICAL HISTORY: {history_text or 'not provided'}\n\n"
        f"REFERENCE PROTOCOLS:\n{ref}\n\n"
        f"DRAFT REPORT (JSON):\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        f"Return the corrected report as JSON with this schema:\n{JSON_SCHEMA_DESCRIPTION}"
    )
    try:
        revised, _, _ = generate_json(CRITIC_MODEL, [prompt], CRITIC_SYSTEM)
    except Exception:
        logger.warning("Critic pass failed; keeping the first-pass report", exc_info=True)
        return None
    if not isinstance(revised, dict):
        return None
    if not isinstance(revised.get("primary_diagnosis"), str) or not isinstance(revised.get("medicines"), list):
        return None
    # the critic never saw the images, so visual fields always come from the original examination
    for key in ("species_detected", "age_class", "body_condition", "image_quality",
                "clinical_findings", "not_assessable"):
        if key in draft:
            revised[key] = draft[key]
    return revised


def safety_review(data: dict, species_tags: set, weight: Optional[float], temperature: Optional[float],
                  primary_entries: list) -> dict:
    """Server-side guardrails applied on top of the model's answer."""
    notes = []

    # --- confidence calibration ---
    try:
        conf = int(round(float(data.get("confidence_percent", 0))))
    except (TypeError, ValueError):
        conf = 0
    conf = max(0, min(100, conf))
    if data.get("indeterminate"):
        conf = min(conf, 40)
    if conf > MAX_VISUAL_CONFIDENCE:
        conf = MAX_VISUAL_CONFIDENCE
        notes.append(
            f"Confidence capped at {MAX_VISUAL_CONFIDENCE}%: photos/video alone can never confirm a disease "
            "without examination or laboratory testing."
        )
    data["confidence_percent"] = conf

    if data.get("severity") not in ("Low", "Moderate", "High", "Critical"):
        data["severity"] = "Moderate"

    # --- species facts (detected species + what the user picked) ---
    detected = canonical_species(str(data.get("species_detected", "")))
    tags = detected | species_tags
    is_food_animal = bool(tags & FOOD_ANIMALS)
    is_cat = "cat" in tags

    # --- temperature assessment (code-based, not AI) ---
    if temperature is not None:
        for sp in ("camel", "cattle", "buffalo", "goat", "sheep", "horse", "donkey", "dog", "cat",
                   "poultry", "duck", "pig", "rabbit"):
            if sp in tags:
                low, high = NORMAL_TEMP_C[sp]
                if temperature > high:
                    status = f"ABOVE the typical {sp} range ({low}-{high} C): fever - suggests infection/inflammation or heat stress."
                elif temperature < low:
                    status = f"BELOW the typical {sp} range ({low}-{high} C): possible shock, hypothermia or measurement error."
                else:
                    status = f"within the typical {sp} range ({low}-{high} C)."
                data["temperature_assessment"] = f"Recorded {temperature:g} C is {status}"
                break

    # --- drug safety + code-computed total doses ---
    safe_meds = []
    for med in data.get("medicines") or []:
        if not isinstance(med, dict):
            continue
        name = str(med.get("name", "")).lower()
        if is_food_animal and any(b in name for b in FOOD_DRUGS_BANNED):
            notes.append(f"Removed '{med.get('name')}': prohibited in food-producing animals.")
            continue
        if is_cat and any(b in name for b in CAT_UNSAFE_DRUGS):
            notes.append(f"Removed '{med.get('name')}': toxic to cats.")
            continue
        if is_food_animal and not str(med.get("withdrawal", "")).strip():
            med["withdrawal"] = "Not stated - ask your vet before using milk/meat/eggs"
        if ("camel" in tags or "horse" in tags or "donkey" in tags) and any(i in name for i in IONOPHORES):
            notes.append(f"Removed '{med.get('name')}': ionophores are toxic to camels and horses.")
            continue

        per_kg = med.get("dose_mg_per_kg")
        try:
            per_kg = float(per_kg) if per_kg is not None else None
        except (TypeError, ValueError):
            per_kg = None
        if per_kg is not None and per_kg <= 0:
            per_kg = None
        med["dose_mg_per_kg"] = per_kg
        if per_kg is not None and weight is not None:
            med["total_dose_for_weight"] = (
                f"about {per_kg * weight:.4g} mg total for {weight:g} kg "
                "(check the product concentration to convert to ml)"
            )
        if HIDE_DOSES:
            med["dose"] = "Dose to be set by the veterinarian"
            med["dose_mg_per_kg"] = None
            med.pop("total_dose_for_weight", None)
        safe_meds.append(med)
    data["medicines"] = safe_meds
    if HIDE_DOSES:
        notes.append("Exact doses are hidden on this server: ask your veterinarian for the dose.")
    if any(m.get("dose_mg_per_kg") is not None for m in safe_meds) and weight is None:
        notes.append("Enter the animal's real body weight to get a calculated total dose. Never guess the weight of camels/cattle by eye.")

    # --- notifiable / zoonotic flags from the reference knowledge base ---
    notif = data.get("notifiable_suspected")
    if not isinstance(notif, dict):
        notif = {"suspected": False, "disease": "", "action": ""}
    zoo = data.get("zoonotic_risk")
    if not isinstance(zoo, dict):
        zoo = {"present": False, "notes": ""}
    for entry in primary_entries[:1]:
        if entry.get("notifiable") and not notif.get("suspected") and conf >= 30:
            notif = {"suspected": True, "disease": entry["name"],
                     "action": "Isolate the animal and contact the local animal-health authority."}
            notes.append(f"Reference check: {entry['name']} is usually a reportable disease.")
        if entry.get("zoonotic") and not zoo.get("present"):
            zoo = {"present": True, "notes": "This disease can infect humans - wear gloves/mask and wash hands after handling."}
    data["notifiable_suspected"] = notif
    data["zoonotic_risk"] = zoo

    if notif.get("suspected"):
        current = data.get("urgency", "")
        if current not in URGENCY_ORDER or URGENCY_ORDER.index(current) < URGENCY_ORDER.index("Same day"):
            data["urgency"] = "Same day"
        flags = data.get("red_flags") or []
        flags.insert(0, "Suspected notifiable disease - isolate the animal and contact the local animal-health authority.")
        data["red_flags"] = flags
    if data.get("urgency") not in URGENCY_ORDER:
        data["urgency"] = {"Critical": "Emergency - vet now", "High": "Same day",
                           "Moderate": "Within 48 hours", "Low": "Routine / monitor"}[data["severity"]]

    data["safety_notes"] = notes
    data.setdefault("disclaimer", DISCLAIMER)
    return data


def _lines(title, items, lines):
    items = [str(i) for i in (items or []) if i]
    if not items:
        return
    lines.append(title)
    for i in items:
        lines.append(f"   - {i}")
    lines.append("")


def format_report_text(d: dict) -> str:
    lines = ["DOCTORVET AI - EXAMINATION REPORT", ""]
    lines.append("1. PATIENT")
    lines.append(f"   Species: {d.get('species_detected', 'Not specified')} | Age: {d.get('age_class', 'unknown')}")
    lines.append(f"   Body condition: {d.get('body_condition', 'Not specified')}")
    lines.append(f"   Image quality: {d.get('image_quality', 'Not specified')}")
    if d.get("temperature_assessment"):
        lines.append(f"   Temperature: {d['temperature_assessment']}")
    lines.append("")
    _lines("2. VISIBLE CLINICAL FINDINGS", d.get("clinical_findings"), lines)
    _lines("   NOT ASSESSABLE FROM A PHOTO", d.get("not_assessable"), lines)

    lines.append("3. PRIMARY DIAGNOSIS")
    lines.append(f"   {d.get('primary_diagnosis', 'Indeterminate')}")
    lines.append(f"   Confidence: {d.get('confidence_percent', 0)}%")
    _lines("   Evidence for:", d.get("key_evidence"), lines)
    _lines("   Evidence against:", d.get("evidence_against"), lines)

    lines.append("4. DIFFERENTIAL DIAGNOSES")
    for x in d.get("differentials") or []:
        if isinstance(x, dict):
            lines.append(f"   - {x.get('name', '')} ({x.get('likelihood', '?')}): {x.get('reasoning', '')} "
                         f"[Differentiate by: {x.get('how_to_differentiate', '-')}]")
        else:
            lines.append(f"   - {x}")
    lines.append("")

    lines.append("5. SEVERITY & URGENCY")
    lines.append(f"   Severity: {d.get('severity', 'Moderate')}")
    lines.append(f"   Urgency: {d.get('urgency', '')}")
    if d.get("severity_reasoning"):
        lines.append(f"   Reasoning: {d['severity_reasoning']}")
    notif = d.get("notifiable_suspected") or {}
    if notif.get("suspected"):
        lines.append(f"   NOTIFIABLE DISEASE SUSPECTED: {notif.get('disease', '')} - {notif.get('action', '')}")
    zoo = d.get("zoonotic_risk") or {}
    if zoo.get("present"):
        lines.append(f"   ZOONOTIC RISK (can infect humans): {zoo.get('notes', '')}")
    lines.append("")

    _lines("6. IMMEDIATE ACTIONS", d.get("immediate_actions"), lines)

    lines.append("7. PRESCRIPTION (confirm every dose with a vet)")
    for m in d.get("medicines") or []:
        total = f" | Total: {m['total_dose_for_weight']}" if m.get("total_dose_for_weight") else ""
        lines.append(
            f"   - {m.get('name', '')} | Dose: {m.get('dose', '')}{total} | Route: {m.get('route', '')} | "
            f"Freq: {m.get('frequency', '')} | Duration: {m.get('duration', '')} | "
            f"Withdrawal: {m.get('withdrawal', '')} | {m.get('notes', '')}"
        )
    lines.append("")
    _lines("8. TREATMENT STEPS", d.get("treatment_steps"), lines)
    _lines("9. SUPPORTIVE CARE", d.get("supportive_care"), lines)
    _lines("10. CONFIRMATORY TESTS", d.get("confirmatory_tests"), lines)
    _lines("11. PREVENTION", d.get("prevention"), lines)
    if d.get("follow_up"):
        lines.append("12. FOLLOW-UP")
        lines.append(f"   {d['follow_up']}")
        lines.append("")
    _lines("13. SEE A VET URGENTLY IF", d.get("red_flags"), lines)
    _lines("14. INFORMATION THAT WOULD IMPROVE THIS ASSESSMENT", d.get("info_needed"), lines)
    if d.get("urdu_summary"):
        lines.append("15. KHULASA (ROMAN URDU)")
        lines.append(f"   {d['urdu_summary']}")
        lines.append("")
    if d.get("urdu_script_summary"):
        lines.append("15b. خلاصہ (URDU SCRIPT)")
        lines.append(f"   {d['urdu_script_summary']}")
        lines.append("")
    refs = d.get("reference_protocols") or []
    if refs:
        lines.append("16. BUILT-IN REFERENCE PROTOCOLS (general guidance - vet to confirm)")
        for r in refs:
            lines.append(f"   - {r.get('name', '')}: {r.get('protocol', '')}")
        lines.append("")
    _lines("SAFETY NOTES", d.get("safety_notes"), lines)
    v = d.get("verification") or {}
    if v:
        lines.append(f"Verification: images analysed = {v.get('images_analyzed')}, second-pass safety review = "
                     f"{'done' if v.get('critic_applied') else 'not applied'}")
    lines.append("DISCLAIMER: " + d.get("disclaimer", DISCLAIMER))
    return "\n".join(lines)


# ----------------------------------------------------------------------------- routes
def _static_file(name: str, media_type: str, no_cache: bool = False, extra_headers: Optional[dict] = None):
    path = os.path.join(BASE_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"{name} not found on the server.")
    headers = dict(extra_headers or {})
    if no_cache:
        headers["Cache-Control"] = "no-cache"
    return FileResponse(path, media_type=media_type, headers=headers)


@app.get("/")
def home():
    """Serves the app itself, so one https link = app + backend (no separate hosting needed)."""
    if os.path.isfile(os.path.join(BASE_DIR, "index.html")):
        return _static_file("index.html", "text/html", no_cache=True)
    return {"status": "success", "message": "DoctorVet AI Backend is running successfully!", "version": VERSION}


@app.get("/manifest.json")
def pwa_manifest():
    return _static_file("manifest.json", "application/manifest+json", no_cache=True)


@app.get("/sw.js")
def pwa_service_worker():
    return _static_file("sw.js", "application/javascript", no_cache=True,
                        extra_headers={"Service-Worker-Allowed": "/"})


@app.get("/icon-192.png")
def pwa_icon_192():
    return _static_file("icon-192.png", "image/png")


@app.get("/icon-512.png")
def pwa_icon_512():
    return _static_file("icon-512.png", "image/png")


MAX_AUDIO_BYTES = 6 * 1024 * 1024
LANGUAGE_HINTS = {
    "ur": "Urdu", "ur-PK": "Urdu", "ps": "Pashto", "ps-AF": "Pashto", "hi": "Hindi", "hi-IN": "Hindi",
    "en": "English", "en-IN": "English", "en-US": "English", "pa": "Punjabi", "pa-PK": "Punjabi",
}


@app.post("/api/v1/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("ur-PK"),
    x_access_code: str = Header(default=""),
):
    """Speech-to-text for the symptoms box. Works in any browser that can record audio."""
    if ACCESS_CODE and not hmac.compare_digest(x_access_code.encode(), ACCESS_CODE.encode()):
        raise HTTPException(status_code=401, detail="Access code is missing or wrong.")
    check_rate_limit(request)
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API client is not initialized on the server.")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="No audio was received.")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Recording is too long. Please keep it under 30 seconds.")
    if not (data[:4] == b"RIFF" and data[8:12] == b"WAVE"):
        raise HTTPException(status_code=400, detail="Unsupported audio format (expected WAV).")

    hint = LANGUAGE_HINTS.get(language.strip(), "Urdu")
    prompt = (
        "Transcribe the speech in this audio exactly as spoken. The speaker is describing the symptoms of a sick "
        "animal. The language is most likely " + hint + " but may also be Urdu, Pashto, Punjabi, Hindi or English. "
        "Write Urdu and Pashto speech in its own script, Hindi in Devanagari or Urdu script, and English in English "
        "letters. Do NOT translate, summarise or answer. Output only the transcript text. "
        "If there is no clear speech, output nothing."
    )
    try:
        text = generate_text(MODEL_NAME, [types.Part.from_bytes(data=data, mime_type="audio/wav"), prompt])
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=friendly_ai_error(e))

    return {"status": "success", "text": (text or "").strip()[:500]}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_configured": client is not None,
        "model": MODEL_NAME,
        "fallback_models": FALLBACK_MODELS,
        "doses_hidden": HIDE_DOSES,
        "critic_enabled": CRITIC_ENABLED,
        "knowledge_base_entries": len(KNOWLEDGE_BASE),
        "access_code_required": bool(ACCESS_CODE),
        "version": VERSION,
        "note": "If gemini_configured is true but every diagnose call still fails with an auth error, your "
                "GEMINI_API_KEY is likely an old 'standard' key that Google has blocked - generate a fresh key "
                "in Google AI Studio (new keys are 'auth keys' by default).",
    }


@app.post("/api/v1/diagnose")
async def diagnose_animal(
    request: Request,
    files: List[UploadFile] = File(default=[]),
    file: Optional[UploadFile] = File(default=None),  # legacy single-file field
    species: str = Form(""),
    symptoms: str = Form(""),
    focus_disease: str = Form(""),
    age: str = Form(""),
    temperature: str = Form(""),
    duration: str = Form(""),
    weight_kg: str = Form(""),
    bcs: str = Form(""),
    sex: str = Form(""),
    breed: str = Form(""),
    region: str = Form(""),
    x_access_code: str = Header(default=""),
):
    if ACCESS_CODE and not hmac.compare_digest(x_access_code.encode(), ACCESS_CODE.encode()):
        raise HTTPException(status_code=401, detail="Access code is missing or wrong. Ask the app owner for the code and enter it under Backend Connection.")
    check_rate_limit(request)
    if not client:
        raise HTTPException(
            status_code=500,
            detail="Gemini API client is not initialized. Check your GEMINI_API_KEY environment variable.",
        )

    uploads = [f for f in (files or []) if f is not None and f.filename != ""]
    if file is not None and file.filename != "":
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="Please upload at least one image or a video.")

    for f in uploads:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {f.content_type}. Please upload valid images or a video.",
            )
    videos = [f for f in uploads if f.content_type in VIDEO_TYPES]
    if videos and len(uploads) > 1:
        raise HTTPException(status_code=400, detail="Send either up to 4 images OR a single video - not both.")
    if len(uploads) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Too many files. Send at most {MAX_IMAGES} images.")

    parts = []
    total = 0
    for f in uploads:
        try:
            data = await f.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read the uploaded file: {e}")
        if not data:
            raise HTTPException(status_code=400, detail=f"The file '{f.filename}' is empty.")
        if not looks_like_declared_image(f.content_type, data):
            raise HTTPException(status_code=400, detail=f"'{f.filename}' is not a valid {f.content_type} image.")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Files too large (over {MAX_TOTAL_BYTES / (1024 * 1024):.0f} MB total). "
                       f"Use fewer or smaller photos.",
            )
        parts.append(types.Part.from_bytes(data=data, mime_type=f.content_type))

    species = species.strip()[:60]
    symptoms = symptoms.strip()[:300]
    focus_disease = focus_disease.strip()[:100]
    age = age.strip()[:40]
    duration = duration.strip()[:60]
    temp_c = to_float(temperature, 30, 46)
    weight = to_float(weight_kg, 0.1, 1500)
    species_tags = canonical_species(species)

    sex = sex.strip()[:20]
    breed = breed.strip()[:60]
    region = region.strip()[:60]
    bcs = bcs.strip()[:120]

    prompt = build_prompt(species, symptoms, focus_disease, age, temp_c, duration, weight,
                          len(uploads), bool(videos), sex, breed, region, bcs)

    # ---- pass 1: clinical examination ----
    try:
        structured, raw_text, used_model = generate_json(MODEL_NAME, parts + [prompt], SYSTEM_INSTRUCTION)
    except Exception as e:
        logger.exception("Gemini analysis failed")
        raise HTTPException(status_code=500, detail=friendly_ai_error(e))

    if not isinstance(structured, dict):
        if not raw_text:
            raise HTTPException(status_code=500, detail="AI model failed to generate a response.")
        return {
            "status": "success",
            "filename": uploads[0].filename,
            "species": species or "auto-detected",
            "focus": focus_disease or None,
            "structured": None,
            "diagnosis_report": raw_text.strip() + "\n\nDISCLAIMER: " + DISCLAIMER,
        }

    tags_for_kb = species_tags | canonical_species(str(structured.get("species_detected", "")))
    protocols = match_entries(diagnosis_text(structured, focus_disease), tags_for_kb)

    # ---- pass 2: critic / verification (text only, cheap) ----
    critic_applied = False
    if CRITIC_ENABLED:
        history_bits = [x for x in (species, age, f"{weight:g} kg" if weight else "",
                                    f"{temp_c:g} C" if temp_c is not None else "", duration, symptoms) if x]
        revised = run_critic(structured, protocols, "; ".join(history_bits))
        if revised:
            structured = revised
            critic_applied = True
            protocols = match_entries(diagnosis_text(structured, focus_disease), tags_for_kb)

    primary_entries = match_entries(str(structured.get("primary_diagnosis", "")), tags_for_kb, limit=1)

    # ---- pass 3: deterministic safety layer ----
    structured = safety_review(structured, species_tags, weight, temp_c, primary_entries)
    structured["reference_protocols"] = [
        {"name": p["name"], "notifiable": p["notifiable"], "zoonotic": p["zoonotic"], "protocol": p["protocol"]}
        for p in protocols
    ]
    structured["verification"] = {
        "images_analyzed": len(uploads),
        "critic_applied": critic_applied,
        "model": used_model,
    }

    return {
        "status": "success",
        "filename": uploads[0].filename,
        "species": species or "auto-detected",
        "focus": focus_disease or None,
        "structured": structured,
        "diagnosis_report": format_report_text(structured),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(status_code=500, content={"detail": "Server error. Please try again."})

# Run locally (keep main.py and knowledge_base.py in the same folder):
# 1. pip install fastapi uvicorn google-genai python-multipart      (optional: python-dotenv)
# 2. export GEMINI_API_KEY="your_api_key_here"
#    optional: export GEMINI_MODEL=<another model id from Google AI Studio's model list>
#    optional: export DOCTORVET_HIDE_DOSES=1          (public apps: leave exact doses to the vet)
#    optional: export DOCTORVET_CRITIC=0              (turn off the second-pass review for max speed)
# 3. uvicorn main:app --reload
