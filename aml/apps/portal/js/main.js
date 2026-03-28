'use strict';

/**
 * ATLAS MULTIVERSAL - Main Entry Point
 * Lógica para la Landing Page
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('--- ATLAS MULTIVERSAL PORTAL ONLINE ---');
  checkApiStatus();
});

async function checkApiStatus() {
  try {
    const response = await fetch('/api/');
    const data = await response.json();
    console.log('API Status:', data.status);
  } catch {
    console.warn('API Offline. Iniciando en modo local.');
  }
}
