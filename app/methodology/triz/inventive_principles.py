"""
TRIZ 40 Inventive Principles - Coaching Reference Data

These are the 40 inventive principles from Genrich Altshuller's TRIZ
methodology, formatted for coaching context injection. Each principle
includes a name, description, coaching prompt hints, and examples.

The coaching engine uses these when:
1. An innovator using the TRIZ archetype reaches Principle Application phase
2. The contradiction matrix suggests specific principles for a parameter pair
3. A biomimicry pattern's triz_connections field references a principle

These are COACHING references, not a TRIZ solver. The coach uses them
to guide the innovator's thinking - the innovator creates the solution.
"""

from typing import Dict, List, Optional


INVENTIVE_PRINCIPLES: List[Dict] = [
    {
        "number": 1,
        "name": "Segmentation",
        "description": "Divide an object into independent parts. Make an object easy to disassemble. Increase the degree of fragmentation or segmentation.",
        "coaching_hints": [
            "Could you break this into smaller, independent pieces?",
            "What if each part could function on its own?",
            "Could modular segments solve different parts of the problem?"
        ],
        "examples": ["Modular furniture", "Sectional garage doors", "Micro-services architecture"],
        "biomimicry_organisms": []
    },
    {
        "number": 2,
        "name": "Taking Out (Extraction)",
        "description": "Separate an interfering part or property from an object. Extract only the necessary part or property.",
        "coaching_hints": [
            "What if you removed the problematic part entirely?",
            "Could you extract just the useful function and discard the rest?",
            "What's the essential quality you need, stripped of everything else?"
        ],
        "examples": ["Noise-cancelling headphones extract sound", "Cloud computing extracts processing from hardware"],
        "biomimicry_organisms": []
    },
    {
        "number": 3,
        "name": "Local Quality",
        "description": "Change an object's structure from uniform to non-uniform. Make each part of an object fulfill a different function. Place each part of an object under conditions most favorable for its operation.",
        "coaching_hints": [
            "Does every part need to be the same, or could different zones have different properties?",
            "What if you optimized each component for its specific function?",
            "Could varying the structure locally solve the contradiction?"
        ],
        "examples": ["Variable-pitch propellers", "Zoned air conditioning", "Multi-layer composites"],
        "biomimicry_organisms": []
    },
    {
        "number": 4,
        "name": "Asymmetry",
        "description": "Change the shape of an object from symmetrical to asymmetrical. If an object is already asymmetrical, increase its degree of asymmetry.",
        "coaching_hints": [
            "What if the design wasn't symmetrical?",
            "Could asymmetry give you an advantage the symmetric version lacks?",
            "Where would asymmetry create new functionality?"
        ],
        "examples": ["Asymmetric car headlights for different driving regions", "Ergonomic tool handles"],
        "biomimicry_organisms": []
    },
    {
        "number": 5,
        "name": "Merging (Consolidation)",
        "description": "Bring closer together or merge identical or similar objects. Assemble identical or similar parts to perform parallel operations. Make operations contiguous or parallel.",
        "coaching_hints": [
            "Could you combine multiple similar components into one?",
            "What if you ran these processes in parallel?",
            "Could consolidation reduce complexity while maintaining function?"
        ],
        "examples": ["Multi-blade razors", "Parallel computing", "Combined shipping containers"],
        "biomimicry_organisms": []
    },
    {
        "number": 6,
        "name": "Universality",
        "description": "Make a part or object perform multiple functions, eliminating the need for other parts.",
        "coaching_hints": [
            "Could this component serve multiple purposes?",
            "What if one element did the work of several?",
            "Is there a way to combine functions to eliminate parts?"
        ],
        "examples": ["Swiss Army knife", "Smartphone replacing multiple devices", "Sofa bed"],
        "biomimicry_organisms": []
    },
    {
        "number": 7,
        "name": "Nested Doll (Matryoshka)",
        "description": "Place one object inside another. Make one part pass through a cavity in the other. Multiple objects pass through cavities in each other.",
        "coaching_hints": [
            "Could you nest components inside each other?",
            "What if one thing passed through another?",
            "Could nesting reduce the space or increase functionality?"
        ],
        "examples": ["Telescoping antenna", "Stackable chairs", "Nested measuring cups"],
        "biomimicry_organisms": []
    },
    {
        "number": 8,
        "name": "Anti-Weight (Counterweight)",
        "description": "Compensate for the weight of an object by merging with other objects that provide lift. Compensate for the weight of an object by interaction with the environment providing aerodynamic, hydrodynamic, or buoyancy forces.",
        "coaching_hints": [
            "Could you compensate for the weight using another force?",
            "What if you used buoyancy, lift, or counterbalancing?",
            "Is there an environmental force you could harness?"
        ],
        "examples": ["Counterweights in elevators", "Hydrofoils", "Hot air balloons"],
        "biomimicry_organisms": []
    },
    {
        "number": 9,
        "name": "Preliminary Anti-Action",
        "description": "If it will be necessary to do an action with both harmful and useful effects, this action should be replaced with anti-actions to control harmful effects.",
        "coaching_hints": [
            "Could you counteract the harmful effect before it happens?",
            "What if you built in the opposite action in advance?",
            "Is there a preventive measure that neutralizes the downside?"
        ],
        "examples": ["Pre-stressed concrete", "Preventive medication", "Firebreaks"],
        "biomimicry_organisms": []
    },
    {
        "number": 10,
        "name": "Preliminary Action",
        "description": "Perform the required change of an object in advance. Pre-arrange objects such that they can come into action from the most convenient place.",
        "coaching_hints": [
            "Could you do the work in advance, before it's needed?",
            "What if the preparation was already built in?",
            "How could pre-positioning reduce complexity later?"
        ],
        "examples": ["Pre-cut vegetables", "Pre-pasted wallpaper", "Just-in-time inventory staging"],
        "biomimicry_organisms": []
    },
    {
        "number": 11,
        "name": "Beforehand Cushioning",
        "description": "Prepare emergency means beforehand to compensate for the relatively low reliability of an object.",
        "coaching_hints": [
            "What backup would protect against failure?",
            "Could you build in a safety net in advance?",
            "What fallback would cushion the impact of a worst-case scenario?"
        ],
        "examples": ["Airbags", "Emergency exits", "Data backup systems"],
        "biomimicry_organisms": []
    },
    {
        "number": 12,
        "name": "Equipotentiality",
        "description": "In a potential field, limit position changes. Change operating conditions to eliminate the need to raise or lower objects in a potential field.",
        "coaching_hints": [
            "Could you eliminate the need for lifting or lowering?",
            "What if you operated at a constant level or state?",
            "Is there a way to avoid the energy cost of changing potential?"
        ],
        "examples": ["Spring-loaded platforms", "Lock systems in canals", "Level conveyors"],
        "biomimicry_organisms": []
    },
    {
        "number": 13,
        "name": "The Other Way Round (Inversion)",
        "description": "Invert the action used to solve the problem. Make movable parts fixed and fixed parts movable. Turn the object upside down.",
        "coaching_hints": [
            "What if you did the exact opposite?",
            "Could you flip which part moves and which stays still?",
            "What would happen if you turned this problem inside out?"
        ],
        "examples": ["Moving sidewalks instead of walking", "Treadmill instead of running outdoors", "Rotation vs. linear motion"],
        "biomimicry_organisms": []
    },
    {
        "number": 14,
        "name": "Spheroidality (Curvature)",
        "description": "Replace linear parts with curved parts, flat surfaces with spherical surfaces, cube shapes with ball shapes. Use rollers, balls, spirals. Replace linear motion with rotary motion, use centrifugal force.",
        "coaching_hints": [
            "Could curves work better than straight lines?",
            "What if you used rotation instead of linear motion?",
            "Would spherical or rounded shapes offer advantages?"
        ],
        "examples": ["Ball bearings", "Spiral staircases", "Centrifuges"],
        "biomimicry_organisms": []
    },
    {
        "number": 15,
        "name": "Dynamics",
        "description": "Allow characteristics of an object or environment to change to be optimal at each stage. Divide an object into parts capable of movement relative to each other. Make an object movable or adaptive.",
        "coaching_hints": [
            "Could this adapt to changing conditions?",
            "What if it reconfigured itself for each stage?",
            "Could dynamic adjustment solve the contradiction?"
        ],
        "examples": ["Adjustable car seats", "Variable-speed drives", "Responsive web design"],
        "biomimicry_organisms": []
    },
    {
        "number": 16,
        "name": "Partial or Excessive Action",
        "description": "If 100% of an objective is hard to achieve, use slightly less or slightly more of the same method.",
        "coaching_hints": [
            "What if you aimed for 90% instead of 100%?",
            "Could overshooting the target make the problem easier?",
            "Would a partial solution be good enough?"
        ],
        "examples": ["Overfilling then trimming", "Spray painting coverage", "Salt on icy roads (more than needed)"],
        "biomimicry_organisms": []
    },
    {
        "number": 17,
        "name": "Another Dimension",
        "description": "Move into three-dimensional space. Use a multi-story arrangement. Tilt or reorient the object. Use another side of a given area.",
        "coaching_hints": [
            "Could you add a dimension the current design doesn't use?",
            "What if you went vertical instead of horizontal?",
            "Could tilting or reorienting change the dynamics?"
        ],
        "examples": ["Multi-story parking", "Spiral notebook binding", "Infrared remote (another spectrum dimension)"],
        "biomimicry_organisms": []
    },
    {
        "number": 18,
        "name": "Mechanical Vibration",
        "description": "Cause an object to oscillate or vibrate. Increase frequency up to ultrasonic. Use resonance frequency. Use piezoelectric vibrators instead of mechanical. Use combined ultrasonic and electromagnetic field oscillations.",
        "coaching_hints": [
            "Could vibration or oscillation help?",
            "What if you used resonance to your advantage?",
            "Would ultrasonic or subsonic frequencies work better?"
        ],
        "examples": ["Ultrasonic cleaning", "Jackhammers", "Vibrating screens for sorting"],
        "biomimicry_organisms": []
    },
    {
        "number": 19,
        "name": "Periodic Action",
        "description": "Replace continuous action with periodic action. If an action is already periodic, change the periodic magnitude or frequency. Use pauses between impulses to perform a different action.",
        "coaching_hints": [
            "Could intermittent action work better than continuous?",
            "What if you pulsed instead of sustained?",
            "Could the pauses be used for something else?"
        ],
        "examples": ["Pulsed lasers", "Intermittent windshield wipers", "Interval training"],
        "biomimicry_organisms": []
    },
    {
        "number": 20,
        "name": "Continuity of Useful Action",
        "description": "Carry on work continuously without idle time. Eliminate all idle or intermittent actions. Replace to-and-fro motion with rotary motion.",
        "coaching_hints": [
            "How could you eliminate downtime?",
            "What if the useful action never stopped?",
            "Could continuous flow replace batch processing?"
        ],
        "examples": ["Continuous casting", "Assembly line", "Flywheel energy storage"],
        "biomimicry_organisms": []
    },
    {
        "number": 21,
        "name": "Skipping (Rushing Through)",
        "description": "Conduct a process at high speed. Skip dangerous or harmful stages quickly.",
        "coaching_hints": [
            "Could you get through the problematic phase faster?",
            "What if speed eliminated the danger window?",
            "Would rushing through minimize exposure to harm?"
        ],
        "examples": ["Flash pasteurization", "Quick-release mechanisms", "Speed welding"],
        "biomimicry_organisms": []
    },
    {
        "number": 22,
        "name": "Blessing in Disguise (Turn Lemons into Lemonade)",
        "description": "Use harmful factors or effects to achieve a positive effect. Eliminate a harmful factor by adding it to another harmful factor. Amplify a harmful factor to such a degree that it is no longer harmful.",
        "coaching_hints": [
            "Could the 'bad' part actually be useful?",
            "What if you turned the problem into the solution?",
            "Could combining two negatives create a positive?"
        ],
        "examples": ["Vaccination uses weakened viruses", "Sand in oysters creates pearls", "Forest fires enable regrowth"],
        "biomimicry_organisms": []
    },
    {
        "number": 23,
        "name": "Feedback",
        "description": "Introduce feedback to improve a process or action. If feedback already exists, change its magnitude or influence.",
        "coaching_hints": [
            "Could the system learn from its own output?",
            "What if you added a feedback loop?",
            "Could real-time feedback improve performance?"
        ],
        "examples": ["Thermostat", "Cruise control", "Customer feedback systems"],
        "biomimicry_organisms": []
    },
    {
        "number": 24,
        "name": "Intermediary (Mediator)",
        "description": "Use an intermediate carrier article or process. Merge one object temporarily with another which can be easily removed.",
        "coaching_hints": [
            "Could an intermediary make this easier?",
            "What if something bridged the gap between the two?",
            "Could a temporary connector solve the problem?"
        ],
        "examples": ["Catalysts", "Escrow services", "Adapters and converters"],
        "biomimicry_organisms": []
    },
    {
        "number": 25,
        "name": "Self-Service",
        "description": "Make an object serve itself by performing auxiliary functions. Use waste resources, energy, or substances.",
        "coaching_hints": [
            "Could the system maintain itself?",
            "What if byproducts became inputs?",
            "Could waste energy be captured and reused?"
        ],
        "examples": ["Self-cleaning ovens", "Regenerative braking", "Composting toilet"],
        "biomimicry_organisms": []
    },
    {
        "number": 26,
        "name": "Copying",
        "description": "Instead of an unavailable, expensive, fragile object, use simpler and inexpensive copies. Replace an object or system with optical copies. Use infrared or ultraviolet copies.",
        "coaching_hints": [
            "Could a copy or simulation work just as well?",
            "What if you used a replica instead of the original?",
            "Could digital or virtual copies replace physical ones?"
        ],
        "examples": ["Digital twins", "Flight simulators", "Scale models"],
        "biomimicry_organisms": []
    },
    {
        "number": 27,
        "name": "Cheap Short-Lived Objects",
        "description": "Replace an expensive object with multiple cheap objects, compromising certain qualities like service life.",
        "coaching_hints": [
            "What if you used disposable instead of durable?",
            "Could many cheap copies replace one expensive item?",
            "Is longevity actually necessary, or could you replace cheaply?"
        ],
        "examples": ["Disposable razors", "Paper cups", "Temporary scaffolding"],
        "biomimicry_organisms": []
    },
    {
        "number": 28,
        "name": "Mechanics Substitution",
        "description": "Replace a mechanical system with an optical, acoustic, or other field-based system. Use electric, magnetic, or electromagnetic fields for interaction. Change fields from static to dynamic, from fixed to changeable. Use fields in conjunction with field-activated particles.",
        "coaching_hints": [
            "Could a field replace mechanical contact?",
            "What if you used magnetic, electric, or optical forces?",
            "Could sensor-based approaches replace physical mechanisms?"
        ],
        "examples": ["Magnetic levitation", "Induction cooking", "Touchless sensors"],
        "biomimicry_organisms": []
    },
    {
        "number": 29,
        "name": "Pneumatics and Hydraulics",
        "description": "Use gas and liquid parts of an object instead of solid parts. Inflatable and filled structures, air cushion, hydrostatic and hydro-reactive.",
        "coaching_hints": [
            "Could air or liquid replace solid components?",
            "What if you used pneumatic or hydraulic pressure?",
            "Could inflatable or fluid-filled designs work?"
        ],
        "examples": ["Air bags", "Hydraulic jacks", "Pneumatic tools"],
        "biomimicry_organisms": []
    },
    {
        "number": 30,
        "name": "Flexible Shells and Thin Films",
        "description": "Use flexible shells and thin films instead of three-dimensional structures. Isolate the object from the external environment using flexible shells and thin films.",
        "coaching_hints": [
            "Could a thin film do the job of a thick structure?",
            "What if a flexible membrane replaced a rigid shell?",
            "Could coatings or wraps provide the needed protection?"
        ],
        "examples": ["Shrink wrap", "Bubble wrap", "Protective coatings"],
        "biomimicry_organisms": []
    },
    {
        "number": 31,
        "name": "Porous Materials",
        "description": "Make an object porous or add porous elements. If an object is already porous, use the pores to introduce a useful substance or function.",
        "coaching_hints": [
            "Could adding porosity help?",
            "What if the material had holes or voids?",
            "Could you use existing pores to add functionality?"
        ],
        "examples": ["Sponges", "Foam insulation", "Sintered metal filters"],
        "biomimicry_organisms": []
    },
    {
        "number": 32,
        "name": "Color Changes",
        "description": "Change the color of an object or its external environment. Change the transparency of an object or its environment. Use colored additives to observe things that are difficult to see. Use luminescent or photochromic materials.",
        "coaching_hints": [
            "Could color change indicate status?",
            "What if visibility was controlled by transparency?",
            "Could photochromic or thermochromic materials help?"
        ],
        "examples": ["Mood rings", "Photochromic lenses", "Color-coded warnings"],
        "biomimicry_organisms": []
    },
    {
        "number": 33,
        "name": "Homogeneity",
        "description": "Make objects interact with a given object of the same material or material with identical properties.",
        "coaching_hints": [
            "Could using the same material throughout help?",
            "What if all components shared identical properties?",
            "Would homogeneity simplify manufacturing or interaction?"
        ],
        "examples": ["Ice containers for ice", "Wooden pegs in wooden furniture", "Single-material recycling"],
        "biomimicry_organisms": []
    },
    {
        "number": 34,
        "name": "Discarding and Recovering",
        "description": "Make portions of an object that have fulfilled their functions go away or modify themselves during the work process. Conversely, restore consumable parts of an object directly in operation.",
        "coaching_hints": [
            "Could the used portion disappear or transform?",
            "What if the component regenerated while operating?",
            "Could you eliminate waste by design?"
        ],
        "examples": ["Dissolving stitches", "Self-sharpening knives", "Rocket stage separation"],
        "biomimicry_organisms": []
    },
    {
        "number": 35,
        "name": "Parameter Changes",
        "description": "Change an object's physical state. Change concentration or consistency. Change degree of flexibility. Change temperature or volume. Change pressure. Change other parameters.",
        "coaching_hints": [
            "What if you changed the state (solid, liquid, gas)?",
            "Could adjusting concentration or density help?",
            "Would changing temperature or pressure solve the problem?"
        ],
        "examples": ["Freeze drying", "Pressure cooking", "Phase-change materials"],
        "biomimicry_organisms": []
    },
    {
        "number": 36,
        "name": "Phase Transitions",
        "description": "Use phenomena occurring during phase transitions. Use the effects accompanying phase transitions, such as volume change, heat absorption or release.",
        "coaching_hints": [
            "Could a phase change provide the needed effect?",
            "What if you harnessed melting, freezing, or vaporizing?",
            "Could the energy released during phase change be useful?"
        ],
        "examples": ["Ice packs", "Heat pipes", "Steam engines"],
        "biomimicry_organisms": []
    },
    {
        "number": 37,
        "name": "Thermal Expansion",
        "description": "Use thermal expansion or contraction of materials. If thermal expansion is being used, use multiple materials with different coefficients of expansion.",
        "coaching_hints": [
            "Could thermal expansion do mechanical work?",
            "What if different expansion rates created useful motion?",
            "Could bimetallic effects be harnessed?"
        ],
        "examples": ["Bimetallic thermostats", "Shrink fitting", "Expansion joints"],
        "biomimicry_organisms": []
    },
    {
        "number": 38,
        "name": "Strong Oxidants (Accelerated Oxidation)",
        "description": "Replace common air with oxygen-enriched air. Replace enriched air with pure oxygen. Expose air or oxygen to ionizing radiation. Use ionized oxygen. Replace ozonized oxygen with ozone.",
        "coaching_hints": [
            "Could more reactive agents speed up the process?",
            "What if you used enriched or activated forms?",
            "Would stronger oxidation solve the problem faster?"
        ],
        "examples": ["Oxygen welding", "Ozone sterilization", "Hyperbaric oxygen therapy"],
        "biomimicry_organisms": []
    },
    {
        "number": 39,
        "name": "Inert Atmosphere",
        "description": "Replace a normal environment with an inert one. Add neutral parts or inert additives to an object. Carry out the process in a vacuum.",
        "coaching_hints": [
            "Could an inert environment prevent unwanted reactions?",
            "What if you removed reactive elements?",
            "Would a vacuum or neutral gas improve the process?"
        ],
        "examples": ["Nitrogen food packaging", "Argon welding", "Vacuum-sealed products"],
        "biomimicry_organisms": []
    },
    {
        "number": 40,
        "name": "Composite Materials",
        "description": "Change from uniform to composite materials. Use materials with complementary properties.",
        "coaching_hints": [
            "Could combining materials give you both properties?",
            "What if you used a composite instead of a single material?",
            "Could reinforcement or layering solve the contradiction?"
        ],
        "examples": ["Fiberglass", "Reinforced concrete", "Carbon fiber composites"],
        "biomimicry_organisms": []
    },
]


def get_principle(number: int) -> Optional[Dict]:
    """
    Get a specific inventive principle by number.

    Args:
        number: Principle number (1-40)

    Returns:
        The principle dict, or None if not found
    """
    if 1 <= number <= 40:
        return INVENTIVE_PRINCIPLES[number - 1]
    return None


def get_principles_by_numbers(numbers: List[int]) -> List[Dict]:
    """
    Get multiple inventive principles by their numbers.

    Args:
        numbers: List of principle numbers (1-40)

    Returns:
        List of principle dicts
    """
    return [get_principle(n) for n in numbers if get_principle(n)]


def get_coaching_hints(number: int) -> List[str]:
    """
    Get coaching hints for a specific principle.

    Args:
        number: Principle number (1-40)

    Returns:
        List of coaching hint strings
    """
    principle = get_principle(number)
    return principle.get("coaching_hints", []) if principle else []
