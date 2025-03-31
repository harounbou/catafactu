CREATE TABLE IF NOT EXISTS products (
    reference TEXT PRIMARY KEY,
    denomination TEXT,
    quantite_initiale INTEGER,
    quantite_restockee INTEGER,
    quantite_vendue INTEGER,
    "couleurs-dispo-usine" TEXT,
    images TEXT,
    "prix-super-gros" REAL,
    "prix-gros" REAL,
    "prix-détail" REAL,
    uni_colour INTEGER DEFAULT 0,
    default_colour INTEGER DEFAULT 0,
    brown INTEGER DEFAULT 0,
    brown_deg INTEGER DEFAULT 0,
    blue INTEGER DEFAULT 0,
    white INTEGER DEFAULT 0,
    black INTEGER DEFAULT 0,
    green_bottle INTEGER DEFAULT 0,
    red INTEGER DEFAULT 0,
    grey INTEGER DEFAULT 0,
    grey_deg INTEGER DEFAULT 0,
    beige INTEGER DEFAULT 0,
    yellow INTEGER DEFAULT 0,
    orange INTEGER DEFAULT 0,
    garnet INTEGER DEFAULT 0,
    golden INTEGER DEFAULT 0,
    green INTEGER DEFAULT 0,
    rose INTEGER DEFAULT 0,
    note TEXT,
    category TEXT,
    quantite_vendu_actue INTEGER,
    last_updated TEXT,
    discontinued INTEGER DEFAULT 0,
    version INTEGER DEFAULT 0,
    quantite_actuelle INTEGER GENERATED ALWAYS AS (
        COALESCE(uni_colour, 0) + COALESCE(default_colour, 0) + 
        COALESCE(brown, 0) + COALESCE(brown_deg, 0) + 
        COALESCE(blue, 0) + COALESCE(white, 0) + 
        COALESCE(black, 0) + COALESCE(green_bottle, 0) + 
        COALESCE(red, 0) + COALESCE(grey, 0) + 
        COALESCE(grey_deg, 0) + COALESCE(beige, 0) + 
        COALESCE(yellow, 0) + COALESCE(orange, 0) + 
        COALESCE(garnet, 0) + COALESCE(golden, 0) + 
        COALESCE(green, 0) + COALESCE(rose, 0)
    ) STORED
);