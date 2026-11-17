// Sfondo "liquido" dell'intro (markup: portfolio/_intro.html, <canvas class="intro-liquid">; aspetto: custom.css, sezione [13]).
//
// È uno shader WebGL a schermo intero: rumore simplex a più livelli, che scorre piano nel tempo, come un liquido. L'idea viene dal pen
// "Liquid Rainbow | GLSL" di Johan Karlsson (codepen.io/DonKarlssonSan/pen/gROawd); qui al posto dell'arcobaleno i colori sono una
// rampa nero → colore di accento → bianco, e tutto si regola dalle variabili CSS --intro-liquid-... (colori, velocità, scala, risoluzione).
// Senza WebGL (o se qualcosa va storto) la tela resta vuota e si vede il nero dell'intro. Si ferma da sola quando l'intro viene tolto.

(() => {
    const canvas = document.querySelector('.intro-liquid');
    if (!canvas) return; // l'intro non c'è (spento, già visto, movimento ridotto)

    const intro = canvas.closest('.intro');
    const style = getComputedStyle(intro);

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
    const dark = color('--intro-liquid-dark', '#000');
    const mid = color('--intro-liquid-mid', '#b026ff');
    const light = color('--intro-liquid-light', '#fff');
    const speed = number('--intro-liquid-speed', 1);           // 1 = come l'originale; 0.5 = metà; 2 = doppia
    const scale = number('--intro-liquid-scale', 1);           // 1 = macchie grandi come lo schermo; 2 = metà dimensione
    const white = Math.min(1, Math.max(0, number('--intro-liquid-white', 0.75))); // 0 = niente bianco, 1 = bianco pieno sulle creste
    const resolution = number('--intro-liquid-resolution', 0.5); // 1 = un pixel di tela per pixel dello schermo; 0.5 = metà (più leggero, la sfumatura non ne risente)

    if (number('--intro-liquid-opacity', 1) <= 0) return; // sfondo liquido spento (es. con la classe .intro-glow): niente da disegnare

    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' });
    if (!gl) return;

    // --- Shader. Il rumore simplex (snoise) è quello del pen originale (da gist.github.com/patriciogonzalezvivo/670c22f3966e662d2f83).
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
        uniform vec3 uDark;
        uniform vec3 uMid;
        uniform vec3 uLight;
        uniform float uScale;
        uniform float uWhite;

        vec3 permute(vec3 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }

        float snoise(vec2 v) {
            const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                                -0.577350269189626, 0.024390243902439);
            vec2 i  = floor(v + dot(v, C.yy));
            vec2 x0 = v - i + dot(i, C.xx);
            vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
            vec4 x12 = x0.xyxy + C.xxzz;
            x12.xy -= i1;
            i = mod(i, 289.0);
            vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
            vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
            m = m * m;
            m = m * m;
            vec3 x = 2.0 * fract(p * C.www) - 1.0;
            vec3 h = abs(x) - 0.5;
            vec3 ox = floor(x + 0.5);
            vec3 a0 = x - ox;
            m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
            vec3 g;
            g.x  = a0.x * x0.x + h.x * x0.y;
            g.yz = a0.yz * x12.xz + h.yz * x12.yw;
            return 130.0 * dot(m, g);
        }

        void main() {
            // Come nel pen originale, ma con le coordinate normalizzate sull'altezza (le macchie non si stirano sugli schermi larghi).
            vec2 uv = gl_FragCoord.xy / iResolution.y * uScale;
            float xnoise = snoise(vec2(uv.x, iGlobalTime / 5.0 + 10000.0));
            float ynoise = snoise(vec2(uv.y, iGlobalTime / 5.0 + 500.0));
            vec2 t = vec2(xnoise, ynoise);
            float s1 = snoise(uv + t / 2.0 + snoise(uv + snoise(uv + t / 3.0) / 5.0));
            float s2 = snoise(uv + snoise(uv + s1) / 7.0);

            // Nell'originale s1 sceglieva la tinta e s2 la luminosità. Qui s1 sceglie il punto della rampa nero → accento → bianco e
            // s2 lo sposta verso lo scuro (dà profondità alle macchie senza ingrigire i colori). uWhite limita quanto in alto arriva la rampa.
            float level = s1 * 0.5 + 0.5 - s2 * 0.35 - 0.12;
            float a = min(smoothstep(0.2, 1.0, level), 0.5 + 0.5 * uWhite);
            vec3 col = a < 0.5 ? mix(uDark, uMid, a * 2.0) : mix(uMid, uLight, (a - 0.5) * 2.0);
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
    gl.uniform3fv(gl.getUniformLocation(program, 'uDark'), dark);
    gl.uniform3fv(gl.getUniformLocation(program, 'uMid'), mid);
    gl.uniform3fv(gl.getUniformLocation(program, 'uLight'), light);
    gl.uniform1f(gl.getUniformLocation(program, 'uScale'), scale);
    gl.uniform1f(gl.getUniformLocation(program, 'uWhite'), white);

    function resize() {
        canvas.width = Math.max(1, Math.round(canvas.clientWidth * resolution));
        canvas.height = Math.max(1, Math.round(canvas.clientHeight * resolution));
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform2f(uResolution, canvas.width, canvas.height);
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
    requestAnimationFrame(frame);
})();
