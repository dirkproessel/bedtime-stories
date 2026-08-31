export interface KdpMarketplaceInfo {
    id: string;
    label: string;
    flag: string;
    country: string;
    currency: string;
    defaultLang: string;
}

export const KDP_MARKETPLACES: KdpMarketplaceInfo[] = [
    { id: 'amazon.de', label: 'Amazon.de', flag: '🇩🇪', country: 'Deutschland / AT / CH', currency: 'EUR', defaultLang: 'de' },
    { id: 'amazon.com', label: 'Amazon.com', flag: '🇺🇸', country: 'USA & Global', currency: 'USD', defaultLang: 'en' },
    { id: 'amazon.co.uk', label: 'Amazon.co.uk', flag: '🇬🇧', country: 'Großbritannien', currency: 'GBP', defaultLang: 'en' },
    { id: 'amazon.fr', label: 'Amazon.fr', flag: '🇫🇷', country: 'Frankreich', currency: 'EUR', defaultLang: 'fr' },
    { id: 'amazon.es', label: 'Amazon.es', flag: '🇪🇸', country: 'Spanien', currency: 'EUR', defaultLang: 'es' },
    { id: 'amazon.it', label: 'Amazon.it', flag: '🇮🇹', country: 'Italien', currency: 'EUR', defaultLang: 'it' },
];

export interface KdpCategoryDefinition {
    id: string;
    mainCategory: string;
    subCategory: string;
    leaf: string;
    path: string;
    breadcrumbs: string[];
    marketplace: 'de' | 'en' | 'all';
    tags: string[];
    ageHint?: string;
}

