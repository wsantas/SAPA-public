"""Homestead gap analysis target knowledge areas.

Family-shared (not per-profile). Four main domains:
Gardening, Goats, Chickens, Water Capture.
"""

HOMESTEAD_GAP_TARGETS = {
    # ============== Gardening ==============
    "Soil Health & Amendments": {
        "priority": "critical",
        "topics": ["soil testing", "ph level", "compost", "composting", "vermicompost", "worm casting", "mulch", "cover crop", "green manure", "biochar", "organic matter", "amendments", "no-till", "hugelkultur", "mycorrhizae", "nitrogen fixing"]
    },
    "Garden Planning & Layout": {
        "priority": "critical",
        "topics": ["garden planning", "raised bed", "companion planting", "crop rotation", "succession planting", "square foot gardening", "permaculture", "food forest", "zone planning", "garden map", "bed layout", "row spacing"]
    },
    "Seed Starting & Propagation": {
        "priority": "high",
        "topics": ["seed starting", "germination", "seedling", "transplant", "hardening off", "direct sow", "seed saving", "propagation", "cuttings", "grafting", "cold stratification", "seed viability"]
    },
    "Season Extension": {
        "priority": "high",
        "topics": ["greenhouse", "hoop house", "cold frame", "row cover", "frost protection", "season extension", "winter gardening", "microclimate", "shade cloth", "polytunnel", "heat mat", "grow light"]
    },
    "Vegetable Production": {
        "priority": "critical",
        "topics": ["tomato", "pepper", "squash", "cucumber", "beans", "peas", "corn", "potato", "garlic", "onion", "carrot", "beet", "lettuce", "kale", "spinach", "broccoli", "cabbage", "melon", "pumpkin"]
    },
    "Herbs & Perennials": {
        "priority": "medium",
        "topics": ["basil", "cilantro", "dill", "parsley", "rosemary", "thyme", "sage", "oregano", "mint", "lavender", "chives", "lemon balm", "chamomile", "echinacea", "comfrey", "asparagus", "rhubarb"]
    },
    "Fruit & Orchard": {
        "priority": "high",
        "topics": ["fruit tree", "apple tree", "peach tree", "pear tree", "cherry tree", "plum tree", "pruning", "grafting", "rootstock", "berry", "strawberry", "blueberry", "raspberry", "blackberry", "grape", "vineyard", "pollination", "thinning"]
    },
    "Pest & Disease Management": {
        "priority": "high",
        "topics": ["pest control", "integrated pest management", "ipm", "beneficial insect", "companion planting", "organic spray", "neem oil", "bt", "diatomaceous earth", "blight", "mildew", "fungus", "rot", "wilt", "aphid", "hornworm", "squash bug", "deer fence", "row cover"]
    },
    "Harvest & Preservation": {
        "priority": "high",
        "topics": ["harvest", "canning", "pressure canning", "water bath", "pickling", "fermentation", "dehydrating", "freeze drying", "vacuum seal", "root cellar", "food storage", "preserving", "jam", "jelly", "salsa", "sauce", "dried herbs", "smoking", "curing"]
    },

    # ============== Goats ==============
    "Goat Breeds & Selection": {
        "priority": "high",
        "topics": ["dairy goat", "meat goat", "nigerian dwarf", "nubian", "alpine", "lamancha", "saanen", "boer", "kiko", "pygmy", "breed selection", "registered goat", "goat purchase"]
    },
    "Goat Housing & Fencing": {
        "priority": "critical",
        "topics": ["goat shelter", "goat barn", "goat fencing", "electric fence", "woven wire", "cattle panel", "goat pen", "kidding pen", "buck housing", "predator protection", "ventilation", "bedding", "straw"]
    },
    "Goat Nutrition & Feeding": {
        "priority": "critical",
        "topics": ["goat feed", "hay", "alfalfa", "browse", "grain", "mineral", "loose mineral", "copper bolus", "selenium", "baking soda", "goat nutrition", "body condition score", "feeding schedule", "pasture management"]
    },
    "Goat Health & Veterinary": {
        "priority": "critical",
        "topics": ["goat health", "hoof trimming", "deworming", "famacha", "coccidia", "cdt vaccine", "bloat", "ketosis", "mastitis", "pneumonia", "caseous lymphadenitis", "cl", "johnes", "cae", "parasite", "fecal test", "body temperature", "goat first aid"]
    },
    "Goat Breeding & Kidding": {
        "priority": "high",
        "topics": ["kidding", "breeding", "heat cycle", "buck", "doe", "gestation", "kidding kit", "dystocia", "kid care", "bottle feeding", "colostrum", "disbudding", "castration", "weaning", "breeding season"]
    },
    "Goat Milking & Dairy": {
        "priority": "high",
        "topics": ["milking", "milk stand", "milking routine", "udder health", "milk storage", "pasteurization", "raw milk", "cheese making", "goat cheese", "soap making", "goat milk soap", "milk yield", "drying off"]
    },

    # ============== Chickens ==============
    "Chicken Breeds & Selection": {
        "priority": "high",
        "topics": ["layer", "broiler", "dual purpose", "rhode island red", "plymouth rock", "orpington", "australorp", "leghorn", "wyandotte", "easter egger", "ameraucana", "silkie", "breed selection", "chick purchase", "hatchery"]
    },
    "Coop Design & Setup": {
        "priority": "critical",
        "topics": ["chicken coop", "nesting box", "roost", "ventilation", "coop size", "run", "chicken run", "predator proofing", "hardware cloth", "coop bedding", "deep litter", "coop cleaning", "automatic door", "pop door"]
    },
    "Chicken Feeding & Nutrition": {
        "priority": "critical",
        "topics": ["layer feed", "chick starter", "grower feed", "scratch grain", "oyster shell", "grit", "kitchen scraps", "fermented feed", "fodder", "free range", "chicken treats", "protein supplement", "mealworm"]
    },
    "Egg Production & Management": {
        "priority": "critical",
        "topics": ["egg production", "egg laying", "egg collection", "egg storage", "egg washing", "bloom", "broody hen", "incubation", "candling", "hatching", "pullet", "point of lay", "molting", "light supplementation", "winter laying"]
    },
    "Chicken Health": {
        "priority": "high",
        "topics": ["chicken health", "respiratory", "bumblefoot", "mites", "lice", "worms", "coccidiosis", "mareks", "avian flu", "chicken first aid", "electrolytes", "apple cider vinegar", "dust bath", "quarantine", "biosecurity"]
    },
    "Chick Raising": {
        "priority": "high",
        "topics": ["brooder", "heat lamp", "chick care", "brooder temperature", "pasty butt", "chick waterer", "chick feeder", "integration", "pecking order", "socializing chicks"]
    },

    # ============== Water Capture ==============
    "Rainwater Harvesting": {
        "priority": "critical",
        "topics": ["rain barrel", "rainwater harvesting", "cistern", "first flush diverter", "roof catchment", "gutter", "downspout", "collection area", "rainfall calculation", "storage tank", "ibc tote", "water quality"]
    },
    "Water Storage & Distribution": {
        "priority": "critical",
        "topics": ["water storage", "water tank", "pressure tank", "pump", "gravity fed", "distribution", "plumbing", "overflow", "filtration", "uv sterilization", "sediment filter", "water treatment"]
    },
    "Irrigation Systems": {
        "priority": "high",
        "topics": ["drip irrigation", "soaker hose", "irrigation timer", "sprinkler", "micro irrigation", "emitter", "irrigation layout", "water pressure", "backflow preventer", "zone irrigation", "irrigation scheduling"]
    },
    "Earthworks & Drainage": {
        "priority": "high",
        "topics": ["swale", "french drain", "grading", "drainage", "berm", "rain garden", "dry creek bed", "retention pond", "infiltration", "erosion control", "terracing", "keyline design", "contour"]
    },
    "Greywater & Conservation": {
        "priority": "medium",
        "topics": ["greywater", "water conservation", "mulching", "drought tolerant", "xeriscaping", "ollas", "wicking bed", "hugelkultur", "water audit", "leak detection", "low flow", "reuse"]
    },
}
