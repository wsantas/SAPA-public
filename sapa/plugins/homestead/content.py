"""Content extraction helpers for homestead sessions."""

import re


def extract_title_from_content(content: str) -> str | None:
    """Extract title from first H1 heading in markdown."""
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_topics_from_content(content: str) -> list[str]:
    """Extract homestead-related topics from content."""
    topics = set()

    terms = [
        # Garden & Soil
        'garden', 'gardening', 'raised bed', 'raised beds', 'soil', 'soil testing',
        'compost', 'composting', 'mulch', 'mulching', 'topsoil', 'amendments',
        'ph level', 'fertilizer', 'organic matter', 'no-till', 'hugelkultur',
        'permaculture', 'cover crop', 'green manure', 'worm casting', 'vermicompost',
        'biochar', 'mycorrhizae', 'nitrogen fixing',
        # Planting & Growing
        'planting', 'transplant', 'seedling', 'seeds', 'germination', 'propagation',
        'hardening off', 'direct sow', 'succession planting', 'companion planting',
        'crop rotation', 'growing season', 'frost date', 'last frost', 'first frost',
        'zone', 'hardiness zone', 'cold frame', 'row cover', 'season extension',
        'square foot gardening', 'zone planning', 'garden planning', 'garden map',
        'bed layout', 'row spacing', 'seed starting', 'seed saving', 'seed viability',
        'cold stratification', 'cuttings', 'grafting',
        # Greenhouse & Structures
        'greenhouse', 'hoop house', 'cold frame', 'polytunnel', 'shade cloth',
        'frost protection', 'winter gardening', 'microclimate', 'heat mat', 'grow light',
        # Harvest & Preservation
        'harvest', 'harvesting', 'canning', 'preserving', 'preservation', 'fermentation',
        'dehydrating', 'freeze drying', 'pickling', 'smoking', 'curing', 'root cellar',
        'food storage', 'vacuum seal', 'water bath', 'pressure canning', 'jam', 'jelly',
        'salsa', 'sauce', 'dried herbs',
        # Irrigation & Water
        'irrigation', 'drip irrigation', 'soaker hose', 'rain barrel', 'rainwater',
        'rainwater harvesting', 'water catchment', 'swale', 'french drain', 'well',
        'cistern', 'watering', 'first flush diverter', 'roof catchment', 'gutter',
        'downspout', 'collection area', 'rainfall calculation', 'storage tank',
        'ibc tote', 'water quality', 'water storage', 'water tank', 'pressure tank',
        'pump', 'gravity fed', 'distribution', 'overflow', 'filtration',
        'uv sterilization', 'sediment filter', 'water treatment', 'irrigation timer',
        'sprinkler', 'micro irrigation', 'emitter', 'irrigation layout',
        'water pressure', 'backflow preventer', 'zone irrigation',
        'irrigation scheduling',
        # Earthworks & Drainage
        'berm', 'rain garden', 'dry creek bed', 'retention pond', 'infiltration',
        'erosion control', 'terracing', 'keyline design', 'contour',
        # Greywater & Conservation
        'greywater', 'water conservation', 'drought tolerant', 'xeriscaping', 'ollas',
        'wicking bed', 'water audit', 'leak detection', 'low flow', 'reuse',
        # Specific Crops
        'tomato', 'pepper', 'squash', 'zucchini', 'cucumber', 'beans', 'peas',
        'corn', 'potato', 'sweet potato', 'garlic', 'onion', 'carrot', 'beet',
        'lettuce', 'kale', 'spinach', 'chard', 'cabbage', 'broccoli', 'cauliflower',
        'melon', 'watermelon', 'pumpkin', 'herb', 'basil', 'cilantro', 'dill',
        'parsley', 'rosemary', 'thyme', 'sage', 'oregano', 'mint', 'lavender',
        'chives', 'lemon balm', 'chamomile', 'echinacea', 'comfrey',
        'asparagus', 'rhubarb',
        'berry', 'strawberry', 'blueberry', 'raspberry', 'blackberry',
        'fruit tree', 'apple tree', 'peach tree', 'pear tree', 'cherry tree',
        'plum tree', 'grape', 'vineyard', 'pruning', 'rootstock', 'pollination',
        'thinning',
        # Chickens — Breeds
        'chicken', 'chickens', 'hen', 'rooster', 'pullet', 'chick', 'broiler',
        'layer', 'dual purpose', 'rhode island red', 'plymouth rock', 'orpington',
        'australorp', 'leghorn', 'wyandotte', 'easter egger', 'ameraucana', 'silkie',
        'breed selection', 'chick purchase', 'hatchery',
        # Chickens — Housing
        'coop', 'chicken coop', 'nesting box', 'roost', 'chicken run', 'run',
        'predator proofing', 'hardware cloth', 'coop bedding', 'deep litter',
        'coop cleaning', 'coop size', 'automatic door', 'pop door', 'ventilation',
        # Chickens — Feeding
        'layer feed', 'chick starter', 'grower feed', 'scratch grain', 'oyster shell',
        'grit', 'kitchen scraps', 'fermented feed', 'fodder', 'free range',
        'chicken treats', 'protein supplement', 'mealworm',
        # Chickens — Eggs
        'egg production', 'egg laying', 'laying pattern', 'egg collection', 'collecting eggs',
        'egg storage', 'egg washing', 'washing eggs', 'bloom',
        'broody hen', 'broodiness', 'incubation', 'incubator', 'candling', 'hatching',
        'point of lay', 'molting', 'molt', 'light supplementation', 'supplemental light',
        'supplemental lighting', 'winter laying', 'winter eggs',
        # Chickens — Health
        'chicken health', 'respiratory', 'bumblefoot', 'mites', 'lice', 'worms',
        'coccidiosis', 'mareks', 'avian flu', 'chicken first aid', 'electrolytes',
        'apple cider vinegar', 'dust bath', 'quarantine', 'biosecurity',
        # Chick Raising
        'brooder', 'heat lamp', 'chick care', 'brooder temperature', 'pasty butt',
        'chick waterer', 'chick feeder', 'integration', 'pecking order',
        'socializing chicks',
        # Goats — Breeds
        'goat', 'goats', 'dairy goat', 'meat goat', 'nigerian dwarf', 'nubian',
        'alpine', 'lamancha', 'saanen', 'boer', 'kiko', 'pygmy',
        'registered goat', 'goat purchase',
        # Goats — Housing
        'goat shelter', 'goat barn', 'goat fencing', 'woven wire', 'cattle panel',
        'goat pen', 'kidding pen', 'buck housing', 'predator protection',
        # Goats — Feeding
        'goat feed', 'alfalfa', 'browse', 'grain', 'mineral', 'loose mineral',
        'copper bolus', 'selenium', 'baking soda', 'goat nutrition',
        'body condition score', 'feeding schedule', 'pasture management',
        # Goats — Health
        'goat health', 'hoof trimming', 'deworming', 'famacha', 'coccidia',
        'cdt vaccine', 'bloat', 'ketosis', 'mastitis', 'pneumonia',
        'caseous lymphadenitis', 'cl', 'johnes', 'cae', 'parasite', 'fecal test',
        'body temperature', 'goat first aid',
        # Goats — Breeding
        'kidding', 'breeding', 'heat cycle', 'buck', 'doe', 'gestation',
        'kidding kit', 'dystocia', 'kid care', 'bottle feeding', 'colostrum',
        'disbudding', 'castration', 'weaning', 'breeding season',
        # Goats — Milking
        'milking', 'milk stand', 'milking routine', 'udder health', 'milk storage',
        'pasteurization', 'raw milk', 'cheese making', 'goat cheese', 'soap making',
        'goat milk soap', 'milk yield', 'drying off',
        # Other Livestock
        'cattle', 'cow', 'calf', 'heifer', 'bull', 'steer',
        'pig', 'pigs', 'hog', 'piglet', 'farrowing',
        'sheep', 'lamb', 'ewe', 'ram', 'shearing', 'wool',
        'duck', 'ducks', 'turkey', 'turkeys', 'quail', 'guinea fowl',
        'rabbit', 'rabbits', 'hutch',
        'bee', 'bees', 'beekeeping', 'apiary', 'hive', 'honey', 'pollinator',
        'livestock', 'animal husbandry', 'feed', 'hay', 'straw', 'bedding',
        'pasture', 'pasture raised', 'rotational grazing', 'paddock', 'electric fence',
        # Fencing & Property
        'fencing', 'fence', 'gate', 'post', 'wire', 'electric fence',
        'property line', 'survey', 'easement', 'acreage',
        # Equipment & Tools
        'tractor', 'mower', 'tiller', 'chainsaw', 'splitter', 'chipper',
        'wheelbarrow', 'hand tools', 'pruner', 'loppers', 'shovel', 'rake',
        'hoe', 'broadfork', 'seeder', 'sprayer',
        # Firewood & Energy
        'firewood', 'woodstove', 'wood stove', 'cord', 'splitting',
        'seasoning', 'kindling', 'solar', 'solar panel', 'off-grid',
        'generator', 'battery bank', 'wind turbine',
        # Building & Projects
        'barn', 'shed', 'outbuilding', 'workshop', 'root cellar',
        'deck', 'porch', 'fencing project', 'building project',
        'concrete', 'lumber', 'hardware', 'plumbing', 'electrical',
        # Land Management
        'orchard', 'food forest', 'windbreak', 'hedgerow',
        'timber', 'logging', 'clearing', 'grading', 'drainage',
        'erosion', 'terracing', 'pond', 'dam',
        # Pest & Disease
        'pest', 'pest control', 'integrated pest management', 'ipm',
        'predator', 'beneficial insect', 'ladybug', 'praying mantis',
        'deer', 'deer fence', 'rabbit damage', 'vole', 'mole', 'groundhog',
        'blight', 'mildew', 'fungus', 'rot', 'wilt', 'aphid', 'hornworm',
        'squash bug', 'neem oil', 'bt', 'diatomaceous earth', 'organic spray',
        # Seasonal
        'spring prep', 'fall cleanup', 'winter prep', 'winterizing',
        'seed starting', 'garden planning', 'harvest season',
    ]

    content_lower = content.lower()
    for term in terms:
        if term in content_lower:
            topics.add(term)

    # Extract hashtags
    hashtags = re.findall(r'#(\w+)', content)
    topics.update(tag.lower() for tag in hashtags)

    return list(topics)[:100]
