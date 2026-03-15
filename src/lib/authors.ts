export interface Author {
    id: string;
    name: string;
    desc: string;
}

export const AUTHORS: Author[] = [
    { id: 'kehlmann', name: 'Daniel Kehlmann', desc: 'Präzise, Geistreich, Verspielt.' },
    { id: 'zeh', name: 'Juli Zeh', desc: 'Analytisch, Kühl, Kritisch.' },
    { id: 'fitzek', name: 'Sebastian Fitzek', desc: 'Atemlos, Rasant, Düster.' },
    { id: 'kracht', name: 'Christian Kracht', desc: 'Snobistisch, Dekadent, Distanziert.' },
    { id: 'kafka', name: 'Franz Kafka', desc: 'Surreal, Beklemmend, Trocken.' },
    { id: 'jaud', name: 'Tommy Jaud', desc: 'Lustig, Hektisch, Peinlich.' },
    { id: 'regener', name: 'Sven Regener', desc: 'Lakonisch, Echt, Schnodderig.' },
    { id: 'strunk', name: 'Heinz Strunk', desc: 'Grotesk, Erbarmungslos, Schräg.' },
    { id: 'kling', name: 'Marc-Uwe Kling', desc: 'Schlagfertig, Logisch, Trocken.' },
    { id: 'stuckrad_barre', name: 'Benjamin v. Stuckrad-Barre', desc: 'Nervös, Pop-affin, Hyper.' },
    { id: 'evers', name: 'Horst Evers', desc: 'Absurd, Gemütlich, Skurril.' },
    { id: 'loriot', name: 'Loriot', desc: 'Bürgerlich, Präzise, Absurd.' },
    { id: 'funke', name: 'Cornelia Funke', desc: 'Magisch, Bildstark, Abenteuerlich.' },
    { id: 'pantermueller', name: 'Alice Pantermüller', desc: 'Rotzig, Frech, Chaotisch.' },
    { id: 'auer', name: 'Margit Auer', desc: 'Geborgen, Geheimnisvoll, Empathisch.' },
    { id: 'pratchett', name: 'Terry Pratchett', desc: 'Scharfsinnig, Satirisch, Trocken.' },
    { id: 'adams', name: 'Douglas Adams', desc: 'Absurd, Lakonisch, Kosmisch.' },
    { id: 'kinney', name: 'Jeff Kinney', desc: 'Pubertär, Ironisch, Authentisch.' },
    { id: 'kaestner', name: 'Erich Kästner', desc: 'Ironisch, Klar, Herzlich.' },
    { id: 'lindgren', name: 'Astrid Lindgren', desc: 'Herzlich, Mutig, Kindlich-weise.' },
    { id: 'dahl', name: 'Roald Dahl', desc: 'Skurril, Drastisch, Respektlos.' },
    { id: 'christie', name: 'Agatha Christie', desc: 'Sachlich, Analytisch, Rätselhaft.' },
    { id: 'king', name: 'Stephen King', desc: 'Detailreich, Volksnah, Unheimlich.' },
    { id: 'hemingway', name: 'Ernest Hemingway', desc: 'Karg, Trocken, Präzise.' },
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
