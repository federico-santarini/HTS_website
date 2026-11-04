// Galleria immagini dei progetti (markup in portfolio/_project.html, modale e carosello di Bootstrap).
// Bootstrap sa già aprire il modale, scorrere con le frecce a schermo e con lo swipe; qui manca solo:
//  1. aprire la galleria sull'immagine cliccata (non sempre sulla prima);
//  2. le frecce sinistra/destra della tastiera.

// Il modale parte con la miniatura cliccata in e.relatedTarget; data-gallery-index è la sua posizione.
// Si sposta la classe "active" a mano (senza animazione): il modale è ancora nascosto, non c'è nulla da animare.
document.addEventListener('show.bs.modal', (e) => {
    const thumb = e.relatedTarget;
    if (!thumb || thumb.dataset.galleryIndex === undefined) return;
    const items = e.target.querySelectorAll('.carousel-item');
    items.forEach((item, i) => item.classList.toggle('active', i === Number(thumb.dataset.galleryIndex)));
});

// Il carosello ha data-bs-keyboard="false": le frecce le gestiamo qui, una volta sola, per il modale aperto.
document.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const carousel = document.querySelector('.gallery-modal.show .carousel');
    if (!carousel) return;
    const instance = bootstrap.Carousel.getOrCreateInstance(carousel);
    if (e.key === 'ArrowLeft') instance.prev(); else instance.next();
});
