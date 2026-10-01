"""
DoctorVet AI - built-in veterinary reference protocols (RAG-lite).

IMPORTANT: These entries were written from general, widely published veterinary
knowledge. They are a *reference layer* that is shown to the AI reviewer and to
the user - they are NOT a substitute for the Merck Veterinary Manual, WOAH
Terrestrial Manual, or your national/provincial livestock department
guidelines. Have a licensed veterinarian review and extend this file before
using it commercially. Doses marked "typical" must always be confirmed by a vet
against the product label and the animal's real body weight.

Each entry:
  id         short key
  name       display name
  keywords   lowercase words that trigger retrieval (matched against the AI's
             diagnosis / differentials / the focus disease chosen by the user)
  species    canonical species tags this applies to ("all" = any)
  notifiable True if usually reportable to animal-health authorities
  zoonotic   True if it can infect humans
  protocol   short reference text
"""

KNOWLEDGE_BASE = [
    # ------------------------------------------------------------------ CATTLE / BUFFALO
    {
        "id": "fmd", "name": "Foot & Mouth Disease (FMD)",
        "keywords": ["foot and mouth", "foot & mouth", "fmd", "aphthous"],
        "species": ["cattle", "buffalo", "goat", "sheep", "pig", "camel"],
        "notifiable": True, "zoonotic": False,
        "protocol": (
            "Highly contagious viral disease of cloven-hoofed animals (camels are relatively resistant). "
            "Signs: fever, drooling, vesicles/erosions on tongue, dental pad, muzzle, teats and between the hooves, "
            "lameness, sharp drop in milk. Isolate immediately, restrict movement of animals/people/vehicles, disinfect "
            "(4% sodium carbonate or 0.2% citric acid), and report to the animal-health authority. No antiviral exists: "
            "supportive care - soft feed, clean water, gentle antiseptic mouth wash and hoof cleaning as advised by a vet, "
            "NSAID for fever/pain, antibiotics ONLY for secondary bacterial infection. Vaccinate healthy stock with the "
            "locally matched serotype vaccine as directed by the authority."
        ),
    },
    {
        "id": "lsd", "name": "Lumpy Skin Disease (LSD)",
        "keywords": ["lumpy skin", "lsd"],
        "species": ["cattle", "buffalo"],
        "notifiable": True, "zoonotic": False,
        "protocol": (
            "Capripoxvirus spread mainly by biting flies, mosquitoes and ticks. Signs: fever, firm skin nodules (2-5 cm), "
            "swollen superficial lymph nodes, limb/brisket oedema, nasal/eye discharge, mouth lesions. Isolate, control "
            "vectors (fly control, insect repellents), NSAID for fever/pain, broad-spectrum antibiotic for secondary "
            "infection and wound care of open nodules. Report to authority; vaccinate with a homologous LSD/Neethling "
            "vaccine per the official programme."
        ),
    },
    {
        "id": "hs", "name": "Haemorrhagic Septicaemia (HS)",
        "keywords": ["haemorrhagic septicaemia", "hemorrhagic septicemia", "hemorrhagic septicaemia", "pasteurellosis", "pasteurella"],
        "species": ["cattle", "buffalo", "camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Pasteurella multocida (type B:2 in Asia). Signs: sudden high fever, swelling of throat/dewlap/brisket, "
            "salivation, laboured breathing, rapid death, often in the rainy season. Treat EARLY with an antibiotic the "
            "organism is susceptible to (e.g. oxytetracycline or sulphonamides - vet to choose) plus NSAID and fluids; "
            "prognosis is poor once respiratory distress is advanced. Isolate, avoid stress, vaccinate before the monsoon."
        ),
    },
    {
        "id": "bq", "name": "Black Quarter (Blackleg)",
        "keywords": ["black quarter", "blackleg", "black leg", "clostridium chauvoei", "bq"],
        "species": ["cattle", "buffalo", "sheep", "goat"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Clostridium chauvoei; young, well-fed cattle (6-24 months). Signs: sudden lameness, hot painful then cold "
            "crepitant (gas) swelling of a heavy muscle (hind/fore quarter), fever, sudden death. High-dose penicillin "
            "early plus NSAID/supportive care by a vet. Do NOT cut open carcasses (spreads spores) - deep burial or "
            "burning. Vaccinate annually before the risk season."
        ),
    },
    {
        "id": "anthrax", "name": "Anthrax",
        "keywords": ["anthrax", "bacillus anthracis"],
        "species": ["all"],
        "notifiable": True, "zoonotic": True,
        "protocol": (
            "Sudden death with dark unclotted blood from body openings, bloating and no rigor mortis. NEVER open a "
            "suspect carcass. Notifiable and zoonotic: keep people and animals away, report to the animal-health "
            "authority at once, burn or deep-bury with lime under official guidance. In-contact animals may be treated "
            "with penicillin/oxytetracycline and vaccinated under veterinary supervision. Humans with skin contact or "
            "who handled the carcass must seek medical care."
        ),
    },
    {
        "id": "brucellosis", "name": "Brucellosis",
        "keywords": ["brucellosis", "brucella", "contagious abortion"],
        "species": ["cattle", "buffalo", "goat", "sheep", "camel", "pig", "dog"],
        "notifiable": True, "zoonotic": True,
        "protocol": (
            "Signs: abortion in late pregnancy, retained placenta, weak calves/kids/camel calves, orchitis, joint "
            "swelling (hygroma). Zoonotic through raw milk and birth fluids. Antibiotic treatment is not effective or "
            "recommended in herds; confirm by serology (RBT/ELISA), segregate positives and follow the authority's "
            "test-and-control programme, vaccinate young females where the programme allows. Boil/pasteurise milk; "
            "wear gloves and mask when handling abortions and burn/bury foetal membranes."
        ),
    },
    {
        "id": "mastitis", "name": "Mastitis",
        "keywords": ["mastitis", "udder infection"],
        "species": ["cattle", "buffalo", "goat", "sheep", "camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Hot, swollen, painful quarter with abnormal milk (clots, watery, blood), sometimes fever. Strip out the "
            "quarter frequently, culture milk if possible, use an intramammary antibiotic labelled for lactating animals "
            "chosen by a vet, add an NSAID, and give systemic antibiotics/fluids if the animal is systemically ill. "
            "Discard milk during treatment and the labelled withdrawal period. Prevention: teat dipping, clean bedding, "
            "milk sick animals last, dry-cow therapy."
        ),
    },
    {
        "id": "theileriosis", "name": "Theileriosis (Tropical, T. annulata)",
        "keywords": ["theileriosis", "theileria", "tropical theileriosis"],
        "species": ["cattle", "buffalo"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Tick-borne (Hyalomma). Signs: high fever, enlarged prescapular/precrural lymph nodes, pale or yellow mucous "
            "membranes, weakness, drop in milk. Confirm with a Giemsa blood/lymph-node smear. Typical treatment: "
            "buparvaquone (about 2.5 mg/kg IM, repeat if needed - vet to confirm) with supportive care (fluids, "
            "haematinics, transfusion in severe anaemia). Tick control and calf-hood immunisation where available."
        ),
    },
    {
        "id": "babesiosis", "name": "Babesiosis / Tick Fever (Redwater)",
        "keywords": ["babesiosis", "tick fever", "redwater", "red water", "babesia", "anaplasmosis"],
        "species": ["cattle", "buffalo", "dog", "horse", "sheep", "goat"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Signs: fever, pale/yellow gums, dark red-brown urine, weakness, ticks present. Confirm by blood smear. "
            "Typical treatment: diminazene aceturate (about 3.5 mg/kg IM) or imidocarb; oxytetracycline for anaplasmosis; "
            "supportive care and blood transfusion if severe. Control ticks; do not stress or force-walk animals."
        ),
    },
    {
        "id": "milkfever", "name": "Milk Fever (Hypocalcaemia)",
        "keywords": ["milk fever", "hypocalcaemia", "hypocalcemia", "parturient paresis"],
        "species": ["cattle", "buffalo", "goat", "sheep"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "High-yielding dairy animals around calving: weakness, muscle tremor, cold ears, cow down/recumbent, "
            "S-shaped neck. Emergency: SLOW intravenous calcium borogluconate by a vet (monitor the heart; stop if "
            "rhythm changes), then oral calcium. Keep animal upright on its sternum, treat bloat. Prevention: correct "
            "pre-calving mineral/DCAD feeding."
        ),
    },
    {
        "id": "bloat", "name": "Bloat (Ruminal Tympany)",
        "keywords": ["bloat", "tympany", "ruminal tympany"],
        "species": ["cattle", "buffalo", "goat", "sheep", "camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Left flank distended and tight, distress, grunting. EMERGENCY. Frothy bloat: anti-foaming agent "
            "(e.g. vegetable oil or a silicone anti-bloat product) via stomach tube. Free-gas bloat: pass a stomach tube. "
            "If suffocating, a vet may need to use a trocar and cannula. Keep the animal standing/walking gently. "
            "Prevent by avoiding sudden lush legume/grain feeding."
        ),
    },
    {
        "id": "calf_scours", "name": "Neonatal / Calf Diarrhoea (Scours)",
        "keywords": ["calf diarrhoea", "calf diarrhea", "scours", "neonatal diarrhoea", "neonatal diarrhea", "kid diarrhoea"],
        "species": ["cattle", "buffalo", "goat", "sheep", "camel"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Causes: E. coli, rota/coronavirus, Cryptosporidium, Salmonella, coccidia. Main danger is dehydration and "
            "acidosis: give oral rehydration solution (ORS) often, keep the young animal warm, keep feeding milk, and "
            "make sure it received colostrum in the first hours. Antibiotics only if there is fever/blood/systemic "
            "illness. Sunken eyes, weakness or not standing = urgent vet (IV fluids). Wash hands - some causes are zoonotic."
        ),
    },
    # ------------------------------------------------------------------ GOAT / SHEEP
    {
        "id": "ppr", "name": "Peste des Petits Ruminants (PPR)",
        "keywords": ["ppr", "peste des petits", "goat plague"],
        "species": ["goat", "sheep", "camel"],
        "notifiable": True, "zoonotic": False,
        "protocol": (
            "Morbillivirus. Signs: fever, nasal/eye discharge, mouth erosions/necrosis, diarrhoea, pneumonia, high "
            "mortality in kids/lambs. No antiviral: isolate, supportive care, antibiotics for secondary pneumonia, "
            "report to authority. Control through vaccination (per official programme) and movement restriction."
        ),
    },
    {
        "id": "ccpp", "name": "Contagious Caprine Pleuropneumonia (CCPP)",
        "keywords": ["ccpp", "caprine pleuropneumonia", "pleuropneumonia"],
        "species": ["goat"],
        "notifiable": True, "zoonotic": False,
        "protocol": (
            "Mycoplasma capricolum subsp. capripneumoniae. Signs: fever, severe cough, laboured breathing, nasal "
            "discharge, often high mortality. Isolate and report; early treatment with an appropriate antibiotic "
            "(e.g. macrolide such as tylosin, or oxytetracycline - vet to choose), supportive care, ventilation; "
            "vaccinate in endemic areas."
        ),
    },
    {
        "id": "enterotoxaemia", "name": "Enterotoxaemia (Overeating disease)",
        "keywords": ["enterotoxaemia", "enterotoxemia", "pulpy kidney", "clostridium perfringens"],
        "species": ["goat", "sheep", "cattle", "camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Clostridium perfringens type D (also C). Sudden death, convulsions, colic, diarrhoea after a feed change "
            "or heavy grain. Treat urgently with antitoxin and penicillin under a vet, with fluids/NSAID; reduce "
            "grain, feed roughage. Prevent with clostridial vaccine and gradual diet changes."
        ),
    },
    {
        "id": "goatpox", "name": "Sheep / Goat Pox",
        "keywords": ["goat pox", "goatpox", "sheep pox", "sheeppox", "capripox"],
        "species": ["goat", "sheep"],
        "notifiable": True, "zoonotic": False,
        "protocol": (
            "Fever then skin macules/papules/scabs (thin-skinned areas), eye/nose discharge, lung lesions. Isolate, "
            "supportive care, topical antiseptic and antibiotic cover for secondary infection, report to authority, "
            "vaccinate per the official programme."
        ),
    },
    {
        "id": "cla", "name": "Caseous Lymphadenitis / Abscesses (C. pseudotuberculosis)",
        "keywords": ["caseous lymphadenitis", "pseudotuberculosis", "abscess", "cheesy gland", "lymph node abscess"],
        "species": ["goat", "sheep", "camel", "horse"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Firm/painful swellings of superficial lymph nodes (jaw, neck, prescapular) with thick cheesy pus. Do NOT "
            "burst them in the shed - the pus spreads the bacteria. A vet should lance a MATURE abscess, collect the "
            "pus, flush the cavity with dilute iodine and burn/bury the waste; isolate discharging animals; wear "
            "gloves (rarely zoonotic). Antibiotics alone rarely cure it."
        ),
    },
    # ------------------------------------------------------------------ POULTRY
    {
        "id": "newcastle", "name": "Newcastle Disease (Ranikhet)",
        "keywords": ["newcastle", "ranikhet", "ranikhet disease"],
        "species": ["poultry", "duck"],
        "notifiable": True, "zoonotic": True,
        "protocol": (
            "Sudden high mortality, greenish diarrhoea, gasping, twisted neck/paralysis, egg drop. No cure: isolate, "
            "biosecurity, report, supportive care (electrolytes, vitamins); antibiotics only for secondary bacterial "
            "infection. Prevent with a proper vaccination schedule (e.g. LaSota/Hitchner then boosters). Mild "
            "conjunctivitis possible in people handling sick birds - wear gloves."
        ),
    },
    {
        "id": "avian_influenza", "name": "Avian Influenza (Bird Flu)",
        "keywords": ["avian influenza", "bird flu", "hpai", "h5n1", "h9n2"],
        "species": ["poultry", "duck"],
        "notifiable": True, "zoonotic": True,
        "protocol": (
            "Sudden deaths, swollen/blue comb and wattles, facial oedema, respiratory signs, drop in eggs. Do NOT "
            "treat or move birds. Isolate, wear gloves/mask/eye protection, report to the authority immediately; "
            "culling/disposal only under official direction. Anyone with fever/cough after exposure must seek medical care."
        ),
    },
    {
        "id": "coccidiosis", "name": "Coccidiosis",
        "keywords": ["coccidiosis", "coccidia", "eimeria"],
        "species": ["poultry", "cattle", "goat", "sheep", "buffalo", "camel", "dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Bloody or watery droppings, ruffled feathers/dullness, weight loss, worst in young or crowded/wet-litter "
            "flocks (also calves and kids). Treat with an anticoccidial labelled for the species (e.g. amprolium or "
            "toltrazuril per label), with vitamins/electrolytes; observe withdrawal periods. Keep litter/bedding dry, "
            "avoid overcrowding, routine prevention per the vet."
        ),
    },
    {
        "id": "gumboro", "name": "Gumboro (Infectious Bursal Disease)",
        "keywords": ["gumboro", "infectious bursal", "ibd"],
        "species": ["poultry"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "3-6 week-old chicks: whitish watery diarrhoea, ruffled feathers, vent pecking, dehydration, sudden "
            "mortality peak. No specific treatment; supportive (electrolytes, vitamins, warmth), control secondary "
            "infections, strict biosecurity and disinfection, and a correct vaccination programme."
        ),
    },
    {
        "id": "crd", "name": "Chronic Respiratory Disease (Mycoplasma / E. coli)",
        "keywords": ["chronic respiratory disease", "crd", "mycoplasma gallisepticum", "infectious coryza", "coryza", "air sacculitis"],
        "species": ["poultry"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Sneezing, rattling breathing, nasal/eye discharge, swollen face (coryza), slow growth. Improve ventilation "
            "and litter, reduce dust/ammonia; antibiotic choice (e.g. macrolide or doxycycline) per vet after ruling out "
            "Newcastle/avian influenza; respect withdrawal periods; vaccinate/biosecurity for prevention."
        ),
    },
    # ------------------------------------------------------------------ DOGS / CATS
    {
        "id": "rabies", "name": "Rabies",
        "keywords": ["rabies", "hydrophobia"],
        "species": ["all"],
        "notifiable": True, "zoonotic": True,
        "protocol": (
            "Fatal viral disease of all mammals. Signs: behaviour change, aggression or unusual tameness, excessive "
            "drooling, difficulty swallowing, paralysis, bellowing (livestock). No treatment. Do not handle the animal "
            "without protection; isolate and report to the authority. ANY bite/scratch/saliva exposure: wash the wound "
            "with soap and running water for 15 minutes and go to a doctor immediately for post-exposure prophylaxis. "
            "Prevent by vaccinating dogs/cats and livestock in endemic areas."
        ),
    },
    {
        "id": "mange", "name": "Mange / Scabies (dogs, goats, sheep)",
        "keywords": ["mange", "scabies", "sarcoptes", "sarcoptic"],
        "species": ["dog", "goat", "sheep", "cat", "cattle", "horse", "donkey"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Intense itching, hair loss, crusts and thickened skin. Confirm with a skin scraping. Use a parasiticide "
            "labelled for the species (macrocyclic lactone, isoxazoline or approved acaricide dip per vet; in food "
            "animals respect withdrawal periods), treat all in-contact animals, clean bedding/housing, treat secondary "
            "infection. Sarcoptic mange can cause an itchy rash in people - wear gloves."
        ),
    },
    {
        "id": "parvo", "name": "Canine Parvovirus",
        "keywords": ["parvovirus", "parvo"],
        "species": ["dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Puppies: vomiting, bloody foul diarrhoea, severe lethargy, dehydration. EMERGENCY: hospital treatment with "
            "IV fluids, anti-vomiting drugs, antibiotics for secondary sepsis and nutritional support. Strict isolation, "
            "disinfect with diluted bleach, complete puppy vaccination series."
        ),
    },
    {
        "id": "distemper", "name": "Canine Distemper",
        "keywords": ["distemper"],
        "species": ["dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Fever, eye/nose discharge, cough, vomiting/diarrhoea, hard footpads, later twitching/seizures. No specific "
            "antiviral: supportive care, antibiotics for secondary infection, anticonvulsants when needed, strict "
            "isolation. Prevent by vaccination."
        ),
    },
    {
        "id": "panleuk", "name": "Feline Panleukopenia",
        "keywords": ["panleukopenia", "feline parvovirus", "feline distemper"],
        "species": ["cat"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Kittens: high fever, vomiting, diarrhoea, severe dehydration, very low white cells. Emergency supportive "
            "care with IV fluids, anti-vomiting drugs, antibiotics; isolate and disinfect thoroughly; vaccinate."
        ),
    },
    # ------------------------------------------------------------------ HORSES
    {
        "id": "strangles", "name": "Strangles (Streptococcus equi)",
        "keywords": ["strangles", "streptococcus equi"],
        "species": ["horse", "donkey"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Fever, thick nasal discharge, painful swelling and abscesses under the jaw/throat, difficulty swallowing. "
            "Isolate, strict hygiene, hot-compress mature abscesses so they drain; antibiotic use is selective (vet to "
            "decide - penicillin is used for early/complicated cases). Watch for breathing difficulty (emergency)."
        ),
    },
    {
        "id": "colic", "name": "Colic (horses / donkeys)",
        "keywords": ["colic"],
        "species": ["horse", "donkey"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Pawing, rolling, looking at flanks, sweating, no manure. TREAT AS AN EMERGENCY: remove feed, keep the "
            "animal safe, walk gently, do not give drugs that mask pain before a vet has examined it, and call a "
            "vet immediately - surgical colic can be fatal within hours."
        ),
    },
    {
        "id": "tetanus", "name": "Tetanus",
        "keywords": ["tetanus", "lockjaw"],
        "species": ["horse", "donkey", "goat", "sheep", "cattle", "buffalo", "camel", "dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Stiff 'sawhorse' stance, third eyelid flicking across the eye, locked jaw, sensitivity to noise. Vet care: "
            "tetanus antitoxin, penicillin, wound cleaning/debridement, muscle relaxants and sedation in a dark quiet "
            "stall with soft feed and water at head height. Prevent with tetanus toxoid vaccination and wound care."
        ),
    },
    # ------------------------------------------------------------------ CAMEL (dromedary)
    {
        "id": "camel_mange", "name": "Camel Mange (Sarcoptes scabiei var. cameli)",
        "keywords": ["mange", "scabies", "sarcoptes", "sarcoptic", "camel mange", "jarab", "khaarish"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "The most common skin disease of camels. Signs: intense itching/rubbing, hair loss, thickened wrinkled "
            "crusted skin usually starting on the head, neck, axillae and flanks; loss of condition. Confirm with a "
            "deep skin scraping. Typical treatment: ivermectin about 0.2 mg/kg subcutaneously, repeated after 10-14 "
            "days (vet to confirm dose and product; observe the label withdrawal period and do not use the milk "
            "from treated lactating camels until it is safe). Treat ALL in-contact camels, clean/burn contaminated "
            "bedding, rotate resting places, treat secondary bacterial infection, and improve nutrition. Zoonotic: "
            "herders may develop an itchy rash - wear gloves and wash after handling."
        ),
    },
    {
        "id": "camel_surra", "name": "Camel Trypanosomiasis (Surra, T. evansi)",
        "keywords": ["surra", "trypanosomiasis", "trypanosoma", "tibersa", "evansi"],
        "species": ["camel", "cattle", "buffalo", "horse", "donkey", "dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Spread by biting flies (Tabanus, Haematopota, Stomoxys). Signs: intermittent fever, progressive weight "
            "loss despite eating, anaemia, oedema of the belly/legs, rough coat, abortion, reduced milk, weakness. "
            "Confirm with a fresh/Giemsa blood smear, CATT/ELISA or PCR (negative smears do not rule it out). "
            "Treatment options used by vets: quinapyramine (typically about 3-5 mg/kg SC), melarsomine/Cymelarsan "
            "(about 0.25 mg/kg SC) or suramin (about 10 mg/kg IV) - vet to choose because drug resistance and relapse "
            "are common. Give supportive care (feed, minerals, haematinics), and control flies. Repeat blood testing "
            "after treatment."
        ),
    },
    {
        "id": "camel_pox", "name": "Camel Pox",
        "keywords": ["camel pox", "camelpox", "pox"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Orthopoxvirus; most severe in young camels. Signs: fever, swollen lymph nodes, skin papules/pustules and "
            "scabs on lips, muzzle, head, neck, udder and limbs; may cause mouth lesions and, in the generalised form, "
            "death. No antiviral: isolate, supportive feeding and water, topical antiseptic, antibiotics only for "
            "secondary infection, and vaccination of healthy herds with a camelpox vaccine per the vet/authority. "
            "Zoonotic: people (especially camel handlers) can develop hand or face lesions - wear gloves and wash hands. "
            "Report outbreaks to the local livestock authority."
        ),
    },
    {
        "id": "camel_ecthyma", "name": "Camel Contagious Ecthyma (Orf-like)",
        "keywords": ["ecthyma", "orf", "contagious ecthyma", "sore mouth"],
        "species": ["camel", "goat", "sheep"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Parapoxvirus. Proliferative scabby, cauliflower-like lesions on the lips, muzzle and around the mouth, "
            "difficulty feeding in young camels. Usually self-limiting over 3-6 weeks: soft feed, topical antiseptic, "
            "treat secondary infection, isolate affected animals. Zoonotic (people get painful finger/hand lesions) - "
            "wear gloves. Do not confuse with camel pox or FMD-like lesions: ask a vet to confirm."
        ),
    },
    {
        "id": "camel_papillomatosis", "name": "Camel Papillomatosis (Warts)",
        "keywords": ["papillomatosis", "warts", "papilloma"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Warty growths on the head, lips, neck and limbs of young camels. Usually resolves by itself in weeks to "
            "months. Vet may remove problem warts surgically or use an autogenous vaccine; keep wounds clean and "
            "control flies. Isolate heavily affected animals."
        ),
    },
    {
        "id": "camel_resp", "name": "Camel Respiratory Disease (Pneumonia)",
        "keywords": ["pneumonia", "respiratory disease", "camel respiratory", "bronchopneumonia"],
        "species": ["camel", "cattle", "buffalo", "goat", "sheep"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Fever, nasal discharge, coughing, laboured or open-mouth breathing, depression, off feed. Causes include "
            "Pasteurella, Mycoplasma, viruses and stress/dust. Separate from the herd, give shade, clean water and "
            "dust-free feed; a vet should choose an antibiotic (e.g. oxytetracycline or a macrolide) plus NSAID. Rule "
            "out notifiable respiratory diseases (e.g. HS, PPR, CCPP, MERS-CoV carriers in camels) when several "
            "animals are affected."
        ),
    },
    {
        "id": "camel_calf_diarrhoea", "name": "Camel Calf Diarrhoea",
        "keywords": ["camel calf diarrhoea", "camel calf diarrhea", "calf scour"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Common cause of camel calf loss: E. coli, rota/coronavirus, Cryptosporidium, Salmonella. Ensure early "
            "colostrum and clean, dry, shaded bedding. Treat dehydration first: oral rehydration solution frequently, "
            "IV fluids for weak/down calves, keep warm, keep milk feeding. Antibiotics only if fever, blood or "
            "systemic illness. Wash hands - some causes are zoonotic."
        ),
    },
    {
        "id": "camel_ringworm", "name": "Camel Ringworm (Dermatophytosis)",
        "keywords": ["ringworm", "dermatophytosis", "trichophyton", "fungal skin"],
        "species": ["camel", "cattle", "horse", "dog", "cat", "goat", "sheep"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Circular scaly hairless patches with crusts (camels: often head, neck, shoulders). Confirm by microscopy/"
            "culture. Isolate, remove crusts gently with gloves, apply a topical antifungal labelled for the species "
            "as directed by the vet, disinfect equipment/housing. Zoonotic: wear gloves and wash hands."
        ),
    },
    {
        "id": "camel_ticks", "name": "Camel Tick Infestation (Hyalomma)",
        "keywords": ["tick infestation", "ticks", "hyalomma", "tick infest"],
        "species": ["camel", "cattle", "buffalo", "goat", "sheep", "horse"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Ticks cause anaemia, skin damage, stress and carry blood parasites and CCHF virus (human risk). Remove ticks "
            "with gloves; use only acaricides labelled for camels or ask a vet - not all cattle products are safe in "
            "camels. Treat bedding/shelter, avoid heavy-tick pastures, and wear gloves to protect yourself from CCHF."
        ),
    },
    {
        "id": "camel_ionophore", "name": "Ionophore Poisoning in Camels (Monensin, Salinomycin, Lasalocid)",
        "keywords": ["ionophore", "monensin", "salinomycin", "lasalocid", "narasin", "feed poisoning"],
        "species": ["camel", "horse", "donkey", "dog"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Camels (and horses) are very sensitive to ionophore feed additives meant for poultry/cattle. Signs after "
            "eating contaminated feed: sudden weakness, staggering, recumbency, muscle tremor, breathing difficulty, "
            "dark (myoglobin) urine, sudden death. No antidote: stop the suspect feed immediately, keep the animal quiet "
            "and give fluids and supportive care under a vet. NEVER feed camels poultry/broiler feed or medicated "
            "cattle feed containing ionophores."
        ),
    },
    {
        "id": "camel_lameness", "name": "Camel Foot / Pad Injury and Lameness",
        "keywords": ["foot pad", "footpad", "pad injury", "lameness", "sole abscess", "foot rot", "thorn"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": False,
        "protocol": (
            "Camels get pad cuts, punctures, thorns and pad abscesses from hard/rocky or wet ground. Restrain safely, "
            "clean and inspect the sole, remove foreign bodies, drain abscesses (vet), apply antiseptic and a protective "
            "pad/bandage, NSAID for pain, check tetanus cover, and rest on soft dry ground. Rule out FMD if several "
            "animals are lame with mouth lesions."
        ),
    },
    {
        "id": "mers", "name": "MERS-CoV in Dromedary Camels (public-health note)",
        "keywords": ["mers", "mers-cov", "coronavirus", "middle east respiratory"],
        "species": ["camel"],
        "notifiable": False, "zoonotic": True,
        "protocol": (
            "Camels are the animal reservoir: infection is often mild or silent (runny nose, cough in young camels). "
            "Humans can be infected (especially with contact with sick camels, raw camel milk/urine or undercooked "
            "meat). Wear gloves and a mask when handling camels with respiratory signs, wash hands, boil/pasteurise "
            "milk, cook meat well. People who develop fever/cough after camel contact should seek medical care and "
            "tell the doctor about camel exposure; clusters should be reported to public-health authorities."
        ),
    },
]
