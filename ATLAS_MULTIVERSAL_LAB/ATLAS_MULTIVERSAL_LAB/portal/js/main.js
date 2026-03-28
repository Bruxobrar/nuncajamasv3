'use strict';

/**
 * ATLAS MULTIVERSAL - Main Entry Point
 * Lógica para la Landing Page
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('--- ATLAS MULTIVERSAL PORTAL ONLINE ---');
    
    // Verificar estado de la API
    checkApiStatus();
});

async function checkApiStatus() {
    try {
        const response = await fetch('http://localhost:8000/api/');
        const data = await response.json();
        console.log('API Status:', data.status);
    } catch (error) {
        console.warn('API Offline. Iniciando en modo local.');
    }
}
