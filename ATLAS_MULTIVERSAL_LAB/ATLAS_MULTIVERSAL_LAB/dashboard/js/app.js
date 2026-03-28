let scene, camera, renderer, lamp;

function init() {
    // 1. Escena y Cámara
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, (window.innerWidth - 350) / window.innerHeight, 0.1, 1000);
    camera.position.z = 150;

    // 2. Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth - 350, window.innerHeight);
    document.getElementById('canvas-container').appendChild(renderer.domElement);

    // 3. Luces
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0xffaa00, 1, 500);
    pointLight.position.set(50, 50, 50);
    scene.add(pointLight);

    // 4. Geometría Inicial (Lámpara Paramétrica)
    createLamp(50, 32, 0);

    animate();
}

function createLamp(radius, segments, twist) {
    if (lamp) scene.remove(lamp);

    // Creamos una forma de cilindro para simular la lámpara
    const geometry = new THREE.CylinderGeometry(radius * 0.8, radius, 100, segments);
    
    // Aplicamos "twist" básico rotando los vértices (Simulación)
    const vertices = geometry.attributes.position.array;
    for (let i = 0; i < vertices.length; i += 3) {
        const y = vertices[i + 1];
        const angle = (y / 100) * (twist * Math.PI / 180);
        const x = vertices[i];
        const z = vertices[i + 2];
        vertices[i] = x * Math.cos(angle) - z * Math.sin(angle);
        vertices[i + 2] = x * Math.sin(angle) + z * Math.cos(angle);
    }

    const material = new THREE.MeshPhongMaterial({
        color: 0xffaa00,
        wireframe: true,
        transparent: true,
        opacity: 0.8
    });

    lamp = new THREE.Mesh(geometry, material);
    scene.add(lamp);
}

function animate() {
    requestAnimationFrame(animate);
    if (lamp) {
        lamp.rotation.y += 0.005;
    }
    renderer.render(scene, camera);
}

// Escuchadores de Sliders
document.getElementById('radius').addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('radius-val').innerText = val + 'mm';
    createLamp(val, document.getElementById('segments').value, document.getElementById('twist').value);
});

document.getElementById('segments').addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('segments-val').innerText = val + ' faces';
    createLamp(document.getElementById('radius').value, val, document.getElementById('twist').value);
});

document.getElementById('twist').addEventListener('input', (e) => {
    const val = e.target.value;
    document.getElementById('twist-val').innerText = val + '°';
    createLamp(document.getElementById('radius').value, document.getElementById('segments').value, val);
});

// Ajuste de ventana
window.addEventListener('resize', () => {
    camera.aspect = (window.innerWidth - 350) / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth - 350, window.innerHeight);
});

// Botón Generar (Simulación de llamada al Backend)
document.getElementById('generate').addEventListener('click', () => {
    const log = document.getElementById('log');
    log.innerHTML += `<br>> Requesting STL from Python...`;
    
    setTimeout(() => {
        log.innerHTML += `<br>> [SUCCESS] File generated: lamp_exp_v1.stl`;
        log.scrollTop = log.scrollHeight;
    }, 1500);
});

init();
