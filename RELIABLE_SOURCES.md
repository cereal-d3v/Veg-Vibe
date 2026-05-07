# Veg Vibe: Reliable Vegan Grounding Pipeline

## Overview

This document describes Veg Vibe's **multi-source verified data pipeline** that implements the "reliable interface" requirement for agentic AI systems. By constraining AI creativity with hard data from authoritative sources, we prevent hallucination about dietary claims.

---

## Architecture: The Two-Step Verification Pattern

### Step A: Query (Search Recipes)
The user asks: **"High protein quick vegan recipes"**

```
User Query
    ↓
[search_recipes tool]
    ↓
TF-IDF Semantic Search (Vector DB)
    ↓
Initial Results: [Recipe 1, Recipe 2, Recipe 3, ...]
```

### Step B: Verify (External APIs)
Before recommending **ANY** recipe, the agent triggers verification:

```
Retrieved Recipes
    ↓
[verify_recipe_ingredients tool] (Agentic Tool Use)
    ├── Check against PETA Animal-Derived Ingredients List
    ├── Query USDA FoodData Central for nutritional grounding
    └── Query Open Food Facts for branded product verification
    ↓
Verification Results: {status, confidence, evidence}
    ↓
Filter: Only recipes with status="verified_vegan" AND confidence > 0.7
    ↓
Safe Results: [✅ Recipe A, ✅ Recipe C]  (Recipe B rejected: contains honey)
```

---

## External Data Sources

### 1. **USDA FoodData Central** (Grounding Tool)

**Purpose**: Provides the "Source of Truth" for nutritional claims  
**Role**: Prevents LLM hallucinations about health/nutrition  

**Data Structure**:
- Food name → nutrient values (protein, carbs, vitamins, minerals)
- 100+ macronutrients and micronutrients per food
- Community-verified data from USDA

**Integration**:
```python
from app.services.data_fetcher import USDADataFetcher

usda = USDADataFetcher(api_key="...")
nutrients = usda.get_nutrient_values("tofu", nutrients=["Protein", "Iron"])
# Returns: {"Protein": 15.7, "Iron": 1.8}
```

**How It Prevents Hallucination**:
- When user asks for "high protein" recipes, we verify actual protein content
- Example: If LLM claims "this recipe has 50g protein" but USDA data shows 15g, we correct it

**Setup**:
1. Get free API key: https://fdc.nal.usda.gov/
2. Set `USDA_API_KEY` in `.env`

---

### 2. **Open Food Facts** (Verification Tool)

**Purpose**: Verifies if branded products are actually vegan  
**Role**: Prevents confusion about borderline products (like certain vegan meats)

**Data Structure**:
- Product name → vegan status, ingredients, labels
- Community-maintained database of real-world products
- No API key required (rate-limited but free)

**Integration**:
```python
from app.services.data_fetcher import OpenFoodFactsFetcher

off = OpenFoodFactsFetcher()
is_vegan, reason = off.is_product_vegan("Oatly Barista Edition")
# Returns: (True, "Marked as vegan in Open Food Facts")
```

**How It Prevents Hallucination**:
- Some products are ambiguous (e.g., certain plant-based meats contain trace animal products)
- We cross-reference branded ingredients with the real-world database
- Example: If a recipe uses "Casein-free milk alternative," we verify it's actually vegan

**Setup**:
- No setup needed! Open API: https://world.openfoodfacts.org/api

---

### 3. **PETA Animal-Derived Ingredients List** (Hard-Coded Filter)

**Purpose**: Prevents categorization of animal products as vegan  
**Role**: Hard-coded "rules" that override fuzzy ingredient classification

