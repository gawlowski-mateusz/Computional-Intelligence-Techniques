"""Dataset for the diet planning problem.

Every product is described per *one portion* (portion size given in the name).
Nutritional values are approximate (based on typical food composition tables),
prices are approximate retail prices in PLN.
"""

NUTRIENTS = ["kcal", "protein", "fat", "carbs", "fiber"]
NUTRIENT_UNITS = {"kcal": "kcal", "protein": "g", "fat": "g", "carbs": "g", "fiber": "g"}

# name, kcal, protein [g], fat [g], carbs [g], fiber [g], price [PLN], max portions per day
PRODUCTS = [
    ("Płatki owsiane (100 g)",          370, 13.5,  7.0, 59.0, 10.0, 0.90, 2),
    ("Chleb pełnoziarnisty (100 g)",    240,  9.0,  3.0, 41.0,  7.0, 1.20, 3),
    ("Ryż biały (100 g, suchy)",        350,  7.0,  0.7, 78.0,  1.3, 0.80, 2),
    ("Makaron (100 g, suchy)",          350, 12.0,  1.5, 70.0,  3.0, 0.90, 2),
    ("Ziemniaki (200 g)",               150,  4.0,  0.2, 34.0,  3.0, 0.60, 3),
    ("Pierś z kurczaka (150 g)",        165, 34.0,  2.3,  0.0,  0.0, 4.00, 2),
    ("Jajka (2 szt.)",                  140, 12.5, 10.0,  0.7,  0.0, 1.60, 2),
    ("Twaróg półtłusty (100 g)",        130, 18.0,  4.5,  3.5,  0.0, 1.50, 2),
    ("Mleko 2% (250 ml)",               125,  8.0,  5.0, 12.0,  0.0, 0.90, 2),
    ("Jogurt naturalny (150 g)",         90,  6.0,  4.5,  7.0,  0.0, 1.20, 2),
    ("Łosoś (100 g)",                   200, 20.0, 13.0,  0.0,  0.0, 6.50, 1),
    ("Soczewica (100 g, sucha)",        350, 24.0,  1.5, 60.0, 11.0, 1.50, 1),
    ("Brokuł (200 g)",                   70,  5.6,  0.8, 14.0,  5.0, 2.00, 2),
    ("Marchew (150 g)",                  60,  1.4,  0.3, 14.0,  4.0, 0.50, 2),
    ("Pomidor (150 g)",                  27,  1.3,  0.3,  6.0,  1.8, 1.00, 2),
    ("Jabłko (180 g)",                   95,  0.5,  0.3, 25.0,  4.4, 0.80, 3),
    ("Banan (120 g)",                   105,  1.3,  0.4, 27.0,  3.0, 0.70, 2),
    ("Orzechy włoskie (30 g)",          195,  4.5, 19.5,  4.0,  2.0, 1.80, 2),
    ("Masło orzechowe (30 g)",          180,  7.5, 15.0,  6.0,  2.0, 0.90, 2),
    ("Ser żółty (30 g)",                105,  7.5,  8.5,  0.0,  0.0, 0.90, 3),
    ("Oliwa z oliwek (10 g)",            88,  0.0, 10.0,  0.0,  0.0, 0.40, 3),
]

# Daily requirements of the person: (min, max) for every nutrient.
# Example: man, 25 years, 75 kg, moderate physical activity (~2400 kcal/day).
REQUIREMENTS = {
    "kcal":    (2300, 2500),
    "protein": (90, 160),
    "fat":     (60, 90),
    "carbs":   (300, 380),
    "fiber":   (30, 60),
}
