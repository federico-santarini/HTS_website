// Sfondo "liquido" dell'intro e della pagina About (markup: <canvas class="liquid">; aspetto: custom.css, .liquid in [03]).
//
// È uno shader WebGL a schermo intero: onde morbide di colore che scorrono piano. Quattro colori (base, onde, parte alta, riflessi)
// mescolati con rumore a più livelli, stirato in orizzontale. Tutto si regola dalle variabili CSS --hts-liquid-..., che hanno gli
// stessi nomi dei comandi del file di prova hts_soft_wave_shader_tuner.html.
// Senza WebGL (o se qualcosa va storto) la tela resta vuota: nell'intro si vede il nero, in About il colore di base (CSS). Si ferma da sola quando la tela viene
// tolta dalla pagina (fine dell'intro). Con "meno movimento" disegna un'immagine ferma.

(() => {
    const canvas = document.querySelector('.liquid');
    if (!canvas) return; // pagina senza sfondo, o intro assente (spento, già visto, movimento ridotto)

    const style = getComputedStyle(canvas);
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Valori dal CSS. I colori possono essere scritti in qualsiasi formato CSS: si fanno convertire in RGB dal browser.
    const swatch = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
    swatch.canvas.width = swatch.canvas.height = 1;
    function color(name, fallback) {
        swatch.clearRect(0, 0, 1, 1);
        swatch.fillStyle = '#000';
        swatch.fillStyle = style.getPropertyValue(name).trim() || fallback;
        swatch.fillRect(0, 0, 1, 1);
        const [r, g, b] = swatch.getImageData(0, 0, 1, 1).data;
        return [r / 255, g / 255, b / 255];
    }
    function number(name, fallback) {
        const value = parseFloat(style.getPropertyValue(name));
        return Number.isFinite(value) ? value : fallback;
    }
    const colors = {
        uBase: color('--hts-liquid-color-base', '#eec2ff'),
        uWaves: color('--hts-liquid-color-waves', '#8712a1'),
        uTop: color('--hts-liquid-color-top', '#a364b4'),
        uHighlight: color('--hts-liquid-color-highlight', '#99b2a7'),
    };
    const speed = number('--hts-liquid-speed', 0.7);             // 0 = fermo
    const shape = {
        uScale: number('--hts-liquid-scale', 2.35),              // più alto = onde più grandi
        uStretch: number('--hts-liquid-stretch', 0.4),           // allungamento orizzontale
        uTilt: number('--hts-liquid-tilt', 0),                   // inclinazione
        uRipple: number('--hts-liquid-ripple', 0),               // ondulazione
        uTopAmount: number('--hts-liquid-top-amount', 1),        // quanto si vede il colore della parte alta
        uHighlightAmount: number('--hts-liquid-highlight-amount', 0.9),
        uBrightness: number('--hts-liquid-brightness', 1),
    };
    const resolution = number('--hts-liquid-resolution', 0.5); // 1 = un pixel di tela per pixel dello schermo; 0.5 = metà (più leggero, la sfumatura non ne risente)

    if (number('--hts-liquid-opacity', 1) <= 0) return; // sfondo liquido spento (es. con la classe .intro-glow): niente da disegnare

    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' });
    if (!gl) return;

    // --- Shader. h/n/fbm: rumore a valori in 3D (la terza dimensione è il tempo), a tre livelli di dettaglio.
    const vertexSource = `
        attribute vec2 position;
        void main() { gl_Position = vec4(position, 0.0, 1.0); }
    `;
    const fragmentSource = `
        #ifdef GL_FRAGMENT_PRECISION_HIGH
        precision highp float;
        #else
        precision mediump float;
        #endif

        uniform vec2 iResolution;
        uniform float iGlobalTime;
        uniform float uScale, uStretch, uTilt, uRipple, uTopAmount, uHighlightAmount, uBrightness;
        uniform vec3 uBase, uWaves, uTop, uHighlight;

        float h(vec3 p) {
            p = fract(p * 0.3183099 + 0.1);
            p *= 17.0;
            return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
        }
        float n(vec3 x) {
            vec3 i = floor(x), f = fract(x);
            f = f * f * (3.0 - 2.0 * f);
            return mix(mix(mix(h(i), h(i + vec3(1, 0, 0)), f.x), mix(h(i + vec3(0, 1, 0)), h(i + vec3(1, 1, 0)), f.x), f.y),
                       mix(mix(h(i + vec3(0, 0, 1)), h(i + vec3(1, 0, 1)), f.x), mix(h(i + vec3(0, 1, 1)), h(i + vec3(1, 1, 1)), f.x), f.y), f.z);
        }
        float fbm(vec3 p) { return 0.62 * n(p) + 0.27 * n(p * 2.1 + 7.0) + 0.11 * n(p * 4.3 + 13.0); }

        void main() {
            // Coordinate normalizzate sull'altezza: le onde non si stirano sugli schermi larghi.
            vec2 uv = gl_FragCoord.xy / iResolution.y / uScale;
            float t = iGlobalTime;
            uv.y += uv.x * uTilt;
            uv.y += uRipple * (0.045 * sin(uv.x * 3.2 + t * 0.9) + 0.025 * sin(uv.x * 7.0 - t * 1.3));
            uv.x += 0.12 * (n(vec3(uv * 2.5, t * 0.2)) - 0.5);
            uv.x /= uStretch;
            float y = gl_FragCoord.y / iResolution.y;
            float a = fbm(vec3(uv.x * 1.3 - t * 0.08, uv.y * 4.2, t * 0.18));
            float g = fbm(vec3(uv.x * 0.9 + t * 0.05 + 31.0, uv.y * 2.6, t * 0.12));
            float l = fbm(vec3(uv.x * 2.0 - t * 0.14 + 9.0, uv.y * 7.0, t * 0.25));
            vec3 col = mix(uBase, uWaves, smoothstep(0.3, 0.7, a));
            col = mix(col, uTop, clamp(smoothstep(0.35, 0.72, g + (y - 0.55) * 0.45) * uTopAmount, 0.0, 1.0));
            col = mix(col, uHighlight, clamp(smoothstep(0.52, 0.85, l * 0.65 + a * 0.35) * uHighlightAmount, 0.0, 1.0));
            col = col * uBrightness + (h(vec3(gl_FragCoord.xy, 1.0)) - 0.5) / 255.0; // un filo di grana: niente gradini nelle sfumature
            gl_FragColor = vec4(col, 1.0);
        }
    `;

    function compile(type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
    }
    const vertex = compile(gl.VERTEX_SHADER, vertexSource);
    const fragment = compile(gl.FRAGMENT_SHADER, fragmentSource);
    if (!vertex || !fragment) return;
    const program = gl.createProgram();
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
    gl.useProgram(program);

    // Un rettangolo che copre tutto lo schermo (due triangoli).
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    const uResolution = gl.getUniformLocation(program, 'iResolution');
    const uTime = gl.getUniformLocation(program, 'iGlobalTime');
    for (const [name, value] of Object.entries(colors)) gl.uniform3fv(gl.getUniformLocation(program, name), value);
    for (const [name, value] of Object.entries(shape)) gl.uniform1f(gl.getUniformLocation(program, name), value);

    function resize() {
        canvas.width = Math.max(1, Math.round(canvas.clientWidth * resolution));
        canvas.height = Math.max(1, Math.round(canvas.clientHeight * resolution));
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform2f(uResolution, canvas.width, canvas.height);
        if (still) gl.drawArrays(gl.TRIANGLES, 0, 6); // ridimensionare svuota la tela: si ridisegna l'immagine ferma
    }
    resize();
    window.addEventListener('resize', resize);

    const startedAt = performance.now();
    function frame(now) {
        if (!canvas.isConnected) { // l'intro è finito (intro.js lo toglie dalla pagina): si smette e si libera la scheda grafica
            window.removeEventListener('resize', resize);
            gl.getExtension('WEBGL_lose_context')?.loseContext();
            return;
        }
        gl.uniform1f(uTime, ((now - startedAt) / 1000) * speed);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        requestAnimationFrame(frame);
    }
    if (!still) requestAnimationFrame(frame);
})();