export const KDP_CATEGORIES_DE: KdpCategoryDefinition[] = [
    // --- KINDERBÜCHER ---
    {
        id: 'de-kids-bedtime',
        mainCategory: 'Kinderbücher',
        subCategory: 'Gutenachtgeschichten & Träume',
        leaf: 'Gutenachtgeschichten & Träume',
        path: 'Kinderbücher > Gutenachtgeschichten & Träume',
        breadcrumbs: ['Kinderbücher', 'Gutenachtgeschichten & Träume'],
        marketplace: 'de',
        tags: ['einschlafen', 'schlaf', 'gutenacht', 'traum', 'abend', 'vorlesen', 'ruhe', 'bett'],
        ageHint: '0–6 Jahre'
    },
    {
        id: 'de-kids-animals-farm',
        mainCategory: 'Kinderbücher',
        subCategory: 'Tiere',
        leaf: 'Bauernhoftiere',
        path: 'Kinderbücher > Tiere > Bauernhoftiere',
        breadcrumbs: ['Kinderbücher', 'Tiere', 'Bauernhoftiere'],
        marketplace: 'de',
        tags: ['tiere', 'bauernhof', 'kuh', 'schaf', 'schwein', 'huhn', 'pferd', 'landleben'],
        ageHint: '2–6 Jahre'
    },
    {
        id: 'de-kids-animals-pets',
        mainCategory: 'Kinderbücher',
        subCategory: 'Tiere',
        leaf: 'Haustiere (Hunde & Katzen)',
        path: 'Kinderbücher > Tiere > Haustiere',
        breadcrumbs: ['Kinderbücher', 'Tiere', 'Haustiere'],
        marketplace: 'de',
        tags: ['hunde', 'katzen', 'haustiere', 'welpe', 'kätzchen', 'meerschweinchen'],
        ageHint: '3–8 Jahre'
    },
    {
        id: 'de-kids-animals-wild',
        mainCategory: 'Kinderbücher',
        subCategory: 'Tiere',
        leaf: 'Wildtiere & Waldtiere',
        path: 'Kinderbücher > Tiere > Wildtiere & Waldtiere',
        breadcrumbs: ['Kinderbücher', 'Tiere', 'Wildtiere & Waldtiere'],
        marketplace: 'de',
        tags: ['fuchs', 'bär', 'reh', 'eule', 'wald', 'safari', 'löwe', 'elefant', 'dschungel'],
        ageHint: '3–8 Jahre'
    },
    {
        id: 'de-kids-animals-dino',
        mainCategory: 'Kinderbücher',
        subCategory: 'Tiere',
        leaf: 'Dinosaurier',
        path: 'Kinderbücher > Tiere > Dinosaurier',
        breadcrumbs: ['Kinderbücher', 'Tiere', 'Dinosaurier'],
        marketplace: 'de',
        tags: ['dino', 'dinosaurier', 't-rex', 'urzeit', 'triceratops'],
        ageHint: '3–8 Jahre'
    },
    {
        id: 'de-kids-picture-verse',
        mainCategory: 'Kinderbücher',
        subCategory: 'Bilderbücher & Vorlesebücher',
        leaf: 'Reime & Lieder',
        path: 'Kinderbücher > Bilderbücher & Vorlesebücher > Reime & Lieder',
        breadcrumbs: ['Kinderbücher', 'Bilderbücher & Vorlesebücher', 'Reime & Lieder'],
        marketplace: 'de',
        tags: ['reime', 'verse', 'gedichte', 'lieder', 'reimend', 'rhythmus'],
        ageHint: '1–5 Jahre'
    },
    {
        id: 'de-kids-picture-early',
        mainCategory: 'Kinderbücher',
        subCategory: 'Bilderbücher & Vorlesebücher',
        leaf: 'Erstes Lesen & Wortschatz',
        path: 'Kinderbücher > Bilderbücher & Vorlesebücher > Erstes Lesen & Wortschatz',
        breadcrumbs: ['Kinderbücher', 'Bilderbücher & Vorlesebücher', 'Erstes Lesen & Wortschatz'],
        marketplace: 'de',
        tags: ['erstleser', 'wortschatz', 'farben', 'zahlen', 'sprachentwicklung'],
        ageHint: '2–6 Jahre'
    },
    {
        id: 'de-kids-emotions-courage',
        mainCategory: 'Kinderbücher',
        subCategory: 'Alltag, Familie & Gefühle',
        leaf: 'Mut & Selbstvertrauen',
        path: 'Kinderbücher > Alltag, Familie & Gefühle > Mut & Selbstvertrauen',
        breadcrumbs: ['Kinderbücher', 'Alltag, Familie & Gefühle', 'Mut & Selbstvertrauen'],
        marketplace: 'de',
        tags: ['mut', 'selbstvertrauen', 'stark', 'angst', 'überwinden', 'selbstliebe'],
        ageHint: '3–8 Jahre'
    },
    {
        id: 'de-kids-emotions-friendship',
        mainCategory: 'Kinderbücher',
        subCategory: 'Alltag, Familie & Gefühle',
        leaf: 'Freundschaft & Teilen',
        path: 'Kinderbücher > Alltag, Familie & Gefühle > Freundschaft & Teilen',
        breadcrumbs: ['Kinderbücher', 'Alltag, Familie & Gefühle', 'Freundschaft & Teilen'],
        marketplace: 'de',
        tags: ['freunde', 'freundschaft', 'teilen', 'zusammenhalt', 'miteinander', 'streit'],
        ageHint: '3–8 Jahre'
    },
    {
        id: 'de-kids-emotions-kindergarten',
        mainCategory: 'Kinderbücher',
        subCategory: 'Alltag, Familie & Gefühle',
        leaf: 'Kindergarten & Schulstart',
        path: 'Kinderbücher > Alltag, Familie & Gefühle > Kindergarten & Schulstart',
        breadcrumbs: ['Kinderbücher', 'Alltag, Familie & Gefühle', 'Kindergarten & Schulstart'],
        marketplace: 'de',
        tags: ['kita', 'kindergarten', 'einschulung', 'schule', 'eingewöhnung', 'geschwister'],
        ageHint: '2–7 Jahre'
    },
    {
        id: 'de-kids-fantasy-magic',
        mainCategory: 'Kinderbücher',
        subCategory: 'Fantasy, Magie & Märchen',
        leaf: 'Zauberer, Feen & Magie',
        path: 'Kinderbücher > Fantasy, Magie & Märchen > Zauberer, Feen & Magie',
        breadcrumbs: ['Kinderbücher', 'Fantasy, Magie & Märchen', 'Zauberer, Feen & Magie'],
        marketplace: 'de',
        tags: ['magie', 'fee', 'zauberer', 'einhorn', 'drache', 'zauberwald', 'fabelwesen'],
        ageHint: '4–10 Jahre'
    },
    {
        id: 'de-kids-fantasy-fairytales',
        mainCategory: 'Kinderbücher',
        subCategory: 'Fantasy, Magie & Märchen',
        leaf: 'Märchen, Volkssagen & Fabeln',
        path: 'Kinderbücher > Fantasy, Magie & Märchen > Märchen & Fabeln',
        breadcrumbs: ['Kinderbücher', 'Fantasy, Magie & Märchen', 'Märchen & Fabeln'],
        marketplace: 'de',
        tags: ['märchen', 'fabel', 'saga', 'prinzessin', 'könig', 'burg', 'ritter'],
        ageHint: '4–10 Jahre'
    },
    {
        id: 'de-kids-adventure',
        mainCategory: 'Kinderbücher',
        subCategory: 'Abenteuer & Entdecker',
        leaf: 'Piraten, Detektive & Expeditionen',
        path: 'Kinderbücher > Abenteuer & Entdecker > Piraten, Detektive & Expeditionen',
        breadcrumbs: ['Kinderbücher', 'Abenteuer & Entdecker', 'Piraten, Detektive & Expeditionen'],
        marketplace: 'de',
        tags: ['pirat', 'schatz', 'detektiv', 'rätsel', 'expedition', 'entdecker', 'insel'],
        ageHint: '5–10 Jahre'
    },
    {
        id: 'de-kids-humor',
        mainCategory: 'Kinderbücher',
        subCategory: 'Humor & Lustiges',
        leaf: 'Lustige Geschichten & Quatsch',
        path: 'Kinderbücher > Humor & Lustiges > Lustige Geschichten',
        breadcrumbs: ['Kinderbücher', 'Humor & Lustiges', 'Lustige Geschichten'],
        marketplace: 'de',
        tags: ['lustig', 'humor', 'lachen', 'spaß', 'streiche', 'komisch'],
        ageHint: '3–9 Jahre'
    },
    {
        id: 'de-kids-knowledge',
        mainCategory: 'Kinderbücher',
        subCategory: 'Sachwissen für Kinder',
        leaf: 'Natur, Tiere & Umwelt',
        path: 'Kinderbücher > Sachwissen für Kinder > Natur, Tiere & Umwelt',
        breadcrumbs: ['Kinderbücher', 'Sachwissen für Kinder', 'Natur, Tiere & Umwelt'],
        marketplace: 'de',
        tags: ['sachbuch', 'wissen', 'natur', 'wald', 'ozean', 'bienen', 'umweltschutz'],
        ageHint: '5–10 Jahre'
    },
    {
        id: 'de-kids-holidays-xmas',
        mainCategory: 'Kinderbücher',
        subCategory: 'Feste & Feiertage',
        leaf: 'Weihnachten & Winter',
        path: 'Kinderbücher > Feste & Feiertage > Weihnachten & Winter',
        breadcrumbs: ['Kinderbücher', 'Feste & Feiertage', 'Weihnachten & Winter'],
        marketplace: 'de',
        tags: ['weihnachten', 'advent', 'schnee', 'winter', 'nikolaus', 'weihnachtsmann'],
        ageHint: '2–8 Jahre'
    },

    // --- BELLETRISTIK ---
    {
        id: 'de-fiction-fantasy-epic',
        mainCategory: 'Belletristik',
        subCategory: 'Fantasy',
        leaf: 'Epische Fantasy & High Fantasy',
        path: 'Belletristik > Fantasy > Epische Fantasy',
        breadcrumbs: ['Belletristik', 'Fantasy', 'Epische Fantasy'],
        marketplace: 'de',
        tags: ['high fantasy', 'episch', 'weltenerbauung', 'schwerter', 'königreiche', 'drachen', 'magie']
    },
    {
        id: 'de-fiction-fantasy-urban',
        mainCategory: 'Belletristik',
        subCategory: 'Fantasy',
        leaf: 'Urban Fantasy & Paranormal',
        path: 'Belletristik > Fantasy > Urban Fantasy',
        breadcrumbs: ['Belletristik', 'Fantasy', 'Urban Fantasy'],
        marketplace: 'de',
        tags: ['urban fantasy', 'großstadt', 'vampire', 'gestaltwandler', 'magie heute', 'paranormal']
    },
    {
        id: 'de-fiction-fantasy-romantasy',
        mainCategory: 'Belletristik',
        subCategory: 'Fantasy',
        leaf: 'Romantasy & Romantic Fantasy',
        path: 'Belletristik > Fantasy > Romantic Fantasy',
        breadcrumbs: ['Belletristik', 'Fantasy', 'Romantic Fantasy'],
        marketplace: 'de',
        tags: ['romantasy', 'fantasy liebesroman', 'feen', 'hof', 'enemies to lovers', 'liebe & magie']
    },
    {
        id: 'de-fiction-scifi-spaceopera',
        mainCategory: 'Belletristik',
        subCategory: 'Science-Fiction',
        leaf: 'Space Opera & Galaktische Reiche',
        path: 'Belletristik > Science-Fiction > Space Opera',
        breadcrumbs: ['Belletristik', 'Science-Fiction', 'Space Opera'],
        marketplace: 'de',
        tags: ['raumschiffe', 'weltall', 'sterne', 'galaxis', 'imperium', 'alien', 'flotte']
    },
    {
        id: 'de-fiction-scifi-dystopian',
        mainCategory: 'Belletristik',
        subCategory: 'Science-Fiction',
        leaf: 'Dystopien & Postapokalypse',
        path: 'Belletristik > Science-Fiction > Dystopien',
        breadcrumbs: ['Belletristik', 'Science-Fiction', 'Dystopien'],
        marketplace: 'de',
        tags: ['dystopie', 'endzeit', 'überleben', 'zukunft', 'widerstand', 'gesellschaftskritik']
    },
    {
        id: 'de-fiction-scifi-hard',
        mainCategory: 'Belletristik',
        subCategory: 'Science-Fiction',
        leaf: 'Hard Sci-Fi, KI & Cyberpunk',
        path: 'Belletristik > Science-Fiction > Hard Science-Fiction',
        breadcrumbs: ['Belletristik', 'Science-Fiction', 'Hard Science-Fiction'],
        marketplace: 'de',
        tags: ['hard scifi', 'ki', 'künstliche intelligenz', 'cyberpunk', 'zeitreisen', 'quanten']
    },
    {
        id: 'de-fiction-crime-psycho',
        mainCategory: 'Belletristik',
        subCategory: 'Krimis & Thriller',
        leaf: 'Psychothriller',
        path: 'Belletristik > Krimis & Thriller > Psychothriller',
        breadcrumbs: ['Belletristik', 'Krimis & Thriller', 'Psychothriller'],
        marketplace: 'de',
        tags: ['psychothriller', 'nervenkitzel', 'abgründe', 'serienkiller', 'spannung', 'plot twist']
    },
    {
        id: 'de-fiction-crime-cozy',
        mainCategory: 'Belletristik',
        subCategory: 'Krimis & Thriller',
        leaf: 'Cosy Mystery & Regionalkrimi',
        path: 'Belletristik > Krimis & Thriller > Cosy Mystery',
        breadcrumbs: ['Belletristik', 'Krimis & Thriller', 'Cosy Mystery'],
        marketplace: 'de',
        tags: ['cosy crime', 'gemütlich', 'dörflich', 'humorvoll', 'regionalkrimi', 'hobbyermittler']
    },
    {
        id: 'de-fiction-romance-contemporary',
        mainCategory: 'Belletristik',
        subCategory: 'Liebesromane',
        leaf: 'Contemporary & Romantische Komödie',
        path: 'Belletristik > Liebesromane > Contemporary Romance',
        breadcrumbs: ['Belletristik', 'Liebesromane', 'Contemporary Romance'],
        marketplace: 'de',
        tags: ['romcom', 'zeitgenössisch', 'liebe', 'humorvoll', 'herzschmerz', 'happy end']
    },
    {
        id: 'de-fiction-historical',
        mainCategory: 'Belletristik',
        subCategory: 'Historische Romane',
        leaf: 'Mittelalter, Antike & 20. Jahrhundert',
        path: 'Belletristik > Historische Romane > Historischer Roman',
        breadcrumbs: ['Belletristik', 'Historische Romane', 'Historischer Roman'],
        marketplace: 'de',
        tags: ['geschichte', 'mittelalter', 'weltkrieg', 'jahrhundertwende', 'historisch', 'saga']
    },
    {
        id: 'de-fiction-short',
        mainCategory: 'Belletristik',
        subCategory: 'Kurzgeschichten',
        leaf: 'Kurzgeschichten & Anthologien',
        path: 'Belletristik > Kurzgeschichten & Anthologien',
        breadcrumbs: ['Belletristik', 'Kurzgeschichten & Anthologien'],
        marketplace: 'de',
        tags: ['kurzgeschichten', 'novelle', 'anthologie', 'erzählungen', 'sammelband']
    },

    // --- JUGENDBÜCHER (YA) ---
    {
        id: 'de-ya-fantasy',
        mainCategory: 'Jugendbücher',
        subCategory: 'Fantasy & Romantasy',
        leaf: 'Magische Akademien & Dystopien',
        path: 'Jugendbücher > Fantasy & Romantasy',
        breadcrumbs: ['Jugendbücher', 'Fantasy & Romantasy'],
        marketplace: 'de',
        tags: ['ya fantasy', 'magische akademie', 'jugendbuch', 'erste liebe', 'hexen'],
        ageHint: '12–18 Jahre'
    },
    {
        id: 'de-ya-romance',
        mainCategory: 'Jugendbücher',
        subCategory: 'Romantik & Coming-of-Age',
        leaf: 'Erste Liebe & Highschool',
        path: 'Jugendbücher > Romantik & Coming-of-Age',
        breadcrumbs: ['Jugendbücher', 'Romantik & Coming-of-Age'],
        marketplace: 'de',
        tags: ['coming of age', 'highschool', 'erste liebe', 'drama', 'freundschaft'],
        ageHint: '12–18 Jahre'
    },

    // --- SACHBUCH & RATGEBER ---
    {
        id: 'de-nonfiction-selfhelp',
        mainCategory: 'Sachbuch & Ratgeber',
        subCategory: 'Ratgeber & Lebensführung',
        leaf: 'Achtsamkeit, Meditation & Persönlichkeitsentwicklung',
        path: 'Sachbuch & Ratgeber > Ratgeber & Lebensführung > Achtsamkeit',
        breadcrumbs: ['Sachbuch & Ratgeber', 'Ratgeber & Lebensführung', 'Achtsamkeit'],
        marketplace: 'de',
        tags: ['achtsamkeit', 'meditation', 'stressabbau', 'persönlichkeitsentwicklung', 'selbsthilfe', 'glück']
    },
    {
        id: 'de-nonfiction-health',
        mainCategory: 'Sachbuch & Ratgeber',
        subCategory: 'Gesundheit, Geist & Körper',
        leaf: 'Mentale Gesundheit, Fitness & Ernährung',
        path: 'Sachbuch & Ratgeber > Gesundheit, Geist & Körper > Mentale Gesundheit',
        breadcrumbs: ['Sachbuch & Ratgeber', 'Gesundheit, Geist & Körper', 'Mentale Gesundheit'],
        marketplace: 'de',
        tags: ['gesundheit', 'psyche', 'resilienz', 'fitness', 'schlaf', 'darmgesundheit']
    },
    {
        id: 'de-nonfiction-family',
        mainCategory: 'Sachbuch & Ratgeber',
        subCategory: 'Eltern & Familie',
        leaf: 'Babyjahre & Kindererziehung',
        path: 'Sachbuch & Ratgeber > Eltern & Familie > Erziehung',
        breadcrumbs: ['Sachbuch & Ratgeber', 'Eltern & Familie', 'Erziehung'],
        marketplace: 'de',
        tags: ['eltern', 'baby', 'trotzphase', 'erziehung', 'schwangerschaft', 'pädagogik']
    },
    {
        id: 'de-nonfiction-business',
        mainCategory: 'Sachbuch & Ratgeber',
        subCategory: 'Wirtschaft & Finanzen',
        leaf: 'Geldanlage, Unternehmertum & Karriere',
        path: 'Sachbuch & Ratgeber > Wirtschaft & Finanzen > Geldanlage & Unternehmertum',
        breadcrumbs: ['Sachbuch & Ratgeber', 'Wirtschaft & Finanzen', 'Geldanlage & Unternehmertum'],
        marketplace: 'de',
        tags: ['finanzen', 'aktien', 'etfs', 'startup', 'unternehmer', 'führung', 'passives einkommen']
    }
];

