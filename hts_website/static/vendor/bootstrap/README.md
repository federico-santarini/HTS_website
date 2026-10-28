# Bootstrap (copia locale)

Versione **5.3.8**, licenza MIT (vedi `LICENSE`). I file sono quelli ufficiali del pacchetto npm `bootstrap`,
presi senza modifiche (l'integrità del pacchetto è stata verificata con l'hash pubblicato dal registro npm):

- `css/bootstrap.min.css`
- `js/bootstrap.bundle.min.js` (include Popper; serve per la navbar che si apre su mobile, i menu a tendina, ecc.)

Non si modificano questi file: lo stile personale sta in `static/css/custom.css`, caricato dopo.

Le mappe dei sorgenti (`*.map`) non sono incluse: se aprendo gli strumenti per sviluppatori del browser compare un
404 su `bootstrap.min.css.map` è normale e non ha effetti sul sito.

## Aggiornare Bootstrap

1. Scarica il pacchetto nella nuova versione: `npm pack bootstrap@<versione>` (oppure
   `https://registry.npmjs.org/bootstrap/-/bootstrap-<versione>.tgz`).
2. Sostituisci i tre file qui sopra con `package/dist/css/bootstrap.min.css`,
   `package/dist/js/bootstrap.bundle.min.js` e `package/LICENSE`.
3. Aggiorna il numero di versione in questo file e controlla le pagine: tra versioni maggiori (es. 5 → 6)
   cambiano nomi di classi e variabili.
