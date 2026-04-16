"""Content extraction helpers for health sessions."""

import re


def compute_depth_signals(content: str, matched_topics: list[str]) -> dict[str, float]:
    """Compute per-topic depth signals for an article.

    Measures how substantively an article covers each topic based on
    mention frequency relative to article length and topic breadth.

    Returns dict of topic_name -> mention_weight (0.2 to 1.0).
    """
    content_lower = content.lower()
    word_count = max(len(content.split()), 1)
    total_topics = max(len(matched_topics), 1)

    signals = {}
    for topic in matched_topics:
        topic_lower = topic.lower()
        mentions = content_lower.count(topic_lower)
        density = mentions / total_topics
        depth = min(mentions / max(word_count / 500, 1), 1.0)
        weight = max(0.2, min(0.3 * density + 0.7 * depth, 1.0))
        signals[topic] = round(weight, 3)

    return signals


def extract_title_from_content(content: str) -> str | None:
    """Extract title from first H1 heading in markdown."""
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_topics_from_content(content: str) -> list[str]:
    """Extract health/fitness topics from content."""
    topics = set()

    terms = [
        # Musculoskeletal & Anatomy
        'piriformis', 'hip flexor', 'psoas', 'iliacus',
        'glute', 'gluteus', 'hamstring', 'quadriceps', 'adductor', 'abductor',
        'rotator cuff', 'scapula', 'thoracic', 'lumbar', 'cervical', 'spine',
        'fascia', 'tendon', 'ligament', 'joint', 'capsule', 'cartilage',
        'hip internal rotation', 'hip external rotation', 'hip mobility',
        'pelvic tilt', 'anterior pelvic tilt', 'posterior pelvic tilt',
        'transversus abdominis', 'multifidus', 'diaphragm', 'core stability',
        'obturator', 'sacrum', 'coccyx', 'si joint', 'sacroiliac',
        'trigger point', 'myofascial', 'force closure', 'fhl', 'kinetic chain',
        'imbalance', 'compensation',
        # Movement & Mobility
        'dysfunction', 'motor pattern', 'movement pattern',
        'mobility', 'stability', 'flexibility', 'range of motion', 'rom',
        'hip cars', 'cars', 'controlled articular rotation', 'frc',
        'corrective exercise', 'activation', 'inhibition', 'tightness',
        'movement snacks', 'kinstretch', 'pails', 'rails', 'lift-off', 'end range',
        'sedentary breaks', 'micromovement', 'lipoprotein lipase', 'glut4',
        'soleus pump', 'postural reset', 'ultradian rhythm', 'grease the groove',
        'active couch potato', 'sitting disease', 'thoracic rotation', 'desk protocol',
        'equipment placement',
        # Supplements & Compounds
        'peptide', 'peptides', 'creatine', 'collagen synthesis', 'tissue regeneration',
        # Wearables & Tracking
        'wearables', 'cgm', 'hrv', 'whoop', 'oura', 'garmin', 'apple watch',
        'sleep tracking', 'recovery score', 'strain score', 'body battery',
        'readiness score', 'resting heart rate', 'heart rate variability',
        'vo2 max estimate', 'training load', 'wearable accuracy',
        # Nutrition & Diet
        'nutrition', 'macros', 'protein', 'carbohydrates', 'fats', 'calories',
        'fasting', 'intermittent fasting', 'keto', 'carnivore', 'paleo', 'whole foods',
        'micronutrients', 'vitamins', 'minerals', 'electrolytes', 'hydration',
        'meal prep', 'meal timing', 'nutrient timing', 'supplements', 'creatine',
        'organ meats', 'bone broth', 'anti-nutrients', 'food quality', 'dairy-free',
        'gluten-free', 'collagen', 'fiber',
        # Strength & Training
        'strength training', 'resistance training', 'hypertrophy', 'powerlifting',
        'compound movements', 'deadlift', 'squat', 'bench press', 'overhead press',
        'progressive overload', 'periodization', 'deload', 'volume', 'intensity',
        'reps', 'sets', 'tempo', 'time under tension', 'mind muscle connection',
        'single leg', 'unilateral', 'rdl', 'hip hinge', 'glute bridge',
        'dead bug', 'bird dog', 'eccentric', 'isometric',
        # Cardio & Conditioning
        'cardio', 'zone 2', 'hiit', 'liss', 'vo2 max', 'lactate threshold',
        'endurance', 'conditioning', 'sprints', 'rowing', 'cycling', 'running',
        'heart rate', 'cardiac output', 'aerobic base', 'cardio circuit', 'emom',
        # Recovery & Sleep
        'recovery', 'sleep', 'deep sleep', 'rem sleep', 'sleep hygiene',
        'cold exposure', 'ice bath', 'sauna', 'contrast therapy', 'massage',
        'foam rolling', 'stretching', 'active recovery',
        'tissue healing', 'inflammation', 'anti-inflammatory',
        'red light', 'pemf', 'compression',
        # Hormones & Optimization
        'testosterone', 'cortisol', 'insulin', 'growth hormone', 'thyroid',
        'hormone optimization', 'bloodwork', 'biomarkers', 'labs', 'metabolic health',
        'dhea', 'pregnenolone', 'estrogen', 'progesterone', 'igf-1',
        # Longevity & Biohacking
        'longevity', 'healthspan', 'lifespan', 'aging', 'anti-aging',
        'autophagy', 'mitochondria', 'nad+', 'sirtuins', 'telomeres',
        'biohacking', 'quantified self', 'protocol',
        'biological age', 'epigenetics', 'urolithin a', 'spermidine',
        'rapamycin', 'senolytics', 'dna methylation',
        # Mental Performance
        'focus', 'cognition', 'nootropics', 'brain health', 'neuroplasticity',
        'meditation', 'breathwork', 'stress management', 'mental clarity',
        'emotional resilience', 'memory', 'attention', 'flow state',
        # Body Composition
        'body composition', 'body fat', 'lean mass', 'muscle mass', 'dexa',
        'recomp', 'cutting', 'bulking', 'metabolic rate',
        # Protocols & Systems
        'routine', 'habit', 'consistency', 'tracking', 'optimization',
        'corrective', 'rehabilitation', 'prehab', 'movement practice',
        # Gut Health & Microbiome
        'gut health', 'microbiome', 'probiotics', 'prebiotics', 'fermented foods',
        'fermented', 'fiber diversity', 'resistant starch', 'butyrate', 'scfa',
        'leaky gut', 'intestinal permeability', 'zonulin', 'gut barrier', 'dysbiosis',
        'sibo', 'gut-brain axis', 'digestive enzymes', 'kimchi', 'sauerkraut', 'kefir',
        'kombucha', 'colonocytes', 'microbiota',
        'gerd', 'reflux', 'hiatal hernia', 'les', 'stomach acid',
        # Hydration & Electrolytes
        'electrolytes', 'sodium', 'potassium', 'magnesium', 'hydration', 'celtic salt',
        'mineral water', 'coconut water', 'adrenal cocktail', 'trace minerals',
        'dehydration', 'water intake', 'lmnt', 'diy electrolyte',
        # Natural Compounds & Adaptogens
        'ashwagandha', 'rhodiola', 'lions mane', 'reishi', 'cordyceps', 'shilajit',
        'maca', 'ginseng', 'tulsi', 'saffron', 'adaptogens', 'medicinal mushrooms',
        'l-theanine', 'herbal',
        # Circadian & Light
        'circadian rhythm', 'morning sunlight', 'blue light', 'sleep hygiene',
        'melatonin', 'light exposure', 'sleep tracking', 'sleep latency',
        'night routine', 'wake time',
        # Breathing & Nervous System
        'diaphragmatic breathing', 'nasal breathing', 'mouth taping', 'nitric oxide',
        'co2 tolerance', 'bolt score', 'breath holds', 'resonance breathing',
        'extended exhale', 'cyclic sighing', 'respiratory sinus arrhythmia',
        'vagal tone', 'vagus nerve', 'parasympathetic', 'sympathetic',
        'autonomic nervous system', 'nervous system regulation', 'polyvagal',
        'ventral vagal', 'dorsal vagal', 'diving reflex', 'hrv biofeedback',
        'box breathing', 'wim hof', 'combat breathing', 'stress response',
        'gargling', 'humming', 'bohr effect', 'cholinergic anti-inflammatory',
        'oxygen-hemoglobin dissociation', '2,3-dpg', 'hypocapnia', 'hyperventilation',
        'chemoreceptors', 'reduced breathing', 'respiratory alkalosis',
        'oxygen delivery', 'alveolar recruitment', 'hering-breuer reflex',
        'pulmonary stretch receptors', 'physiological sigh',
        # Thermal Therapy
        'cold plunge', 'infrared sauna', 'contrast shower', 'heat therapy',
        'cryotherapy', 'thermal stress', 'cold adaptation', 'heat shock proteins',
        'brown fat',
        # Ergonomics & Posture
        'standing desk', 'desk posture', 'monitor height', 'sitting', 'workstation',
        'forward head', 'thoracic kyphosis', 'ergonomic',
        # Community & Lifestyle
        'walking', 'nature exposure', 'grounding', 'earthing', 'sunlight',
        'community', 'social connection', 'digital detox', 'screen time',
        'lifestyle design',
        # Wrestling & Combat Sports
        'wrestling', 'takedown', 'single leg', 'double leg', 'high crotch', 'snap down',
        'front headlock', 'underhook', 'duck under', 'ankle pick', 'arm drag', 'sprawl',
        'chain wrestling', 'hand fighting', 'tie-up', 'go-behind', 'cement mixer',
        'top position', 'bottom position', 'ride', 'tilt', 'half nelson', 'arm bar',
        'spiral ride', 'stand up', 'sit out', 'switch', 'granby roll', 'hip heist',
        'mat return', 'breakdown', 'pinning', 'near fall', 'escape', 'reversal',
        'live wrestling', 'drilling', 'scramble', 'mat wrestling', 'neutral position',
        'referee position', 'weight class', 'weight cutting', 'weigh-in', 'rehydration',
        'tournament', 'bracket', 'seeding', 'folkstyle', 'freestyle', 'greco-roman',
        # RSI & Ergonomics
        'carpal tunnel', 'median nerve', 'nerve glides', 'tendon gliding', 'wrist splint',
        'rsi', 'repetitive strain', 'de quervain', 'trigger finger',
        'ulnar nerve', 'radial nerve', 'thoracic outlet', 'neural tension',
    ]

    content_lower = content.lower()
    for term in terms:
        if term in content_lower:
            topics.add(term)

    # Extract hashtags
    hashtags = re.findall(r'#(\w+)', content)
    topics.update(tag.lower() for tag in hashtags)

    return list(topics)


def extract_key_takeaways(content: str) -> list[str]:
    """Extract key takeaways from markdown content."""
    takeaways = []

    match = re.search(r'(?:key\s+)?takeaways?\s*\n((?:[-*]\s+.+\n?)+)', content, re.IGNORECASE)
    if match:
        items = re.findall(r'[-*]\s+(.+)', match.group(1))
        takeaways.extend(items[:5])

    if not takeaways:
        bullets = re.findall(r'^[-*]\s+(.{20,100})$', content, re.MULTILINE)
        takeaways.extend(bullets[:5])

    return takeaways
