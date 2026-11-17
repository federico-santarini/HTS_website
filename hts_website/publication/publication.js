// Comportamenti della pubblicazione (markup: index.html, aspetto: publication.css).
//
// 1. NOTE A SCOMPARSA
//
// Ogni numero in apice nel testo (<sup class="pub-fnref"><a href="#fn-AUTORE-N">) apre e chiude la sua nota
// (<span class="pub-note" id="fn-AUTORE-N">), che sta dentro il paragrafo subito dopo il numero. Le note chiuse sono nascoste dal
// CSS solo se questo script è partito (classe "js" su <html>, messa da index.html): senza JavaScript restano sempre visibili.

(() => {
    const notes = new Map();
    const links = document.querySelectorAll('.pub-fnref a');

    function setOpen(link, note, open) {
        note.classList.toggle('is-open', open);
        note.inert = !open;                          // chiusa: né raggiungibile con Tab né letta dagli screen reader
        link.setAttribute('aria-expanded', String(open));
    }

    links.forEach((link) => {
        const note = document.getElementById(link.getAttribute('href').slice(1));
        if (!note) return;
        notes.set(note.id, { link, note });
        link.setAttribute('role', 'button');
        link.setAttribute('aria-controls', note.id);
        setOpen(link, note, false);
        link.addEventListener('click', (event) => {
            event.preventDefault();                  // niente salto all'ancora: la nota si apre dov'è
            setOpen(link, note, !note.classList.contains('is-open'));
        });
    });

    // Un indirizzo con #fn-... (link condiviso, o pagina riaperta) apre la nota e porta lì.
    function openFromHash() {
        const found = notes.get(decodeURIComponent(location.hash.slice(1)));
        if (!found) return;
        setOpen(found.link, found.note, true);
        found.link.scrollIntoView({ block: 'center' });
    }
    window.addEventListener('hashchange', openFromHash);
    openFromHash();
})();


// 2. BARRA IN ALTO E INDICE A TUTTO SCHERMO
//
// La barra (<div class="pub-topbar">) dice in quale testo si è: nome e autore, letti da data-title e data-author di ogni <article>.
// Il pulsante "Contents" apre l'indice (<div class="pub-menu">) a tutto schermo, come il menu del sito; si chiude con lo stesso
// pulsante, con Esc o scegliendo una voce. La voce del testo in cui si è è evidenziata (aria-current).
// La barra laterale dei numeri (<nav class="pub-sidebar">) compare dal primo capitolo in poi, segna il capitolo o sottocapitolo corrente (aria-current: il CSS ci mette la freccia)
// e al passaggio del mouse su un numero mostra il nome del titolo (data-title).

