// Bagliore dei tracciati del triskele nella home (markup: _triskele.html, stile: custom.css [12]).
//
// Il glow del sito è --hts-glow (custom.css [02]): una lista di ombre scritta come per "text-shadow". Un'ombra CSS non si applica a un
// tracciato SVG, quindi qui la lista viene tradotta in un filtro SVG che fa la stessa cosa: per ogni ombra, la forma del tracciato
// sfocata, colorata e (se serve) spostata; le ombre si sovrappongono come in text-shadow (la prima sta sopra).
// Così cambiare --hts-glow cambia anche il triskele, senza toccare questo file.

(() => {
    const filter = document.getElementById('triskele-glow-filter');
    if (!filter) return;
    const svg = filter.ownerSVGElement;
    const NS = 'http://www.w3.org/2000/svg';

    // Faccio leggere --hts-glow al browser come text-shadow: restituisce sempre la forma "colore x y sfocatura", con i var() già risolti.
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;text-shadow:var(--hts-glow-triskele);';
    document.body.append(probe);
    const computed = getComputedStyle(probe).textShadow;
    probe.remove();

    const SHADOW = /(rgba?\([^)]*\)|#[0-9a-f]+|[a-z]+)\s+(-?[\d.]+)px\s+(-?[\d.]+)px(?:\s+([\d.]+)px)?/gi;
    const layers = [...computed.matchAll(SHADOW)].map(([, color, x, y, blur]) => ({
        color, x: parseFloat(x), y: parseFloat(y), blur: parseFloat(blur || 0),
    }));
    if (!layers.length) return; // --hts-glow assente: resta il filtro di riserva

    const make = (name, attrs = {}) => {
        const el = document.createElementNS(NS, name);
        Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
        return el;
    };

    // Le misure di un'ombra CSS sono in pixel, quelle di un filtro SVG nelle unità del disegno (largo 500): le converto in base alla
    // dimensione a schermo, e le ricalcolo se cambia. Una sfocatura CSS di B pixel è una gaussiana con deviazione standard B/2.
    function build() {
        const pxPerUnit = svg.getBoundingClientRect().width / 500;
        if (!pxPerUnit) return;
        filter.replaceChildren();
        layers.forEach((layer, i) => {
            let last = `blur${i}`;
            filter.append(make('feGaussianBlur', { in: 'SourceAlpha', stdDeviation: layer.blur / 2 / pxPerUnit, result: last }));
            if (layer.x || layer.y) {
                filter.append(make('feOffset', { in: last, dx: layer.x / pxPerUnit, dy: layer.y / pxPerUnit, result: `shift${i}` }));
                last = `shift${i}`;
            }
            filter.append(make('feFlood', { 'flood-color': layer.color, result: `color${i}` }));
            filter.append(make('feComposite', { in: `color${i}`, in2: last, operator: 'in', result: `layer${i}` }));
        });
        const merge = make('feMerge');
        for (let i = layers.length - 1; i >= 0; i--) merge.append(make('feMergeNode', { in: `layer${i}` })); // l'ultima ombra sta sotto
        filter.append(merge);
    }

    build();
    new ResizeObserver(build).observe(svg);
})();
