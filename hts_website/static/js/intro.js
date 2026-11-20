// Intro animato della homepage (markup: portfolio/_intro.html, aspetto: custom.css, sezione [13]).
//
// Perché serve un clic: i browser non fanno partire l'audio finché la persona non ha toccato la pagina (su iPhone mai da soli).
// Il clic sul testo d'ingresso sblocca l'audio e dà il via alla sequenza. Dura TIMELINE.duration secondi dal clic, qualunque sia la lunghezza
// del file audio: se l'audio è più corto, il resto va avanti in silenzio; se è più lungo, il volume scende con la dissolvenza finale e si ferma.
//
// La sequenza è una funzione del tempo: render(t) dice come sta ogni elemento a t secondi dal clic. Cambiare i valori
// in TIMELINE basta per cambiare i tempi; non serve toccare il resto.

const TIMELINE = {
    duration: 18,           // secondi: durata totale dell'intro dal clic (la dissolvenza finale finisce qui)
    textFadeOut: 0.8,       // secondi: il testo "welcome to HTS" sparisce subito dopo il clic
    drawStart: 3,         // secondi dal clic: la prima linea del triskele comincia a disegnarsi
    drawDuration: 12,        // secondi: quanto ci mette ogni linea a disegnarsi
    stagger: 0,           // secondi di ritardo tra una linea e la successiva
    minLength: 1,           // una linea compare solo quando è lunga almeno così tante volte il proprio spessore (sotto sarebbe un puntino)
    lineFadeIn: 0.5,        // secondi: dissolvenza con cui ogni linea compare, appena raggiunge minLength
    fadeOutDuration: 2.5,   // secondi: dissolvenza finale verso la pagina (finisce a TIMELINE.duration; sfuma anche il volume)
};