(() => {
    const topbar = document.querySelector('.pub-topbar');
    const menu = document.getElementById('pub-menu');
    if (!topbar || !menu) return;

    const toggle = topbar.querySelector('.pub-topbar-toggle');
    const titleEl = topbar.querySelector('.pub-topbar-title');
    const authorEl = topbar.querySelector('.pub-topbar-author');
    const root = document.documentElement;
    const articles = [...document.querySelectorAll('article[id]')];
    const coverTitle = titleEl.textContent;
    // Il resto della pagina non è raggiungibile con Tab né letto dagli screen reader mentre l'indice è aperto.
    const page = [...document.body.children].filter((el) => el !== topbar && el !== menu && el.tagName !== 'SCRIPT');

    // --- barra laterale dei numeri (<nav class="pub-sidebar">): un link per ogni capitolo e sottocapitolo, nell'ordine della pagina
    const sidebar = document.querySelector('.pub-sidebar');
    const sideLinks = sidebar ? [...sidebar.querySelectorAll('a[href^="#"]')] : [];
    const sideTargets = sideLinks.map((a) => document.getElementById(a.getAttribute('href').slice(1)));
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    // --- nome del titolo accanto al numero (al passaggio del mouse o con il focus). Una sola etichetta, fuori dalla barra:
    // la barra scorre e taglierebbe ciò che esce dai suoi bordi.
    let label = null;
    function showLabel(link) {
        if (!label) {
            label = document.createElement('div');
            label.className = 'pub-sidebar-label';
            label.setAttribute('aria-hidden', 'true');   // il nome è già nell'aria-label del link
            document.body.append(label);
        }
        const rect = link.getBoundingClientRect();
        label.textContent = link.dataset.title;
        label.dataset.level = link.dataset.level;   // 1 = capitolo, 2 = sottocapitolo, 3 = sotto-sottocapitolo: serve al CSS (.pub-sidebar-label[data-level="2"])
        label.style.left = `${sidebar.getBoundingClientRect().right + 8}px`;
        label.style.top = `${rect.top + rect.height / 2}px`;
        label.classList.add('is-visible');
    }
    function hideLabel() {
        label?.classList.remove('is-visible');
    }
    if (sidebar) {
        sidebar.addEventListener('mouseover', (event) => {
            const link = event.target.closest('a');
            if (link) showLabel(link); else hideLabel();
        });
        sidebar.addEventListener('mouseleave', hideLabel);
        sidebar.addEventListener('focusin', (event) => {
            const link = event.target.closest('a');
            if (link) showLabel(link);
        });
        sidebar.addEventListener('focusout', hideLabel);
        sidebar.addEventListener('scroll', hideLabel, { passive: true });
        sidebar.addEventListener('click', hideLabel);
    }

    // --- testo corrente: l'ultimo articolo il cui inizio è già passato sotto la barra
    // --- sezione corrente: l'ultimo capitolo o sottocapitolo il cui titolo è già passato sotto la barra
    let current = null;
    let currentSide = -1;
    function updateCurrent() {
        const probe = topbar.getBoundingClientRect().height + 1;
        let active = null;
        for (const article of articles) {
            if (article.getBoundingClientRect().top <= probe) active = article; else break;
        }
        if (active !== current) {
            current = active;
            titleEl.textContent = active ? active.dataset.title : coverTitle;
            authorEl.textContent = active ? active.dataset.author || '' : '';
            menu.querySelectorAll('a[aria-current]').forEach((a) => a.removeAttribute('aria-current'));
            if (active) menu.querySelector(`a[href="#${active.id}"]`)?.setAttribute('aria-current', 'true');
        }

        let side = -1;
        for (let i = 0; i < sideTargets.length; i++) {
            if (sideTargets[i] && sideTargets[i].getBoundingClientRect().top <= probe) side = i; else if (sideTargets[i]) break;
        }
        // la barra compare dal primo capitolo in poi (non sulla copertina né sull'indice iniziale)
        if (sidebar) {
            const visible = side >= 0;
            sidebar.classList.toggle('is-visible', visible);
            if (!visible) hideLabel();
        }
        if (side !== currentSide) {
            currentSide = side;
            sideLinks.forEach((a) => a.removeAttribute('aria-current'));
            const link = sideLinks[side];
            if (link) {
                link.setAttribute('aria-current', 'true');
                if (sidebar.offsetParent !== null || getComputedStyle(sidebar).display !== 'none') {
                    // tiene visibile il numero corrente dentro la barra (che scorre da sola), senza muovere la pagina
                    const top = link.offsetTop - (sidebar.clientHeight - link.offsetHeight) / 2;
                    sidebar.scrollTo({ top, behavior: reduceMotion.matches ? 'auto' : 'smooth' });
                }
            }
        }
    }
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => { ticking = false; updateCurrent(); });
    }, { passive: true });
    window.addEventListener('resize', updateCurrent);

    // --- apertura e chiusura dell'indice
    function setMenu(open) {
        menu.classList.toggle('is-open', open);
        menu.inert = !open;
        page.forEach((el) => { el.inert = open; });
        root.classList.toggle('pub-menu-open', open);
        toggle.setAttribute('aria-expanded', String(open));
        if (open) {
            (menu.querySelector('a[aria-current]') || menu.querySelector('a'))?.focus({ preventScroll: true });
            menu.querySelector('a[aria-current]')?.scrollIntoView({ block: 'center' }); // l'indice si apre sulla voce corrente
        } else if (menu.contains(document.activeElement)) {
            toggle.focus({ preventScroll: true });
        }
    }
    toggle.addEventListener('click', () => setMenu(!menu.classList.contains('is-open')));
    menu.addEventListener('click', (event) => {
        if (event.target.closest('a')) setMenu(false);   // si chiude e il link porta alla voce scelta
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && menu.classList.contains('is-open')) setMenu(false);
    });

    setMenu(false);
    updateCurrent();
})();
