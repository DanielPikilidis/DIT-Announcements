""" The website's announcement categories, keyed by taxonomy term ID.
Kept free of discord imports so scripts/make_category_emojis.py can use it too. """

# Same colours as the website (dit_theme/css/components/categories.css)
CATEGORY_COLOURS = {
    "56": 0x730071,     # Προπτυχιακά
    "57": 0xB7AAFF,     # Μεταπτυχιακά
    "58": 0x98CE00,     # Υποτροφίες Προπτυχιακών
    "59": 0xF5B700,     # Πρακτική Άσκηση
    "60": 0xF0A6CA,     # Διδακτορικά
    "61": 0xF71735,     # Προκηρύξεις Μεταπτυχιακών
    "62": 0xDC0073,     # Προκηρύξεις Διδακτορικών
    "131": 0x01FFFF,    # Νέες θέσεις εργασίας
    "132": 0x98CE00,    # Υποτροφίες Μεταπτυχιακών
    "133": 0x98CE00,    # Υποτροφίες Διδακτορικών
    "171": 0x0190D6,    # Γενικά
    "182": 0xEE7727,    # Προκηρύξεις Μελών ΔΕΠ
    "193": 0x6B9080,    # Erasmus+
    "210": 0x3A0CA3,    # ΠΜΣ Πληροφορική
    "211": 0x4361EE,    # ΠΜΣ Μηχανική Υπολογιστών, Τηλεπικοινωνιών και Δικτύων
    "212": 0xFF97B7,    # ΠΜΣ Τεχνολογίες Πληροφορικής και Επικοινωνιών
    "213": 0xA6808C     # ΔΠΜΣ Γλωσσική Τεχνολογία
}

# Fallback for categories without a term ID in the feed
CATEGORY_NAMES = {
    "Γενικά": "171", "Προπτυχιακά": "56", "Μεταπτυχιακά": "57", "Υποτροφίες Προπτυχιακών": "58",
    "Πρακτική Άσκηση": "59", "Διδακτορικά": "60", "Προκηρύξεις Μεταπτυχιακών": "61",
    "Προκηρύξεις Διδακτορικών": "62", "Νέες θέσεις εργασίας": "131",
    "Υποτροφίες Μεταπτυχιακών": "132", "Υποτροφίες Διδακτορικών": "133",
    "Προκηρύξεις Μελών ΔΕΠ": "182", "Erasmus+": "193", "ΠΜΣ Πληροφορική": "210",
    "ΠΜΣ Μηχανική Υπολογιστών, Τηλεπικοινωνιών και Δικτύων": "211",
    "ΠΜΣ Τεχνολογίες Πληροφορικής και Επικοινωνιών": "212",
    "ΔΠΜΣ Γλωσσική Τεχνολογία": "213", "CIVIS": "215"
}


# Diameter of the emoji circle as a share of the 128x128 image. Discord shows emojis in a fixed
# box, so the transparent padding is what makes the circle look smaller.
CIRCLE_RATIO = 0.6

# Every application emoji the bot manages starts with this. Old ones with it are deleted at startup.
EMOJI_PREFIX = "dit_cat_"

# Part of the emoji names, so changing CIRCLE_RATIO uploads new images instead of reusing the old ones
EMOJI_STYLE = f"s{round(CIRCLE_RATIO * 100)}"

def emoji_name(colour: int) -> str:
    """ Application emoji name for a colour. Categories with the same colour share one emoji. """
    return f"{EMOJI_PREFIX}{EMOJI_STYLE}_{colour:06x}"