(() => {
    const intro = document.getElementById('intro');
    if (!intro) return; // l'ha tolto lo script in linea: già visto in questa sessione, o movimento ridotto

    const enter = intro.querySelector('.intro-enter');
    const skip = intro.querySelector('.intro-skip');
    const audio = intro.querySelector('.intro-audio');
    const paths = [...intro.querySelectorAll('.intro-triskele path')];
    // Ogni spirale è un nastro disegnato come contorno: UN tracciato a doppia linea che parte da una giunzione, scende verso il centro lungo un bordo,
    // gira attorno al centro e torna fuori lungo l'altro bordo. Invece di disegnarlo da un capo all'altro (la spirale si "avvolgerebbe" prima verso
    // il centro e poi fuori), lo si fa crescere DAL CENTRO verso entrambe le estremità, con i due bordi insieme: come prima, quando ogni spirale
    // era una linea sola che si svolgeva dal centro. Il punto del giro al centro è data-center sul tracciato (frazione della lunghezza, 0-1):
    // è misurato sul disegno (_triskele.html). Le due metà hanno lunghezze diverse (il bordo esterno è più lungo di quello interno) ma si
    // completano INSIEME: ognuna cresce in proporzione alla propria lunghezza (la più lunga va un po' più veloce). Un tracciato senza data-center
    // si disegna da un capo all'altro, come una linea semplice.
    const centers = paths.map((path) => {
        const value = parseFloat(path.dataset.center);
        return Number.isFinite(value) ? value : null;
    });
    // Progresso (0-1) a cui ogni linea è lunga minLength volte il proprio spessore, e istante (t) in cui è comparsa.
    // Spessore e lunghezza sono nelle stesse unità del disegno (viewBox), quindi il rapporto non dipende dalla dimensione a schermo.
    const strokeWidth = parseFloat(getComputedStyle(paths[0]).strokeWidth) || 0;
    const lengths = paths.map((path) => path.getTotalLength() || 1);
    const appearedAt = paths.map(() => null);
    // Il resto della pagina non è cliccabile né raggiungibile con Tab finché dura l'intro.
    const page = [...document.body.children].filter((el) => el !== intro && el.tagName !== 'SCRIPT');
    page.forEach((el) => { el.inert = true; });
    document.documentElement.classList.add('intro-ready'); // il CSS blocca lo scroll e disattiva la rete di sicurezza

    let started = false;
    let raf = 0;

    // Il file audio si scarica subito e si dà al player come blob (indirizzo locale del browser). Così funziona anche con server
    // che non supportano le richieste a pezzi (HTTP Range), che Safari pretende per riprodurre un audio: il server di sviluppo
    // di Django non le supporta. Se il download fallisce si prova comunque con l'indirizzo normale. Questa promessa non fallisce mai.
    const audioReady = fetch(audio.dataset.src)
        .then((response) => { if (!response.ok) throw new Error(response.status); return response.blob(); })
        .then((blob) => { audio.src = URL.createObjectURL(blob); })
        .catch(() => { audio.src = audio.dataset.src; });

    const clamp01 = (x) => Math.min(1, Math.max(0, x));
    const easeInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

    function markSeen() {
        try { sessionStorage.setItem('htsIntroSeen', '1'); } catch (e) { /* storage bloccato: si rivedrà */ }
    }

    function finish() {
        cancelAnimationFrame(raf);
        audio.pause();
        page.forEach((el) => { el.inert = false; });
        document.documentElement.classList.remove('intro-ready');
        intro.remove();
    }

    // Stato dell'intro a t secondi dal clic.
    function render(t, duration) {
        enter.style.opacity = String(1 - clamp01(t / TIMELINE.textFadeOut));
        if (t >= TIMELINE.textFadeOut) enter.style.visibility = 'hidden';

        paths.forEach((path, i) => {
            const progress = easeInOut(clamp01((t - TIMELINE.drawStart - i * TIMELINE.stagger) / TIMELINE.drawDuration));
            const shown = progress; // frazione visibile della lunghezza: partendo dal centro è proprio il progresso (vedi sotto)
            // Le estremità sono tonde: una linea cortissima si vede come un puntino largo quanto lo spessore. Finché non è
            // lunga almeno minLength volte lo spessore resta nascosta; poi compare con una breve dissolvenza.
            if (shown * lengths[i] < strokeWidth * TIMELINE.minLength) {
                path.style.visibility = 'hidden';
                return;
            }
            if (appearedAt[i] === null) appearedAt[i] = t;
            path.style.visibility = 'visible';
            path.style.opacity = String(clamp01((t - appearedAt[i]) / TIMELINE.lineFadeIn));
            if (centers[i] === null) {
                path.style.strokeDashoffset = String(1 - progress); // 1 = linea nascosta, 0 = tutta disegnata
            } else if (progress >= 1) {
                path.style.strokeDasharray = 'none';                // disegnata tutta: niente trattini
                path.style.strokeDashoffset = '0';
            } else {
                // Un solo trattino lungo "progress" (frazione della lunghezza) che cresce dal centro c: la parte prima del centro ne occupa
                // c * progress e quella dopo (1 - c) * progress, quindi il trattino comincia a c * (1 - progress) e a progress = 1 copre tutto
                // il tracciato (da 0 a 1), con le due metà che arrivano alle loro estremità nello stesso istante. Il vuoto (2) è più lungo
                // del tracciato: il trattino non si ripete.
                path.style.strokeDasharray = `${progress} 2`;
                path.style.strokeDashoffset = String(-centers[i] * (1 - progress));
            }
        });

        const fade = clamp01((t - (duration - TIMELINE.fadeOutDuration)) / TIMELINE.fadeOutDuration);
        intro.style.opacity = String(1 - fade);
        audio.volume = 1 - fade; // il suono sfuma con l'immagine (su iPhone il volume non si può cambiare: lì resta com'è)
    }

    function run() {
        const duration = TIMELINE.duration;
        const startedAt = performance.now();
        const tick = (now) => {
            const t = (now - startedAt) / 1000;
            render(Math.min(t, duration), duration);
            if (t >= duration) finish(); else raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
    }

    function start() {
        if (started) return;
        started = true;
        markSeen();
        enter.disabled = true;
        // La sequenza parte appena parte l'audio. Se l'audio è bloccato, lento o non si carica (qualunque motivo: browser, rete,
        // file) parte lo stesso dopo mezzo secondo e finisce, senza suono: un clic non deve mai sembrare "morto".
        let running = false;
        const go = () => { if (!running) { running = true; run(); } };
        audio.addEventListener('playing', go, { once: true });
        setTimeout(go, 500);
        audioReady.then(() => audio.play()).catch(go);
    }

    function skipIntro() {
        started = true;
        markSeen();
        cancelAnimationFrame(raf);
        intro.style.transition = 'opacity 0.4s';
        intro.style.opacity = '0';
        audio.pause();
        setTimeout(finish, 400);
    }

    enter.addEventListener('click', start);
    skip.addEventListener('click', skipIntro);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') skipIntro(); });
    enter.focus({ preventScroll: true }); // da tastiera basta Invio
})();
