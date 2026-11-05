// Intro animato della homepage (markup: portfolio/_intro.html, aspetto: custom.css, sezione "Intro animato").
//
// Perché serve un clic: i browser non fanno partire l'audio finché la persona non ha toccato la pagina (su iPhone mai da soli).
// Il clic su "welcome to HTS" sblocca l'audio e dà il via alla sequenza. Tutto dura quanto l'audio, dal clic in poi.
//
// La sequenza è una funzione del tempo: render(t) dice come sta ogni elemento a t secondi dal clic. Cambiare i valori
// in TIMELINE basta per cambiare i tempi; non serve toccare il resto.

const TIMELINE = {
    textFadeOut: 0.8,       // secondi: il testo "welcome to HTS" sparisce subito dopo il clic
    drawStart: 1.2,         // secondi dal clic: la prima linea del triskele comincia a disegnarsi
    drawDuration: 9,        // secondi: quanto ci mette ogni linea a disegnarsi
    stagger: 0.5,           // secondi di ritardo tra una linea e la successiva
    fadeOutDuration: 2.5,   // secondi: dissolvenza finale verso la pagina (finisce insieme all'audio)
    fallbackDuration: 15,   // secondi: durata se l'audio non si carica (di norma vale la durata del file)
};

(() => {
    const intro = document.getElementById('intro');
    if (!intro) return; // l'ha tolto lo script in linea: già visto in questa sessione, o movimento ridotto

    const enter = intro.querySelector('.intro-enter');
    const skip = intro.querySelector('.intro-skip');
    const audio = intro.querySelector('.intro-audio');
    const paths = [...intro.querySelectorAll('.intro-triskele path')];
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
            path.style.visibility = progress > 0 ? 'visible' : 'hidden';
            path.style.strokeDashoffset = String(1 - progress); // 1 = linea nascosta, 0 = tutta disegnata
        });

        const fade = clamp01((t - (duration - TIMELINE.fadeOutDuration)) / TIMELINE.fadeOutDuration);
        intro.style.opacity = String(1 - fade);
    }

    function run() {
        const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : TIMELINE.fallbackDuration;
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
