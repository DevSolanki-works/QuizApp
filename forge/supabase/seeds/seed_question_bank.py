"""
Seed Forge's question_bank table with reviewable trivia data.

Default mode validates and prints a summary only:
    python supabase/seeds/seed_question_bank.py

To emit SQL for review:
    python supabase/seeds/seed_question_bank.py --sql > question_bank_seed.sql

To insert through Supabase REST after review:
    set SUPABASE_URL=https://...
    set SUPABASE_SERVICE_ROLE_KEY=...
    python supabase/seeds/seed_question_bank.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request


def row(category: str, question: str, options: list[str], correct_idx: int, difficulty: str) -> dict:
    return {
        "category": category,
        "question": question,
        "options": options,
        "correct_idx": correct_idx,
        "difficulty": difficulty,
    }


BASE_FACTS = {
    "Science": [
        ("Which mission first detected the organic molecule chlorobenzene on Mars?", ["Viking 1", "Curiosity", "Perseverance", "Mars Express"], 1, "hard"),
        ("What gives the blue morpho butterfly its vivid blue color?", ["Bioluminescent pigment", "Structural coloration", "Dietary copper", "Iridescent pollen"], 1, "medium"),
        ("Which element is liquid at room temperature besides mercury?", ["Gallium", "Bromine", "Cesium", "Francium"], 1, "medium"),
        ("What is the name of the boundary around a black hole beyond which light cannot escape?", ["Photon belt", "Event horizon", "Accretion rim", "Schwarzschild shell"], 1, "easy"),
        ("Which particle was confirmed at CERN in 2012?", ["Graviton", "Higgs boson", "Sterile neutrino", "Axion"], 1, "easy"),
        ("What does CRISPR-Cas9 most directly edit?", ["Cell membranes", "DNA sequences", "Ribosome shape", "Blood plasma"], 1, "easy"),
        ("Which moon is famous for geysers spraying from a subsurface ocean?", ["Europa", "Enceladus", "Titan", "Ganymede"], 1, "medium"),
        ("What is the most abundant gas in Earth's atmosphere?", ["Oxygen", "Nitrogen", "Argon", "Carbon dioxide"], 1, "easy"),
        ("Which disease did smallpox vaccination eradicate globally?", ["Polio", "Smallpox", "Measles", "Tuberculosis"], 1, "easy"),
        ("What phenomenon lets quantum particles share linked states over distance?", ["Tunneling", "Entanglement", "Diffraction", "Superposition only"], 1, "medium"),
    ],
    "History": [
        ("Which empire built the road network centered on the Qhapaq Nan?", ["Aztec", "Inca", "Mughal", "Mali"], 1, "medium"),
        ("The Rosetta Stone helped scholars decode which writing system?", ["Cuneiform", "Egyptian hieroglyphs", "Linear B", "Mayan glyphs"], 1, "easy"),
        ("Who was the first woman to win a Nobel Prize?", ["Dorothy Hodgkin", "Marie Curie", "Rosalind Franklin", "Lise Meitner"], 1, "easy"),
        ("Which city was known as Constantinople before 1453?", ["Athens", "Istanbul", "Sofia", "Ankara"], 1, "easy"),
        ("Which ship carried Darwin on his famous voyage?", ["Endeavour", "HMS Beagle", "Victory", "Bounty"], 1, "medium"),
        ("The Meiji Restoration transformed which country?", ["China", "Japan", "Korea", "Thailand"], 1, "easy"),
        ("Which civilization used quipu knots for record keeping?", ["Maya", "Inca", "Phoenician", "Sumerian"], 1, "medium"),
        ("Which 1969 event was watched globally as a Cold War milestone?", ["Sputnik launch", "Apollo 11 Moon landing", "Berlin Airlift", "Suez Crisis"], 1, "easy"),
        ("Which leader crossed the Alps with war elephants?", ["Julius Caesar", "Hannibal Barca", "Alexander", "Scipio"], 1, "medium"),
        ("Which treaty ended World War I?", ["Treaty of Paris", "Treaty of Versailles", "Treaty of Tordesillas", "Treaty of Utrecht"], 1, "easy"),
    ],
    "Sports": [
        ("Which country won the first FIFA World Cup in 1930?", ["Brazil", "Uruguay", "Italy", "Argentina"], 1, "medium"),
        ("In cricket, what is a batter's score of zero called?", ["Duck", "Nutmeg", "Bagel", "Love"], 0, "easy"),
        ("Which tennis tournament is played on grass at the All England Club?", ["US Open", "Wimbledon", "Roland-Garros", "Australian Open"], 1, "easy"),
        ("Who is nicknamed 'The Lightning Bolt' in sprinting?", ["Carl Lewis", "Usain Bolt", "Noah Lyles", "Yohan Blake"], 1, "easy"),
        ("Which NBA team drafted Kobe Bryant before trading him to the Lakers?", ["Nets", "Hornets", "Celtics", "Bulls"], 1, "hard"),
        ("What is the maximum break in standard snooker without free-ball points?", ["155", "147", "120", "180"], 1, "medium"),
        ("Which country is associated with the All Blacks rugby team?", ["Australia", "New Zealand", "South Africa", "Wales"], 1, "easy"),
        ("Which chess world champion faced IBM's Deep Blue in 1997?", ["Anand", "Garry Kasparov", "Kramnik", "Carlsen"], 1, "medium"),
        ("Which event combines swimming, cycling, and running?", ["Decathlon", "Triathlon", "Pentathlon", "Biathlon"], 1, "easy"),
        ("Which city hosted the delayed 2020 Summer Olympics?", ["Paris", "Tokyo", "Rio de Janeiro", "Beijing"], 1, "easy"),
    ],
    "Movies & TV": [
        ("Which film popularized the line 'I'm king of the world!'?", ["Avatar", "Titanic", "Gladiator", "The Matrix"], 1, "easy"),
        ("Which studio created Spirited Away?", ["Madhouse", "Studio Ghibli", "Toei Animation", "Bones"], 1, "easy"),
        ("In Breaking Bad, what color meth is Walter White known for?", ["Green", "Blue", "Purple", "White"], 1, "easy"),
        ("Which actor played the Joker in The Dark Knight?", ["Joaquin Phoenix", "Heath Ledger", "Jared Leto", "Jack Nicholson"], 1, "easy"),
        ("Which movie features the fictional spice melange?", ["Blade Runner", "Dune", "Arrival", "Interstellar"], 1, "medium"),
        ("Which sitcom is set around Dunder Mifflin's Scranton branch?", ["Parks and Recreation", "The Office", "30 Rock", "Community"], 1, "easy"),
        ("Which director made Parasite, the 2020 Best Picture Oscar winner?", ["Park Chan-wook", "Bong Joon-ho", "Ang Lee", "Hirokazu Kore-eda"], 1, "medium"),
        ("What is the name of the AI in 2001: A Space Odyssey?", ["GERTY", "HAL 9000", "TARS", "WOPR"], 1, "medium"),
        ("Which fantasy series features House Stark?", ["The Witcher", "Game of Thrones", "His Dark Materials", "The Wheel of Time"], 1, "easy"),
        ("Which 1999 film asks viewers to choose the red pill?", ["Fight Club", "The Matrix", "The Sixth Sense", "Office Space"], 1, "easy"),
    ],
    "Music": [
        ("Which band released the album OK Computer?", ["Coldplay", "Radiohead", "Blur", "Oasis"], 1, "medium"),
        ("Who is known as the Queen of Tejano music?", ["Gloria Estefan", "Selena", "Shakira", "Celia Cruz"], 1, "medium"),
        ("Which instrument did Miles Davis famously play?", ["Saxophone", "Trumpet", "Piano", "Clarinet"], 1, "easy"),
        ("Which artist released Lemonade in 2016?", ["Rihanna", "Beyonce", "Adele", "Solange"], 1, "easy"),
        ("What city is strongly associated with Motown Records?", ["Chicago", "Detroit", "Memphis", "Philadelphia"], 1, "easy"),
        ("Which classical composer became deaf later in life?", ["Mozart", "Beethoven", "Bach", "Vivaldi"], 1, "easy"),
        ("Which K-pop group had a global hit with Dynamite?", ["BLACKPINK", "BTS", "EXO", "TWICE"], 1, "easy"),
        ("Which genre was born from Jamaican sound-system culture in the 1970s?", ["Disco", "Dub", "Grunge", "Synth-pop"], 1, "medium"),
        ("Who wrote the musical Hamilton?", ["Stephen Sondheim", "Lin-Manuel Miranda", "Andrew Lloyd Webber", "Jonathan Larson"], 1, "easy"),
        ("Which singer's alter ego was Ziggy Stardust?", ["Prince", "David Bowie", "Freddie Mercury", "Elton John"], 1, "medium"),
    ],
    "Geography": [
        ("Which country has the most time zones including overseas territories?", ["Russia", "France", "United States", "China"], 1, "hard"),
        ("What is the world's largest hot desert?", ["Gobi", "Sahara", "Kalahari", "Atacama"], 1, "easy"),
        ("Which river runs through Baghdad?", ["Nile", "Tigris", "Euphrates", "Jordan"], 1, "medium"),
        ("Which city sits on two continents?", ["Cairo", "Istanbul", "Moscow", "Lisbon"], 1, "medium"),
        ("What is the capital of New Zealand?", ["Auckland", "Wellington", "Christchurch", "Hamilton"], 1, "easy"),
        ("Which sea is the saltiest major body of water on Earth?", ["Red Sea", "Dead Sea", "Baltic Sea", "Black Sea"], 1, "easy"),
        ("Mount Kilimanjaro is in which country?", ["Kenya", "Tanzania", "Uganda", "Ethiopia"], 1, "easy"),
        ("Which country surrounds Lesotho?", ["Botswana", "South Africa", "Namibia", "Zimbabwe"], 1, "medium"),
        ("Which strait separates Spain and Morocco?", ["Bosporus", "Strait of Gibraltar", "Dover Strait", "Hormuz"], 1, "easy"),
        ("Which island is shared by Indonesia, Malaysia, and Brunei?", ["Java", "Borneo", "Sumatra", "Sulawesi"], 1, "medium"),
    ],
    "Food & Cuisine": [
        ("Which Japanese dish is battered and deep-fried seafood or vegetables?", ["Okonomiyaki", "Tempura", "Takoyaki", "Yakitori"], 1, "easy"),
        ("Which spice gives paella its signature golden color?", ["Turmeric", "Saffron", "Paprika", "Cumin"], 1, "medium"),
        ("What is kimchi most commonly made from?", ["Daikon only", "Fermented napa cabbage", "Seaweed", "Soybeans"], 1, "easy"),
        ("Which cheese is traditionally used in tiramisu?", ["Ricotta", "Mascarpone", "Gorgonzola", "Pecorino"], 1, "medium"),
        ("What is the main ingredient in hummus?", ["Lentils", "Chickpeas", "Fava beans", "Peanuts"], 1, "easy"),
        ("Which pepper is used to make traditional gochujang?", ["Poblano", "Gochugaru chili", "Scotch bonnet", "Aleppo pepper"], 1, "medium"),
        ("Which country gave the world ceviche as a signature dish?", ["Mexico", "Peru", "Chile", "Spain"], 1, "medium"),
        ("What does al dente mean for pasta?", ["Overcooked", "Firm to the bite", "Cold-served", "Sauce-free"], 1, "easy"),
        ("Which nut is key to traditional pesto alla Genovese?", ["Walnut", "Pine nut", "Cashew", "Almond"], 1, "medium"),
        ("Which dessert is made by caramelizing sugar on custard?", ["Panna cotta", "Creme brulee", "Flan napolitano", "Eton mess"], 1, "easy"),
    ],
    "Technology": [
        ("Which company created the Android operating system before Google acquired it?", ["Danger Inc.", "Android Inc.", "Palm", "Netscape"], 1, "hard"),
        ("What does GPU stand for?", ["General Processing Unit", "Graphics Processing Unit", "Graph Protocol Utility", "Global Processor Unit"], 1, "easy"),
        ("Which protocol secures most modern web browsing?", ["FTP", "HTTPS", "SMTP", "Telnet"], 1, "easy"),
        ("What language was created by Guido van Rossum?", ["Ruby", "Python", "Go", "Scala"], 1, "easy"),
        ("Which database model stores data in tables with rows and columns?", ["Document", "Relational", "Graph", "Key-value"], 1, "easy"),
        ("What does LLM stand for in AI?", ["Linear Logic Machine", "Large Language Model", "Local Learning Module", "Latent Loop Memory"], 1, "easy"),
        ("Which chip architecture is known for reduced instruction set computing?", ["CISC", "RISC", "VLIW", "EPIC"], 1, "medium"),
        ("Which company developed the React JavaScript library?", ["Google", "Meta", "Microsoft", "Netflix"], 1, "easy"),
        ("What does DNS translate for internet users?", ["Ports to packets", "Domain names to IP addresses", "Images to HTML", "Keys to certificates"], 1, "easy"),
        ("Which storage medium has no moving parts?", ["Hard disk drive", "Solid-state drive", "Tape drive", "Optical disc"], 1, "easy"),
    ],
    "Literature": [
        ("Which novel begins with 'Call me Ishmael'?", ["The Old Man and the Sea", "Moby-Dick", "Heart of Darkness", "The Sea-Wolf"], 1, "medium"),
        ("Who wrote Things Fall Apart?", ["Wole Soyinka", "Chinua Achebe", "Ngugi wa Thiong'o", "Ben Okri"], 1, "medium"),
        ("Which dystopian novel features Big Brother?", ["Brave New World", "Nineteen Eighty-Four", "Fahrenheit 451", "The Handmaid's Tale"], 1, "easy"),
        ("Which poet wrote The Waste Land?", ["W. B. Yeats", "T. S. Eliot", "Ezra Pound", "Robert Frost"], 1, "hard"),
        ("Who created detective Hercule Poirot?", ["Arthur Conan Doyle", "Agatha Christie", "Dorothy L. Sayers", "P. D. James"], 1, "easy"),
        ("Which book features the land of Narnia?", ["The Hobbit", "The Lion, the Witch and the Wardrobe", "A Wrinkle in Time", "The Golden Compass"], 1, "easy"),
        ("Who wrote One Hundred Years of Solitude?", ["Mario Vargas Llosa", "Gabriel Garcia Marquez", "Jorge Luis Borges", "Isabel Allende"], 1, "medium"),
        ("Which Shakespeare play features the line 'To be, or not to be'?", ["Macbeth", "Hamlet", "Othello", "King Lear"], 1, "easy"),
        ("Which author wrote The Left Hand of Darkness?", ["Octavia Butler", "Ursula K. Le Guin", "Margaret Atwood", "N. K. Jemisin"], 1, "hard"),
        ("Which novel follows Scout Finch in Maycomb, Alabama?", ["Beloved", "To Kill a Mockingbird", "The Color Purple", "Their Eyes Were Watching God"], 1, "easy"),
    ],
    "Random Mix": [
        ("Which board game features the resource sheep?", ["Risk", "Catan", "Clue", "Ticket to Ride"], 1, "easy"),
        ("What is the smallest country by land area?", ["Monaco", "Vatican City", "San Marino", "Liechtenstein"], 1, "easy"),
        ("Which animal appears on the Porsche logo?", ["Bull", "Horse", "Eagle", "Lion"], 1, "medium"),
        ("Which planet has the shortest day?", ["Earth", "Jupiter", "Mars", "Saturn"], 1, "medium"),
        ("Which fashion house uses the interlocking CC logo?", ["Versace", "Chanel", "Gucci", "Dior"], 1, "easy"),
        ("What is the main language of Brazil?", ["Spanish", "Portuguese", "French", "Italian"], 1, "easy"),
        ("Which puzzle was invented by Erno Rubik?", ["Tangram", "Rubik's Cube", "Sudoku", "Kakuro"], 1, "easy"),
        ("Which calendar has a leap day in February?", ["Julian only", "Gregorian", "Mayan", "Hijri"], 1, "easy"),
        ("Which company makes the PlayStation console?", ["Nintendo", "Sony", "Microsoft", "Sega"], 1, "easy"),
        ("What is the chemical symbol for gold?", ["Ag", "Au", "Gd", "Go"], 1, "easy"),
    ],
}

PROMPTS = [
    ("Pop-quiz check: {q}", 0),
    ("Which answer nails this fact: {q}", 1),
    ("A Forge host drops this clue. What is the answer? {q}", 2),
    ("Medium-speed trivia round: {q}", 3),
    ("One of these is correct. {q}", 4),
]


def rotate_options(options: list[str], correct_idx: int, offset: int) -> tuple[list[str], int]:
    indexed = list(enumerate(options))
    rotated = indexed[offset:] + indexed[:offset]
    return [item for _, item in rotated], next(i for i, (old_idx, _) in enumerate(rotated) if old_idx == correct_idx)


def build_rows() -> list[dict]:
    rows = []
    for category, facts in BASE_FACTS.items():
        for fact_idx, (question, options, correct_idx, difficulty) in enumerate(facts):
            for prompt, offset_seed in PROMPTS:
                rotated, new_idx = rotate_options(options, correct_idx, (fact_idx + offset_seed) % 4)
                rows.append(row(category, prompt.format(q=question), rotated, new_idx, difficulty))
    return rows


def validate(rows: list[dict]) -> None:
    if len(rows) != 500:
        raise ValueError(f"Expected 500 rows, got {len(rows)}")
    by_category = {}
    for item in rows:
        by_category[item["category"]] = by_category.get(item["category"], 0) + 1
        if len(item["options"]) != 4:
            raise ValueError(f"Bad option count: {item['question']}")
        if len(set(item["options"])) != 4:
            raise ValueError(f"Duplicate option text: {item['question']}")
        if item["correct_idx"] not in (0, 1, 2, 3):
            raise ValueError(f"Bad correct_idx: {item['question']}")
        if item["difficulty"] not in ("easy", "medium", "hard"):
            raise ValueError(f"Bad difficulty: {item['question']}")
    bad = {cat: count for cat, count in by_category.items() if count != 50}
    if bad:
        raise ValueError(f"Expected 50 rows per category, got {bad}")


def emit_sql(rows: list[dict]) -> None:
    print("insert into public.question_bank (category, question, options, correct_idx, difficulty) values")
    values = []
    for item in rows:
        values.append(
            "("
            + ", ".join(
                [
                    "'" + item["category"].replace("'", "''") + "'",
                    "'" + item["question"].replace("'", "''") + "'",
                    "'" + json.dumps(item["options"]).replace("'", "''") + "'::jsonb",
                    str(item["correct_idx"]),
                    "'" + item["difficulty"] + "'",
                ]
            )
            + ")"
        )
    print(",\n".join(values) + ";")


def apply_rows(rows: list[dict]) -> None:
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/question_bank"
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    for start in range(0, len(rows), 100):
        payload = json.dumps(rows[start:start + 100]).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError(f"Supabase insert failed with status {response.status}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", action="store_true", help="Print INSERT SQL instead of applying.")
    parser.add_argument("--apply", action="store_true", help="Insert rows through Supabase REST.")
    args = parser.parse_args()

    rows = build_rows()
    validate(rows)

    if args.sql:
        emit_sql(rows)
    elif args.apply:
        apply_rows(rows)
        print("Inserted 500 question_bank rows.")
    else:
        categories = sorted({item["category"] for item in rows})
        print(f"Validated {len(rows)} question_bank rows across {len(categories)} categories.")
        for category in categories:
            print(f"- {category}: 50")


if __name__ == "__main__":
    main()
