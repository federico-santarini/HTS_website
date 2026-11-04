// Player di YouTube e SoundCloud (markup in portfolio/_project.html, aspetto in custom.css).
//  - YouTube: finché non si preme play c'è solo una copertina; al clic si crea l'<iframe> e parte il video.
//  - SoundCloud: il widget ufficiale resta nascosto e fa da motore audio; i controlli (play/pausa, barra, tempo)
//    sono nostri e lo pilotano con la Widget API di SoundCloud (https://developers.soundcloud.com/docs/api/html5-widget).

// ---------- YouTube ----------
document.addEventListener('click', (e) => {
    const facade = e.target.closest('.yt-facade');
    if (!facade) return;
    e.preventDefault(); // senza JavaScript il link porta al video su YouTube
    const url = new URL(facade.dataset.embedUrl);
    url.searchParams.set('autoplay', '1');
    const iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.title = facade.dataset.title;
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    facade.replaceWith(iframe);
    iframe.focus();
});

// ---------- SoundCloud ----------
const soundCloudRoots = document.querySelectorAll('[data-sc-player]');
const soundCloudWidgets = [];

function formatTime(ms) {
    const seconds = Math.floor(ms / 1000);
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

function initSoundCloud(root) {
    const iframe = root.querySelector('.sc-engine');
    const toggle = root.querySelector('.sc-toggle');
    const seek = root.querySelector('.sc-seek');
    const title = root.querySelector('.sc-title');
    const artist = root.querySelector('.sc-artist');
    const time = root.querySelector('.sc-time');
    let duration = 0;
    let seeking = false;

    function showPosition(ms) {
        const fraction = duration ? Math.min(ms / duration, 1) : 0;
        seek.value = Math.round(fraction * 1000);
        seek.style.setProperty('--progress', `${fraction * 100}%`);
        time.textContent = `${formatTime(ms)} / ${formatTime(duration)}`;
    }

    // Titolo, artista e durata del brano in corso (in una playlist cambiano da un brano all'altro).
    function refreshSound() {
        widget.getCurrentSound((sound) => {
            if (!sound) return;
            duration = sound.duration;
            title.textContent = sound.title;
            title.href = sound.permalink_url;
            artist.textContent = sound.user.username;
            showPosition(0);
        });
    }

    iframe.src = iframe.dataset.src;
    const widget = SC.Widget(iframe);
    soundCloudWidgets.push(widget);

    widget.bind(SC.Widget.Events.READY, () => {
        toggle.disabled = false;
        seek.disabled = false;
        refreshSound();
    });
    widget.bind(SC.Widget.Events.PLAY, () => {
        toggle.textContent = 'Pause';
        soundCloudWidgets.forEach((other) => { if (other !== widget) other.pause(); }); // un solo brano alla volta nel feed
        refreshSound();
    });
    widget.bind(SC.Widget.Events.PAUSE, () => { toggle.textContent = 'Play'; });
    widget.bind(SC.Widget.Events.FINISH, () => { toggle.textContent = 'Play'; showPosition(0); });
    widget.bind(SC.Widget.Events.PLAY_PROGRESS, (data) => { if (!seeking) showPosition(data.currentPosition); });

    toggle.addEventListener('click', () => widget.toggle());

    // "input" scatta mentre si trascina (aggiorna solo il tempo mostrato), "change" quando si lascia: lì si sposta davvero il brano.
    seek.addEventListener('pointerdown', () => { seeking = true; });
    seek.addEventListener('input', () => showPosition((seek.value / 1000) * duration));
    seek.addEventListener('change', () => {
        seeking = false;
        widget.seekTo((seek.value / 1000) * duration);
    });
}

if (soundCloudRoots.length) {
    const script = document.createElement('script');
    script.src = 'https://w.soundcloud.com/player/api.js';
    script.onload = () => {
        // Il widget si carica solo quando il player sta per entrare nello schermo (il feed ne può avere molti).
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                observer.unobserve(entry.target);
                initSoundCloud(entry.target);
            });
        }, { rootMargin: '300px' });
        soundCloudRoots.forEach((root) => observer.observe(root));
    };
    document.head.append(script);
}
