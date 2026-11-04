export async function checkBackendHealth() {
    const statusIndicator = document.getElementById('status-indicator');
    try {
        const response = await fetch('http://localhost:8000/api/v1/health');
        if (response.ok) {
            const data = await response.json();
            statusIndicator.textContent = `Backend status: Connected (${data.status})`;
            statusIndicator.style.color = '#10a37f';
        } else {
            statusIndicator.textContent = 'Backend status: Error connecting';
            statusIndicator.style.color = '#ef4444';
        }
    } catch (error) {
        statusIndicator.textContent = 'Backend status: Offline';
        statusIndicator.style.color = '#ef4444';
    }
} 