export const KDP_CATEGORIES_EN: KdpCategoryDefinition[] = [
    // --- CHILDREN'S BOOKS ---
    {
        id: 'en-kids-bedtime',
        mainCategory: "Children's Books",
        subCategory: 'Bedtime & Dreams',
        leaf: 'Bedtime & Dreams',
        path: "Children's Books > Bedtime & Dreams",
        breadcrumbs: ["Children's Books", "Bedtime & Dreams"],
        marketplace: 'en',
        tags: ['bedtime', 'sleep', 'night', 'dreams', 'lullaby', 'calm', 'toddler'],
        ageHint: 'Ages 0–6'
    },
    {
        id: 'en-kids-animals-farm',
        mainCategory: "Children's Books",
        subCategory: 'Animals',
        leaf: 'Farm Animals',
        path: "Children's Books > Animals > Farm Animals",
        breadcrumbs: ["Children's Books", "Animals", "Farm Animals"],
        marketplace: 'en',
        tags: ['farm', 'animals', 'cow', 'sheep', 'pig', 'horse', 'barnyard'],
        ageHint: 'Ages 2–6'
    },
    {
        id: 'en-kids-animals-wildlife',
        mainCategory: "Children's Books",
        subCategory: 'Animals',
        leaf: 'Wildlife & Forest Animals',
        path: "Children's Books > Animals > Wildlife",
        breadcrumbs: ["Children's Books", "Animals", "Wildlife"],
        marketplace: 'en',
        tags: ['wildlife', 'bear', 'fox', 'forest', 'jungle', 'lion', 'safari'],
        ageHint: 'Ages 3–8'
    },
    {
        id: 'en-kids-growingup-emotions',
        mainCategory: "Children's Books",
        subCategory: 'Growing Up & Facts of Life',
        leaf: 'Emotions & Feelings',
        path: "Children's Books > Growing Up & Facts of Life > Emotions & Feelings",
        breadcrumbs: ["Children's Books", "Growing Up & Facts of Life", "Emotions & Feelings"],
        marketplace: 'en',
        tags: ['emotions', 'feelings', 'courage', 'kindness', 'anxiety', 'resilience'],
        ageHint: 'Ages 3–8'
    },
    {
        id: 'en-kids-growingup-friendship',
        mainCategory: "Children's Books",
        subCategory: 'Growing Up & Facts of Life',
        leaf: 'Friendship & Social Skills',
        path: "Children's Books > Growing Up & Facts of Life > Friendship",
        breadcrumbs: ["Children's Books", "Growing Up & Facts of Life", "Friendship"],
        marketplace: 'en',
        tags: ['friends', 'friendship', 'sharing', 'teamwork', 'social skills'],
        ageHint: 'Ages 3–8'
    },
    {
        id: 'en-kids-fantasy-magic',
        mainCategory: "Children's Books",
        subCategory: 'Fantasy & Magic',
        leaf: 'Fairies, Wizards & Mythical Creatures',
        path: "Children's Books > Fantasy & Magic > Fairies & Wizards",
        breadcrumbs: ["Children's Books", "Fantasy & Magic", "Fairies & Wizards"],
        marketplace: 'en',
        tags: ['magic', 'fairies', 'wizards', 'dragons', 'unicorns', 'mythical'],
        ageHint: 'Ages 4–10'
    },
    // --- FICTION ---
    {
        id: 'en-fiction-fantasy-epic',
        mainCategory: 'Fiction',
        subCategory: 'Fantasy',
        leaf: 'Epic & High Fantasy',
        path: 'Fiction > Fantasy > Epic Fantasy',
        breadcrumbs: ['Fiction', 'Fantasy', 'Epic Fantasy'],
        marketplace: 'en',
        tags: ['epic fantasy', 'high fantasy', 'worldbuilding', 'swords', 'magic', 'kingdoms']
    },
    {
        id: 'en-fiction-fantasy-romantasy',
        mainCategory: 'Fiction',
        subCategory: 'Fantasy',
        leaf: 'Romantic Fantasy & Romantasy',
        path: 'Fiction > Fantasy > Romantic Fantasy',
        breadcrumbs: ['Fiction', 'Fantasy', 'Romantic Fantasy'],
        marketplace: 'en',
        tags: ['romantasy', 'romantic fantasy', 'fae', 'enemies to lovers', 'court']
    },
    {
        id: 'en-fiction-scifi-spaceopera',
        mainCategory: 'Fiction',
        subCategory: 'Science Fiction',
        leaf: 'Space Opera & Galactic Empires',
        path: 'Fiction > Science Fiction > Space Opera',
        breadcrumbs: ['Fiction', 'Science Fiction', 'Space Opera'],
        marketplace: 'en',
        tags: ['space opera', 'spaceships', 'galaxy', 'aliens', 'fleet', 'space travel']
    },
    {
        id: 'en-fiction-thriller-psychological',
        mainCategory: 'Fiction',
        subCategory: 'Mystery, Thriller & Suspense',
        leaf: 'Psychological Thrillers',
        path: 'Fiction > Mystery, Thriller & Suspense > Psychological Thrillers',
        breadcrumbs: ['Fiction', 'Mystery, Thriller & Suspense', 'Psychological Thrillers'],
        marketplace: 'en',
        tags: ['psychological thriller', 'plot twist', 'suspense', 'serial killer', 'mystery']
    },
    {
        id: 'en-fiction-cozy-mystery',
        mainCategory: 'Fiction',
        subCategory: 'Mystery, Thriller & Suspense',
        leaf: 'Cozy Mystery',
        path: 'Fiction > Mystery, Thriller & Suspense > Cozy Mystery',
        breadcrumbs: ['Fiction', 'Mystery, Thriller & Suspense', 'Cozy Mystery'],
        marketplace: 'en',
        tags: ['cozy mystery', 'small town', 'amateur sleuth', 'whodunit', 'humorous']
    },
    {
        id: 'en-fiction-romance-contemporary',
        mainCategory: 'Fiction',
        subCategory: 'Romance',
        leaf: 'Contemporary Romance & Rom-Com',
        path: 'Fiction > Romance > Contemporary Romance',
        breadcrumbs: ['Fiction', 'Romance', 'Contemporary Romance'],
        marketplace: 'en',
        tags: ['romance', 'rom com', 'contemporary', 'love story', 'happy ending']
    }
];

export function getCategoriesForMarketplace(marketplace: string): KdpCategoryDefinition[] {
    const isEn = ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.com.au'].includes(marketplace.toLowerCase());
    return isEn ? KDP_CATEGORIES_EN : KDP_CATEGORIES_DE;
}

export function searchKdpCategories(query: string, marketplace: string, mainCategoryFilter?: string): KdpCategoryDefinition[] {
    const list = getCategoriesForMarketplace(marketplace);
    const q = (query || '').toLowerCase().trim();
    
    return list.filter(item => {
        if (mainCategoryFilter && mainCategoryFilter !== 'ALL' && item.mainCategory !== mainCategoryFilter) {
            return false;
        }
        if (!q) return true;
        
        const inPath = item.path.toLowerCase().includes(q);
        const inTags = item.tags.some(t => t.toLowerCase().includes(q));
        const inMain = item.mainCategory.toLowerCase().includes(q);
        const inSub = item.subCategory.toLowerCase().includes(q);
        const inLeaf = item.leaf.toLowerCase().includes(q);
        
        return inPath || inTags || inMain || inSub || inLeaf;
    });
}
