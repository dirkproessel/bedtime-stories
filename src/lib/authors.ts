export interface Author {
    id: string;
    name: string;
    desc: string;
    preferredGenres?: string[];
}

export const AUTHORS: Author[] = [
    { id: 'kehlmann', name: 'Daniel Kehlmann', desc: 'Präzise, Geistreich, Verspielt', preferredGenres: ['Historisch', 'Drama', 'Satire'] },
    { id: 'zeh', name: 'Juli Zeh', desc: 'Analytisch, Kühl, Kritisch', preferredGenres: ['Dystopie', 'Drama', 'Thriller'] },
    { id: 'fitzek', name: 'Sebastian Fitzek', desc: 'Atemlos, Rasant, Düster', preferredGenres: ['Thriller', 'Krimi', 'Grusel'] },
    { id: 'kracht', name: 'Christian Kracht', desc: 'Snobistisch, Dekadent, Distanziert', preferredGenres: ['Satire', 'Dystopie', 'Historisch'] },
    { id: 'kafka', name: 'Franz Kafka', desc: 'Surreal, Beklemmend, Trocken', preferredGenres: ['Grusel', 'Dystopie', 'Drama'] },
    { id: 'jaud', name: 'Tommy Jaud', desc: 'Lustig, Hektisch, Peinlich', preferredGenres: ['Komödie', 'Roadtrip', 'Modern Romanze'] },
    { id: 'regener', name: 'Sven Regener', desc: 'Lakonisch, Echt, Schnodderig', preferredGenres: ['Komödie', 'Roadtrip', 'Drama'] },
    { id: 'strunk', name: 'Heinz Strunk', desc: 'Grotesk, Erbarmungslos, Schräg', preferredGenres: ['Satire', 'Komödie', 'Grusel'] },
    { id: 'kling', name: 'Marc-Uwe Kling', desc: 'Schlagfertig, Logisch, Trocken', preferredGenres: ['Satire', 'Komödie', 'Science-Fiction'] },
    { id: 'stuckrad_barre', name: 'Benjamin v. Stuckrad-Barre', desc: 'Nervös, Pop-affin, Hyper', preferredGenres: ['Satire', 'Modern Romanze', 'Roadtrip'] },
    { id: 'evers', name: 'Horst Evers', desc: 'Absurd, Gemütlich, Skurril', preferredGenres: ['Komödie', 'Fabel', 'Gute Nacht'] },
    { id: 'loriot', name: 'Loriot', desc: 'Bürgerlich, Präzise, Absurd', preferredGenres: ['Komödie', 'Satire', 'Drama'] },
    { id: 'funke', name: 'Cornelia Funke', desc: 'Magisch, Bildstark, Abenteuerlich', preferredGenres: ['Fantasy', 'Abenteuer', 'Märchen'] },
    { id: 'pantermueller', name: 'Alice Pantermüller', desc: 'Rotzig, Frech, Chaotisch', preferredGenres: ['Komödie', 'Abenteuer', 'Fabel'] },
    { id: 'auer', name: 'Margit Auer', desc: 'Geborgen, Geheimnisvoll, Empathisch', preferredGenres: ['Abenteuer', 'Fabel', 'Gute Nacht'] },
    { id: 'pratchett', name: 'Terry Pratchett', desc: 'Scharfsinnig, Satirisch, Trocken', preferredGenres: ['Fantasy', 'Satire', 'Komödie'] },
    { id: 'adams', name: 'Douglas Adams', desc: 'Absurd, Lakonisch, Kosmisch', preferredGenres: ['Science-Fiction', 'Satire', 'Komödie'] },
    { id: 'kinney', name: 'Jeff Kinney', desc: 'Pubertär, Ironisch, Authentisch', preferredGenres: ['Komödie', 'Modern Romanze', 'Abenteuer'] },
    { id: 'kaestner', name: 'Erich Kästner', desc: 'Ironisch, Klar, Herzlich', preferredGenres: ['Fabel', 'Abenteuer', 'Komödie'] },
    { id: 'lindgren', name: 'Astrid Lindgren', desc: 'Herzlich, Mutig, Kindlich-weise', preferredGenres: ['Märchen', 'Abenteuer', 'Gute Nacht'] },
    { id: 'dahl', name: 'Roald Dahl', desc: 'Skurril, Drastisch, Respektlos', preferredGenres: ['Märchen', 'Grusel', 'Abenteuer'] },
    { id: 'christie', name: 'Agatha Christie', desc: 'Sachlich, Analytisch, Rätselhaft', preferredGenres: ['Krimi', 'Thriller', 'Historisch'] },
    { id: 'king', name: 'Stephen King', desc: 'Detailreich, Volksnah, Unheimlich', preferredGenres: ['Grusel', 'Thriller', 'Fantasy'] },
    { id: 'hemingway', name: 'Ernest Hemingway', desc: 'Karg, Trocken, Präzise', preferredGenres: ['Drama', 'Abenteuer', 'Historisch'] },
    { id: 'rooney', name: 'Sally Rooney', desc: 'Modern, analytisch, intim', preferredGenres: ['Modern Romanze', 'Sinnliche Romanze', 'Drama'] },
    { id: 'nin', name: 'Anaïs Nin', desc: 'Sinnlich, poetisch, traumgleich', preferredGenres: ['Sinnliche Romanze', 'Erotik', 'Traum'] },
    { id: 'miller', name: 'Henry Miller', desc: 'Rau, direkt, ausschweifend', preferredGenres: ['Erotik', 'Drama', 'Roadtrip'] },
    { id: 'rice', name: 'Anne Rice', desc: 'Opulent, düster, hochemotional', preferredGenres: ['Dark Romance', 'Fantasy', 'Grusel'] },
];

/** Returns the display name for an author ID, falling back to the ID itself. */
export function authorName(id: string): string {
    const author = AUTHORS.find(a => a.id === id);
    return author ? author.name : id;
}

/** Parses a styles string (comma-separated author IDs) and returns a display string of names. */
export function formatAuthorStyles(styles: string): string {
    if (!styles) return '—';
    return styles.split(',')
        .map(id => authorName(id.trim()))
        .join(', ');
}