**Embedded List** (from https://www.peta.org/living/food/animal-derived-ingredients/):

```python
ANIMAL_DERIVED_INGREDIENTS = {
    # Dairy
    "milk", "cheese", "whey", "casein", "lactose", "butter", "cream",
    # Eggs
    "egg", "eggs", "albumin", "mayonnaise", 
    # Meat
    "meat", "beef", "pork", "chicken", "fish", "seafood",
    # Honey
    "honey", "propolis", "royal jelly",
    # Other
    "gelatin", "collagen", "lard", "lanolin", "carmine",
}
```

**Integration**:
```python
from app.services.data_fetcher import VeganIngredientVerifier

verifier = VeganIngredientVerifier(usda_fetcher, off_fetcher)
is_vegan, evidence = verifier.is_ingredient_vegan("honey")
# Returns: (False, ["❌ PETA animal-derived list: 'honey' contains 'honey'"])
```

**Why This Matters**:
- LLMs are trained on noisy data (some training data incorrectly classifies honey as vegan)
- Hard-coded filter provides ground truth that cannot be overridden by model weights
- This is the "reliable interface" that constrains AI creativity

---

## System Prompt: Enforcing Reliability

The LLM must follow these **CRITICAL RELIABILITY RULES** (in `backend/app/prompts.py`):

```
1. **Verification Requirement**: You MUST NOT suggest a recipe unless its 
   primary ingredients have been verified against the Verification Tool.

2. **Tool Use Authority**: The Verification Tool calls external APIs:
   - USDA FoodData Central (nutritional authority)
   - Open Food Facts (product vegan status)
   - PETA Animal-Derived Ingredients List (hard-coded filter)

3. **Failure Handling**: If the Verification Tool fails:
   - IMMEDIATELY inform user: "I cannot verify the vegan status at this moment."
   - Do NOT recommend the recipe without verification
   - Suggest alternative verified options

4. **Transparency**: Explain WHY a recipe was rejected:
   - Example: "❌ This recipe contains honey [animal-derived], which is not vegan"
   - Example: "⚠️ Contains ingredients we cannot verify; manual review needed"
```

---

## Verification Pipeline: Code Example

### From `backend/app/services/verification_agent.py`

```python
def verify_recipe_ingredients(
    recipe_id: int,
    recipe_title: str,
    ingredients_list: List[str],
) -> VerificationResult:
    """
    Main verification function called in Step B of the two-step pattern.
    
    This is the core "tool use" that constrains the LLM's creativity 
    with hard data from external sources.
    """
    # Step 1: Quick check against PETA list
    for ingredient in ingredients_list:
        for animal_ingredient in ANIMAL_DERIVED_INGREDIENTS:
            if animal_ingredient in ingredient.lower():
                return VerificationResult(
                    status=VerificationStatus.CONTAINS_ANIMAL_DERIVED,
                    reason_for_rejection=f"Contains {animal_ingredient}"
                )
    
    # Step 2: Deep verification with external APIs
    all_vegan, report = self.verifier.verify_recipe_ingredients(ingredients_list)
    
    # Step 3: Apply confidence threshold
    if report["confidence_score"] >= 0.7:
        return VerificationResult(status=VerificationStatus.VERIFIED_VEGAN)
    else:
        return VerificationResult(
            status=VerificationStatus.CONTAINS_UNKNOWN,
            reason_for_rejection="Insufficient confidence"
        )
```

---

## API Response: Transparency Through Evidence

When a user queries `/api/agent/query`, the response includes:

```json
{
  "answer": "🥬 **Veg Vibe Verified Results**...",
  "citations": [12, 45, 78],
  "retrieved_count": 10,
  "verified_vegan_count": 5,
  "verification_results": [
    {
      "recipe_id": 12,
      "recipe_title": "Tofu Scramble",
      "status": "verified_vegan",
      "confidence": 0.95,
      "is_safe": true
    },
    {
      "recipe_id": 45,
      "recipe_title": "Honey Oat Cookies",
      "status": "contains_animal_derived",
      "confidence": 0.0,
      "is_safe": false
    }
  ],
  "verification_stats": {
    "total_verifications": 10,
    "failed_verifications": 0,
    "success_rate": "100.0%"
  }
}
```

**Key Fields**:
- `verified_vegan_count`: How many recipes actually passed verification
- `verification_results`: Detailed status for each recipe
- `verification_stats`: Overall system health metrics

---

## Bootstrap: Dataset Setup

### `scripts/setup_verified_data.py`

This script bootstraps Veg Vibe with a high-quality verified dataset:

```bash
# Download and filter recipes from HuggingFace
python scripts/setup_verified_data.py \
    --output-path backend/vegan_recipes_verified.csv \
    --dataset datahiveai/recipes-with-nutrition

# Processing:
# - Loads ~100k recipes from HuggingFace
# - Filters for strictly vegan recipes
# - Checks against PETA ingredient list
# - Verifies with USDA nutritional data
# - Exports verified subset to CSV
```

**Output**:
```
📈 DATASET PROCESSING STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total recipes processed:        100000
Verified vegan recipes:         43521
Non-vegan recipes rejected:     52147
Unverifiable recipes:           4332
Recipes exported to CSV:        43521
Vegan percentage:               43.5%
```

---

## Why This Addresses "Reliability" (Turing Question 4)

| Challenge | Veg Vibe Solution | Turing Application Benefit |
|-----------|------------------|--------------------------|
| **LLM hallucination about health claims** | USDA FoodData Central provides authoritative nutrient data | "Our system can prove what it claims" |
| **Confusion about edge-case products** | Open Food Facts cross-references real-world vegan status | "We verify against community consensus" |
| **Ambiguous ingredient classification** | PETA hard-coded list overrides fuzzy classification | "Hard constraints that cannot be hallucinated away" |
| **No auditability** | Every recommendation includes verification evidence trail | "Users can see why each recipe was recommended" |
| **Tool reliability unknown** | Verification stats tracked and returned to user | "System health metrics visible to user" |
| **Single point of failure** | Three independent data sources (USDA + Open Food Facts + PETA) | "Fail-gracefully with multiple fallbacks" |

---

## Key Insight: Tool Use as Reliability

This architecture demonstrates **tool use as a reliability mechanism**, not just a convenience:

- **Without verification**: LLM might recommend honey-based recipes as "vegan" (hallucination)
- **With verification**: Even if LLM is confused, the `verify_recipe_ingredients` tool will catch it

The tool acts as a **guardrail** that constrains the LLM's behavior to ground truth.

---

## Files Overview

```
backend/
├── app/
│   ├── services/
│   │   ├── data_fetcher.py          # External API integrations
│   │   └── verification_agent.py     # Two-step verification logic
│   ├── utils/
│   │   └── agentic_rag.py            # Updated with verification
│   ├── prompts.py                    # Reliability-focused system prompts
│   ├── main.py                       # Service initialization
│   └── models/recipe.py              # Extended with verification fields
├── .env.example                      # API key configuration template
└── requirements.txt                  # Added: requests, datasets, tenacity

scripts/
└── setup_verified_data.py            # Bootstrap dataset setup
```

---

## Getting Started

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up API Keys
```bash
cp .env.example .env
# Edit .env and add USDA_API_KEY from https://fdc.nal.usda.gov/
```

### 3. Bootstrap Dataset (Optional)
```bash
python scripts/setup_verified_data.py
```

### 4. Run Backend
```bash
python -m uvicorn app.main:app --reload
```

### 5. Test Verification Pipeline
```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "high protein quick vegan recipes", "max_results": 5}'
```

---

## Monitoring & Debugging

### Check Verification Statistics
```python
from app.services.data_fetcher import get_verifier

verifier = get_verifier()
print(verifier._verification_cache)  # See cached verifications
```

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

### Test Individual Verifications
```python
from app.services.verification_agent import TwoStepVerificationAgent

agent = TwoStepVerificationAgent()
result = agent.verify_recipe_ingredients(
    recipe_id=1,
    recipe_title="Vegan Pasta",
    ingredients_list=["pasta", "tomato", "olive oil"]
)
print(f"Safe: {result.is_safe_to_recommend()}")
print(f"Evidence: {result.evidence}")
```

---

## Future Enhancements

- [ ] Cache USDA/Open Food Facts responses in PostgreSQL
- [ ] Add more nutrient verification (B12, iron, etc.)
- [ ] Integration with Allergen databases
- [ ] User feedback loop to improve confidence scores
- [ ] Multi-language ingredient support
- [ ] Batch verification API for performance
