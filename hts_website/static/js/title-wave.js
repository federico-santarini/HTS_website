// Onda lettera per lettera nei titoli del feed progetti (project_feed.html; aspetto e tempi: custom.css, sezione [07]).
//
// Il CSS da solo non può dare uno stile alla singola lettera: qui ogni titolo diventa una serie di <span>, uno per lettera, e a
// ognuno si scrive --letters-from-end (quante lettere lo seguono), da cui il CSS ricava lo sfasamento. Le lettere di una parola
// stanno in uno span che non va a capo. Senza JavaScript il titolo pulsa tutto insieme.

(() => {
    const titles = document.querySelectorAll('.project-feed .project-title');

    // L'onda si ferma nei titoli fuori dallo schermo: sono centinaia di lettere da ridisegnare a ogni fotogramma.
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => entry.target.classList.toggle('is-offscreen', !entry.isIntersecting));
    });

    titles.forEach((title) => {
        const text = title.textContent.trim().normalize('NFC');
        const words = text.split(/\s+/);
        let remaining = words.reduce((total, word) => total + Array.from(word).length, 0);

        title.setAttribute('aria-label', text); // i lettori di schermo leggono il titolo intero, non le lettere
        title.textContent = '';

        words.forEach((word, i) => {
            const wordSpan = document.createElement('span');
            wordSpan.className = 'wave-word';
            wordSpan.setAttribute('aria-hidden', 'true');
            Array.from(word).forEach((letter) => {
                const span = document.createElement('span');
                span.className = 'wave-letter';
                span.textContent = letter;
                span.style.setProperty('--letters-from-end', --remaining);
                wordSpan.append(span);
            });
            if (i > 0) title.append(' ');
            title.append(wordSpan);
        });

        title.classList.add('is-wave');
        observer.observe(title);
    });
})();
